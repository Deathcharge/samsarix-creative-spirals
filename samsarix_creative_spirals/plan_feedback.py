# Copyright (c) 2026 Samsarix LLC
# SPDX-License-Identifier: MPL-2.0

"""Immutable, source-bound feedback records for campaign-plan review."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .media_package import (
    CampaignPlanMedia,
    CampaignPlanMediaBinding,
    campaign_plan_media_binding_issues,
    campaign_plan_media_identity_issues,
)
from .models import ConfigError, SUPPORTED_PLATFORMS
from .plans import CampaignPlanBundle
from .review import _format_utc, _normalized_text, _parse_timestamp
from .workflow import _load_json_object

MAX_PLAN_REVIEW_FINDINGS = 50
PLAN_REVIEW_DECISIONS = ("comment", "request-changes", "reject")

_FINDING_KEYS = {"message", "item", "platform", "suggestion"}
_REVIEW_KEYS = {
    "schemaVersion",
    "artifactType",
    "reviewId",
    "reviewHash",
    "planId",
    "sourceHash",
    "decision",
    "reviewedBy",
    "reviewedAt",
    "findings",
    "note",
    "media",
}
_REVIEW_ID_RE = re.compile(r"^scr_[0-9a-f]{12}$")
_PLAN_ID_RE = re.compile(r"^scp_[0-9a-f]{12}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def parse_plan_review_timestamp(value: str) -> datetime:
    """Parse a CLI/API review timestamp using the plan-review contract."""
    issues: list[str] = []
    parsed = _parse_timestamp(value, field="reviewed_at", issues=issues)
    if issues or parsed is None:
        raise ConfigError(issues)
    return parsed


def _canonical_json(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )


def _bounded_item(value: object, *, field: str, issues: list[str]) -> int | None:
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= 100:
        issues.append(f"{field} must be an integer between 1 and 100")
        return None
    return value


@dataclass(frozen=True, slots=True)
class PlanReviewFinding:
    """One actionable or informational observation about an exact plan revision."""

    message: str
    item: int | None = None
    platform: str | None = None
    suggestion: str | None = None

    def __post_init__(self) -> None:
        issues: list[str] = []
        message = _normalized_text(
            self.message,
            field="message",
            maximum=1_000,
            multiline=True,
            issues=issues,
        )
        item = _bounded_item(self.item, field="item", issues=issues)
        if self.platform is not None and self.platform not in SUPPORTED_PLATFORMS:
            issues.append(f"platform must be one of: {', '.join(SUPPORTED_PLATFORMS)}")
        if self.platform is not None and item is None:
            issues.append("platform requires an item number")
        suggestion = None
        if self.suggestion is not None:
            suggestion = _normalized_text(
                self.suggestion,
                field="suggestion",
                maximum=1_000,
                multiline=True,
                issues=issues,
            )
        if issues:
            raise ConfigError(issues)
        object.__setattr__(self, "message", message)
        object.__setattr__(self, "item", item)
        object.__setattr__(self, "suggestion", suggestion)

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"message": self.message}
        if self.item is not None:
            result["item"] = self.item
        if self.platform is not None:
            result["platform"] = self.platform
        if self.suggestion is not None:
            result["suggestion"] = self.suggestion
        return result

    @classmethod
    def from_dict(
        cls,
        raw: object,
        *,
        field: str,
        issues: list[str],
    ) -> PlanReviewFinding | None:
        if not isinstance(raw, Mapping):
            issues.append(f"{field} must be an object")
            return None
        unknown = sorted(str(key) for key in raw if key not in _FINDING_KEYS)
        if unknown:
            issues.append(f"{field} has unknown field(s): {', '.join(unknown)}")
        nested: list[str] = []
        message = _normalized_text(
            raw.get("message"),
            field=f"{field}.message",
            maximum=1_000,
            multiline=True,
            issues=nested,
        )
        item = _bounded_item(raw.get("item"), field=f"{field}.item", issues=nested)
        platform_value = raw.get("platform")
        platform = platform_value if isinstance(platform_value, str) else None
        if platform_value is not None and platform not in SUPPORTED_PLATFORMS:
            nested.append(f"{field}.platform must be one of: {', '.join(SUPPORTED_PLATFORMS)}")
        if platform is not None and item is None:
            nested.append(f"{field}.platform requires an item number")
        suggestion = None
        if "suggestion" in raw:
            suggestion = _normalized_text(
                raw.get("suggestion"),
                field=f"{field}.suggestion",
                maximum=1_000,
                multiline=True,
                issues=nested,
            )
        issues.extend(nested)
        if nested:
            return None
        return cls(message=message, item=item, platform=platform, suggestion=suggestion)


@dataclass(frozen=True, slots=True)
class CampaignPlanReview:
    """Deterministically identified feedback for one exact campaign-plan revision."""

    review_id: str
    review_hash: str
    plan_id: str
    source_hash: str
    decision: str
    reviewed_by: str
    reviewed_at: datetime
    findings: tuple[PlanReviewFinding, ...]
    note: str | None = None
    media: CampaignPlanMediaBinding | None = None

    def __post_init__(self) -> None:
        issues: list[str] = []
        if not _REVIEW_ID_RE.fullmatch(self.review_id):
            issues.append("review_id must be a Samsarix plan review ID")
        if not _SHA256_RE.fullmatch(self.review_hash):
            issues.append("review_hash must be a lowercase SHA-256 hash")
        if not _PLAN_ID_RE.fullmatch(self.plan_id):
            issues.append("plan_id must be a Samsarix campaign plan ID")
        if not _SHA256_RE.fullmatch(self.source_hash):
            issues.append("source_hash must be a lowercase SHA-256 hash")
        if self.decision not in PLAN_REVIEW_DECISIONS:
            issues.append(f"decision must be one of: {', '.join(PLAN_REVIEW_DECISIONS)}")
        reviewer = _normalized_text(
            self.reviewed_by,
            field="reviewed_by",
            maximum=120,
            multiline=False,
            issues=issues,
        )
        if not isinstance(self.reviewed_at, datetime) or self.reviewed_at.utcoffset() is None:
            issues.append("reviewed_at must be a date-time with timezone information")
            timestamp = datetime(1970, 1, 1, tzinfo=timezone.utc)
        else:
            timestamp = self.reviewed_at.astimezone(timezone.utc)
        try:
            findings = tuple(self.findings)
        except TypeError:
            issues.append("findings must contain PlanReviewFinding values")
            findings = ()
        if not 1 <= len(findings) <= MAX_PLAN_REVIEW_FINDINGS:
            issues.append(f"findings must contain between 1 and {MAX_PLAN_REVIEW_FINDINGS} items")
        if any(not isinstance(finding, PlanReviewFinding) for finding in findings):
            issues.append("findings must contain PlanReviewFinding values")
        note = None
        if self.note is not None:
            note = _normalized_text(
                self.note,
                field="note",
                maximum=500,
                multiline=True,
                issues=issues,
            )
        media_value: object = self.media
        if media_value is not None and not isinstance(media_value, CampaignPlanMediaBinding):
            issues.append("media must be a CampaignPlanMediaBinding value")
        if issues:
            raise ConfigError(issues)
        object.__setattr__(self, "reviewed_by", reviewer)
        object.__setattr__(self, "reviewed_at", timestamp)
        object.__setattr__(self, "findings", findings)
        object.__setattr__(self, "note", note)
        expected_hash = hashlib.sha256(_canonical_json(self._core_dict())).hexdigest()
        if self.review_hash != expected_hash:
            raise ConfigError("review_hash does not match canonical plan review content")
        if self.review_id != f"scr_{expected_hash[:12]}":
            raise ConfigError("review_id does not match review_hash")

    def _core_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "schemaVersion": 1,
            "artifactType": "plan-review",
            "planId": self.plan_id,
            "sourceHash": self.source_hash,
            "decision": self.decision,
            "reviewedBy": self.reviewed_by,
            "reviewedAt": _format_utc(self.reviewed_at),
            "findings": [finding.to_dict() for finding in self.findings],
        }
        if self.note is not None:
            result["note"] = self.note
        if self.media is not None:
            result["media"] = self.media.to_dict()
        return result

    def to_dict(self) -> dict[str, Any]:
        core = self._core_dict()
        return {
            "schemaVersion": core["schemaVersion"],
            "artifactType": core["artifactType"],
            "reviewId": self.review_id,
            "reviewHash": self.review_hash,
            **{
                key: value
                for key, value in core.items()
                if key not in {"schemaVersion", "artifactType"}
            },
        }

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> CampaignPlanReview:
        if not isinstance(raw, Mapping):
            raise ConfigError("plan review must be a JSON object")
        issues: list[str] = []
        unknown = sorted(str(key) for key in raw if key not in _REVIEW_KEYS)
        if unknown:
            issues.append(f"unknown plan review field(s): {', '.join(unknown)}")
        if raw.get("schemaVersion") != 1 or isinstance(raw.get("schemaVersion"), bool):
            issues.append("schemaVersion must be 1")
        if raw.get("artifactType") != "plan-review":
            issues.append("artifactType must be plan-review")

        review_id_value = raw.get("reviewId")
        review_id = review_id_value if isinstance(review_id_value, str) else ""
        if not _REVIEW_ID_RE.fullmatch(review_id):
            issues.append("reviewId must be a Samsarix plan review ID")
        review_hash_value = raw.get("reviewHash")
        review_hash = review_hash_value if isinstance(review_hash_value, str) else ""
        if not _SHA256_RE.fullmatch(review_hash):
            issues.append("reviewHash must be a lowercase SHA-256 hash")
        plan_id_value = raw.get("planId")
        plan_id = plan_id_value if isinstance(plan_id_value, str) else ""
        if not _PLAN_ID_RE.fullmatch(plan_id):
            issues.append("planId must be a Samsarix campaign plan ID")
        source_hash_value = raw.get("sourceHash")
        source_hash = source_hash_value if isinstance(source_hash_value, str) else ""
        if not _SHA256_RE.fullmatch(source_hash):
            issues.append("sourceHash must be a lowercase SHA-256 hash")
        decision_value = raw.get("decision")
        decision = decision_value if isinstance(decision_value, str) else ""
        if decision not in PLAN_REVIEW_DECISIONS:
            issues.append(f"decision must be one of: {', '.join(PLAN_REVIEW_DECISIONS)}")
        reviewed_by = _normalized_text(
            raw.get("reviewedBy"),
            field="reviewedBy",
            maximum=120,
            multiline=False,
            issues=issues,
        )
        reviewed_at = _parse_timestamp(raw.get("reviewedAt"), field="reviewedAt", issues=issues)

        findings_value = raw.get("findings")
        findings: list[PlanReviewFinding] = []
        if not isinstance(findings_value, list):
            issues.append("findings must be a non-empty array")
        else:
            if not 1 <= len(findings_value) <= MAX_PLAN_REVIEW_FINDINGS:
                issues.append(
                    f"findings must contain between 1 and {MAX_PLAN_REVIEW_FINDINGS} items"
                )
            for index, value in enumerate(findings_value[:MAX_PLAN_REVIEW_FINDINGS]):
                finding = PlanReviewFinding.from_dict(
                    value,
                    field=f"findings[{index}]",
                    issues=issues,
                )
                if finding is not None:
                    findings.append(finding)

        note = None
        if "note" in raw:
            note = _normalized_text(
                raw.get("note"),
                field="note",
                maximum=500,
                multiline=True,
                issues=issues,
            )
        media = None
        if "media" in raw:
            media = CampaignPlanMediaBinding.from_dict(
                raw.get("media"), field="media", issues=issues
            )
        if issues:
            raise ConfigError(issues)
        assert reviewed_at is not None
        return cls(
            review_id=review_id,
            review_hash=review_hash,
            plan_id=plan_id,
            source_hash=source_hash,
            decision=decision,
            reviewed_by=reviewed_by,
            reviewed_at=reviewed_at,
            findings=tuple(findings),
            note=note,
            media=media,
        )


@dataclass(frozen=True, slots=True)
class PlanReviewIssue:
    """One verification failure for a plan-review record."""

    code: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": self.message}


@dataclass(frozen=True, slots=True)
class PlanReviewCheck:
    """Verification result for one review record and current plan state."""

    plan_id: str
    review: CampaignPlanReview
    valid: bool
    blocking: bool
    issues: tuple[PlanReviewIssue, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": 1,
            "valid": self.valid,
            "blocking": self.blocking,
            "planId": self.plan_id,
            "review": self.review.to_dict(),
            "issues": [issue.to_dict() for issue in self.issues],
        }


def create_campaign_plan_review(
    bundle: CampaignPlanBundle,
    *,
    decision: str,
    reviewed_by: str,
    findings: Sequence[PlanReviewFinding],
    reviewed_at: datetime | None = None,
    note: str | None = None,
    media: CampaignPlanMedia | None = None,
) -> CampaignPlanReview:
    """Create immutable feedback for the current exact plan and optional media snapshot."""
    issues: list[str] = []
    if decision not in PLAN_REVIEW_DECISIONS:
        issues.append(f"decision must be one of: {', '.join(PLAN_REVIEW_DECISIONS)}")
    reviewer = _normalized_text(
        reviewed_by,
        field="reviewed_by",
        maximum=120,
        multiline=False,
        issues=issues,
    )
    timestamp = reviewed_at or datetime.now(timezone.utc)
    if not isinstance(timestamp, datetime) or timestamp.utcoffset() is None:
        issues.append("reviewed_at must include timezone information")
    try:
        normalized_findings = tuple(findings)
    except TypeError:
        issues.append("findings must contain PlanReviewFinding values")
        normalized_findings = ()
    if not 1 <= len(normalized_findings) <= MAX_PLAN_REVIEW_FINDINGS:
        issues.append(f"findings must contain between 1 and {MAX_PLAN_REVIEW_FINDINGS} items")
    if any(not isinstance(finding, PlanReviewFinding) for finding in normalized_findings):
        issues.append("findings must contain PlanReviewFinding values")
    else:
        for index, finding in enumerate(normalized_findings, start=1):
            if finding.item is not None and finding.item > len(bundle.items):
                issues.append(
                    f"finding {index} targets item {finding.item}, but the plan has "
                    f"{len(bundle.items)} item(s)"
                )
    normalized_note = None
    if note is not None:
        normalized_note = _normalized_text(
            note,
            field="note",
            maximum=500,
            multiline=True,
            issues=issues,
        )
    issues.extend(message for _, message in campaign_plan_media_identity_issues(bundle, media))
    if issues:
        raise ConfigError(issues)
    timestamp_utc = timestamp.astimezone(timezone.utc)
    media_binding = media.binding if media is not None else None
    core: dict[str, Any] = {
        "schemaVersion": 1,
        "artifactType": "plan-review",
        "planId": bundle.plan_id,
        "sourceHash": bundle.source_hash,
        "decision": decision,
        "reviewedBy": reviewer,
        "reviewedAt": _format_utc(timestamp_utc),
        "findings": [finding.to_dict() for finding in normalized_findings],
    }
    if normalized_note is not None:
        core["note"] = normalized_note
    if media_binding is not None:
        core["media"] = media_binding.to_dict()
    review_hash = hashlib.sha256(_canonical_json(core)).hexdigest()
    return CampaignPlanReview(
        review_id=f"scr_{review_hash[:12]}",
        review_hash=review_hash,
        plan_id=bundle.plan_id,
        source_hash=bundle.source_hash,
        decision=decision,
        reviewed_by=reviewer,
        reviewed_at=timestamp_utc,
        findings=normalized_findings,
        note=normalized_note,
        media=media_binding,
    )


def load_campaign_plan_review(path: str | Path) -> CampaignPlanReview:
    """Load and validate one bounded local plan-review JSON file."""
    return CampaignPlanReview.from_dict(_load_json_object(path, kind="plan review"))


def export_campaign_plan_review(review: CampaignPlanReview, path: str | Path) -> Path:
    """Write a new review record without replacing existing feedback evidence."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(review.to_dict(), ensure_ascii=False, indent=2) + "\n"
    try:
        with destination.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
    except FileExistsError:
        raise ConfigError(
            f"refusing to overwrite existing plan review file: {destination}"
        ) from None
    return destination


