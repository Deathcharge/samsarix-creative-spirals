# Copyright (c) 2026 Samsarix LLC
# SPDX-License-Identifier: MPL-2.0

"""Semantic campaign review and non-cryptographic local approval records."""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import CampaignBundle, CampaignConfig, ConfigError, SUPPORTED_PLATFORMS
from .quality import check_campaign
from .workflow import _load_json_object, build_campaign

_DIFF_FIELDS = (
    "name",
    "title",
    "body",
    "link",
    "hashtags",
    "platforms",
    "platformLimits",
    "media",
)
_DRAFT_FIELDS = (
    "content",
    "characterCount",
    "originalCharacterCount",
    "characterLimit",
    "truncated",
    "warnings",
    "media",
)
_APPROVAL_KEYS = {
    "schemaVersion",
    "artifactType",
    "campaignId",
    "sourceHash",
    "approvedBy",
    "approvedAt",
    "qualityPolicy",
    "note",
}
_CAMPAIGN_ID_RE = re.compile(r"^scs_[0-9a-f]{12}$")
_SOURCE_HASH_RE = re.compile(r"^[0-9a-f]{64}$")
_RFC3339_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$")


def _format_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_timestamp(value: Any, *, field: str, issues: list[str]) -> datetime | None:
    if not isinstance(value, str) or not _RFC3339_RE.fullmatch(value):
        issues.append(f"{field} must be an RFC 3339 date-time with an explicit offset or Z")
        return None
    normalized = re.sub(
        r"\.(\d+)(?=Z|[+-]\d{2}:\d{2}$)",
        lambda match: "." + (match.group(1) + "000000")[:6],
        value,
    )
    try:
        parsed = datetime.fromisoformat(normalized.replace("Z", "+00:00"))
    except ValueError:
        issues.append(f"{field} must be a valid date and time")
        return None
    if value.endswith("-00:00"):
        issues.append(f"{field} must use a known UTC offset instead of -00:00")
        return None
    return parsed.astimezone(timezone.utc)


def _normalized_text(
    value: Any,
    *,
    field: str,
    maximum: int,
    multiline: bool,
    issues: list[str],
) -> str:
    if not isinstance(value, str):
        issues.append(f"{field} must be a string")
        return ""
    result = unicodedata.normalize("NFC", value.replace("\r\n", "\n").replace("\r", "\n")).strip()
    if not result:
        issues.append(f"{field} must not be empty")
    elif len(result) > maximum:
        issues.append(f"{field} must be at most {maximum} characters")
    if any(
        unicodedata.category(character) in {"Cc", "Cs"} and not (multiline and character in "\n\t")
        for character in result
    ):
        issues.append(f"{field} contains unsupported control characters")
    if not multiline and ("\n" in result or "\t" in result):
        issues.append(f"{field} must be a single line")
    return result


def _semantic_config(config: CampaignConfig) -> dict[str, Any]:
    return {
        "name": config.name,
        "title": config.title,
        "body": config.body,
        "link": config.link,
        "hashtags": list(config.hashtags),
        "platforms": list(config.platforms),
        "platformLimits": dict(config.platform_limits),
        "media": [reference.to_dict() for reference in config.media],
    }


@dataclass(frozen=True, slots=True)
class CampaignFieldChange:
    """One normalized campaign-source field that changed."""

    field: str
    before: Any
    after: Any

    def to_dict(self) -> dict[str, Any]:
        return {"field": self.field, "before": self.before, "after": self.after}


@dataclass(frozen=True, slots=True)
class CampaignDraftChange:
    """One added, removed, or modified generated platform draft."""

    platform: str
    change: str
    fields: tuple[str, ...]
    before: dict[str, Any] | None
    after: dict[str, Any] | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "platform": self.platform,
            "change": self.change,
            "fields": list(self.fields),
            "before": self.before,
            "after": self.after,
        }


@dataclass(frozen=True, slots=True)
class CampaignDiff:
    """Deterministic semantic comparison of two validated campaigns."""

    before_campaign_id: str
    after_campaign_id: str
    before_source_hash: str
    after_source_hash: str
    fields: tuple[CampaignFieldChange, ...]
    drafts: tuple[CampaignDraftChange, ...]

    @property
    def changed(self) -> bool:
        return bool(self.fields or self.drafts)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": 1,
            "changed": self.changed,
            "beforeCampaignId": self.before_campaign_id,
            "afterCampaignId": self.after_campaign_id,
            "beforeSourceHash": self.before_source_hash,
            "afterSourceHash": self.after_source_hash,
            "fields": [change.to_dict() for change in self.fields],
            "drafts": [change.to_dict() for change in self.drafts],
        }