def verify_campaign_plan_review(
    bundle: CampaignPlanBundle,
    review: CampaignPlanReview,
    *,
    media: CampaignPlanMedia | None = None,
) -> PlanReviewCheck:
    """Verify that feedback still describes the current exact plan and media bytes."""
    issues: list[PlanReviewIssue] = []
    if review.source_hash != bundle.source_hash:
        issues.append(
            PlanReviewIssue("source-changed", "Plan source no longer matches the review.")
        )
    if review.plan_id != bundle.plan_id:
        issues.append(PlanReviewIssue("plan-id-changed", "Plan ID no longer matches the review."))
    issues.extend(
        PlanReviewIssue(code, message)
        for code, message in campaign_plan_media_binding_issues(review.media, media)
    )
    issues.extend(
        PlanReviewIssue(code, message)
        for code, message in campaign_plan_media_identity_issues(bundle, media)
    )
    for index, finding in enumerate(review.findings, start=1):
        if finding.item is not None and finding.item > len(bundle.items):
            issues.append(
                PlanReviewIssue(
                    "finding-item-missing",
                    f"Finding {index} targets item {finding.item}, but the plan has "
                    f"{len(bundle.items)} item(s).",
                )
            )
    valid = not issues
    return PlanReviewCheck(
        plan_id=bundle.plan_id,
        review=review,
        valid=valid,
        blocking=valid and review.decision in {"request-changes", "reject"},
        issues=tuple(issues),
    )