def diff_campaigns(
    before: CampaignConfig | dict[str, Any],
    after: CampaignConfig | dict[str, Any],
) -> CampaignDiff:
    """Compare normalized source fields and their generated platform drafts."""
    before_config = (
        before if isinstance(before, CampaignConfig) else CampaignConfig.from_dict(before)
    )
    after_config = after if isinstance(after, CampaignConfig) else CampaignConfig.from_dict(after)
    before_bundle = build_campaign(before_config)
    after_bundle = build_campaign(after_config)
    before_values = _semantic_config(before_config)
    after_values = _semantic_config(after_config)
    field_changes = tuple(
        CampaignFieldChange(field, before_values[field], after_values[field])
        for field in _DIFF_FIELDS
        if before_values[field] != after_values[field]
    )

    before_drafts = {draft.platform: draft.to_dict() for draft in before_bundle.drafts}
    after_drafts = {draft.platform: draft.to_dict() for draft in after_bundle.drafts}
    draft_changes: list[CampaignDraftChange] = []
    for platform in SUPPORTED_PLATFORMS:
        old = before_drafts.get(platform)
        new = after_drafts.get(platform)
        if old == new:
            continue
        changed_fields: tuple[str, ...]
        if old is None:
            change = "added"
            changed_fields = _DRAFT_FIELDS
        elif new is None:
            change = "removed"
            changed_fields = _DRAFT_FIELDS
        else:
            change = "modified"
            changed_fields = tuple(field for field in _DRAFT_FIELDS if old[field] != new[field])
        draft_changes.append(CampaignDraftChange(platform, change, changed_fields, old, new))

    return CampaignDiff(
        before_campaign_id=before_bundle.campaign_id,
        after_campaign_id=after_bundle.campaign_id,
        before_source_hash=before_bundle.source_hash,
        after_source_hash=after_bundle.source_hash,
        fields=field_changes,
        drafts=tuple(draft_changes),
    )


@dataclass(frozen=True, slots=True)
class CampaignApproval:
    """Human-readable local approval metadata; it is not a digital signature."""

    campaign_id: str
    source_hash: str
    approved_by: str
    approved_at: datetime
    warnings_as_errors: bool = False
    note: str | None = None

    @property
    def quality_policy(self) -> str:
        return "warnings-as-errors" if self.warnings_as_errors else "errors-only"

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "schemaVersion": 1,
            "artifactType": "campaign",
            "campaignId": self.campaign_id,
            "sourceHash": self.source_hash,
            "approvedBy": self.approved_by,
            "approvedAt": _format_utc(self.approved_at),
            "qualityPolicy": self.quality_policy,
        }
        if self.note is not None:
            result["note"] = self.note
        return result

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> CampaignApproval:
        issues: list[str] = []
        unknown = sorted(str(key) for key in raw if key not in _APPROVAL_KEYS)
        if unknown:
            issues.append(f"unknown approval field(s): {', '.join(unknown)}")
        if raw.get("schemaVersion") != 1 or isinstance(raw.get("schemaVersion"), bool):
            issues.append("schemaVersion must be 1")
        if raw.get("artifactType") != "campaign":
            issues.append("artifactType must be campaign")

        campaign_id_value = raw.get("campaignId")
        campaign_id = campaign_id_value if isinstance(campaign_id_value, str) else ""
        if not _CAMPAIGN_ID_RE.fullmatch(campaign_id):
            issues.append("campaignId must be a Samsarix campaign ID")
        source_hash_value = raw.get("sourceHash")
        source_hash = source_hash_value if isinstance(source_hash_value, str) else ""
        if not _SOURCE_HASH_RE.fullmatch(source_hash):
            issues.append("sourceHash must be a lowercase SHA-256 hash")

        approved_by = _normalized_text(
            raw.get("approvedBy"),
            field="approvedBy",
            maximum=120,
            multiline=False,
            issues=issues,
        )
        approved_at = _parse_timestamp(raw.get("approvedAt"), field="approvedAt", issues=issues)
        policy = raw.get("qualityPolicy")
        if policy not in {"errors-only", "warnings-as-errors"}:
            issues.append("qualityPolicy must be errors-only or warnings-as-errors")

        note: str | None
        if "note" not in raw:
            note = None
        else:
            note = _normalized_text(
                raw["note"],
                field="note",
                maximum=500,
                multiline=True,
                issues=issues,
            )
        if issues:
            raise ConfigError(issues)
        assert approved_at is not None
        return cls(
            campaign_id=campaign_id,
            source_hash=source_hash,
            approved_by=approved_by,
            approved_at=approved_at,
            warnings_as_errors=policy == "warnings-as-errors",
            note=note,
        )


@dataclass(frozen=True, slots=True)
class ApprovalIssue:
    """One stable reason that a local approval is not current."""

    code: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": self.message}


@dataclass(frozen=True, slots=True)
class ApprovalCheck:
    """Verification result for a campaign and a local approval record."""

    campaign_id: str
    approval: CampaignApproval
    valid: bool
    issues: tuple[ApprovalIssue, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": 1,
            "valid": self.valid,
            "campaignId": self.campaign_id,
            "approval": self.approval.to_dict(),
            "issues": [issue.to_dict() for issue in self.issues],
        }


def create_campaign_approval(
    bundle: CampaignBundle,
    *,
    approved_by: str,
    approved_at: datetime | None = None,
    warnings_as_errors: bool = False,
    note: str | None = None,
) -> CampaignApproval:
    """Create local approval metadata only when the selected quality policy passes."""
    issues: list[str] = []
    normalized_approver = _normalized_text(
        approved_by,
        field="approved_by",
        maximum=120,
        multiline=False,
        issues=issues,
    )
    normalized_note: str | None = None
    if note is not None:
        normalized_note = _normalized_text(
            note,
            field="note",
            maximum=500,
            multiline=True,
            issues=issues,
        )
    timestamp = approved_at or datetime.now(timezone.utc)
    if timestamp.utcoffset() is None:
        issues.append("approved_at must include timezone information")
    quality = check_campaign(bundle, warnings_as_errors=warnings_as_errors)
    if not quality.publishable:
        details = ", ".join(
            f"[{issue.platform}] {issue.message}"
            for issue in quality.issues
            if issue.severity == "error"
        )
        issues.append(f"campaign does not pass the selected quality policy: {details}")
    if issues:
        raise ConfigError(issues)
    return CampaignApproval(
        campaign_id=bundle.campaign_id,
        source_hash=bundle.source_hash,
        approved_by=normalized_approver,
        approved_at=timestamp.astimezone(timezone.utc),
        warnings_as_errors=warnings_as_errors,
        note=normalized_note,
    )


def load_campaign_approval(path: str | Path) -> CampaignApproval:
    """Load and validate one bounded local approval JSON file."""
    return CampaignApproval.from_dict(_load_json_object(path, kind="approval"))


def export_campaign_approval(approval: CampaignApproval, path: str | Path) -> Path:
    """Write an approval record to a new file without replacing existing evidence."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(approval.to_dict(), ensure_ascii=False, indent=2) + "\n"
    try:
        with destination.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
    except FileExistsError:
        raise ConfigError(f"refusing to overwrite existing approval file: {destination}") from None
    return destination


def verify_campaign_approval(
    bundle: CampaignBundle,
    approval: CampaignApproval,
) -> ApprovalCheck:
    """Verify source identity and re-run the approval record's quality policy."""
    issues: list[ApprovalIssue] = []
    if approval.source_hash != bundle.source_hash:
        issues.append(
            ApprovalIssue("source-changed", "Campaign source no longer matches the approved hash.")
        )
    if approval.campaign_id != bundle.campaign_id:
        issues.append(
            ApprovalIssue("campaign-id-changed", "Campaign ID no longer matches the approval.")
        )
    quality = check_campaign(bundle, warnings_as_errors=approval.warnings_as_errors)
    if not quality.publishable:
        issues.append(
            ApprovalIssue(
                "quality-policy-failed",
                "Campaign no longer passes the quality policy recorded by the approval.",
            )
        )
    return ApprovalCheck(
        campaign_id=bundle.campaign_id,
        approval=approval,
        valid=not issues,
        issues=tuple(issues),
    )


def parse_approval_timestamp(value: str) -> datetime:
    """Parse a CLI/API approval timestamp using the approval contract."""
    issues: list[str] = []
    parsed = _parse_timestamp(value, field="approved_at", issues=issues)
    if issues or parsed is None:
        raise ConfigError(issues)
    return parsed
