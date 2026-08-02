# Copyright (c) 2026 Samsarix LLC
# SPDX-License-Identifier: MPL-2.0

"""Semantic plan review and non-cryptographic local approval records."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import ConfigError
from .policy import ContentPolicy, ContentPolicyBinding, content_policy_binding_issues
from .plans import (
    CampaignPlan,
    CampaignPlanBundle,
    PlanIssue,
    PlannedCampaign,
    build_campaign_plan,
    check_campaign_plan,
)
from .review import (
    ApprovalIssue,
    CampaignDiff,
    _format_utc,
    _normalized_text,
    _parse_timestamp,
    diff_campaigns,
)
from .workflow import _load_json_object

_PLAN_DIFF_FIELDS = ("name", "requiredPlatforms")
_PLAN_ITEM_DIFF_FIELDS = ("source", "intendedAt", "campaign")
_PLAN_APPROVAL_KEYS = {
    "schemaVersion",
    "artifactType",
    "planId",
    "sourceHash",
    "approvedBy",
    "approvedAt",
    "qualityPolicy",
    "contentPolicy",
    "note",
}
_PLAN_ID_RE = re.compile(r"^scp_[0-9a-f]{12}$")
_SOURCE_HASH_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class PlanFieldChange:
    """One normalized plan-level field that changed."""

    field: str
    before: Any
    after: Any

    def to_dict(self) -> dict[str, Any]:
        return {"field": self.field, "before": self.before, "after": self.after}


@dataclass(frozen=True, slots=True)
class PlanItemSnapshot:
    """Compact identity and schedule for one normalized plan position."""

    sequence: int
    source: str
    intended_at: datetime | None
    campaign_id: str
    source_hash: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "sequence": self.sequence,
            "source": self.source,
            "intendedAt": _format_utc(self.intended_at) if self.intended_at else None,
            "campaignId": self.campaign_id,
            "sourceHash": self.source_hash,
        }


@dataclass(frozen=True, slots=True)
class PlanItemChange:
    """One added, removed, or modified position in a campaign plan."""

    sequence: int
    change: str
    fields: tuple[str, ...]
    before: PlanItemSnapshot | None
    after: PlanItemSnapshot | None
    campaign_diff: CampaignDiff | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "sequence": self.sequence,
            "change": self.change,
            "fields": list(self.fields),
            "before": self.before.to_dict() if self.before else None,
            "after": self.after.to_dict() if self.after else None,
            "campaignDiff": self.campaign_diff.to_dict() if self.campaign_diff else None,
        }


@dataclass(frozen=True, slots=True)
class CampaignPlanDiff:
    """Deterministic semantic comparison of two validated campaign plans."""

    before_plan_id: str
    after_plan_id: str
    before_source_hash: str
    after_source_hash: str
    fields: tuple[PlanFieldChange, ...]
    items: tuple[PlanItemChange, ...]

    @property
    def changed(self) -> bool:
        return bool(self.fields or self.items)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": 1,
            "changed": self.changed,
            "beforePlanId": self.before_plan_id,
            "afterPlanId": self.after_plan_id,
            "beforeSourceHash": self.before_source_hash,
            "afterSourceHash": self.after_source_hash,
            "fields": [change.to_dict() for change in self.fields],
            "items": [change.to_dict() for change in self.items],
        }


def _snapshot(item: PlannedCampaign) -> PlanItemSnapshot:
    return PlanItemSnapshot(
        sequence=item.sequence,
        source=item.source,
        intended_at=item.intended_at,
        campaign_id=item.bundle.campaign_id,
        source_hash=item.bundle.source_hash,
    )


def diff_campaign_plans(before: CampaignPlan, after: CampaignPlan) -> CampaignPlanDiff:
    """Compare plan metadata, ordered positions, schedules, and campaign semantics."""
    built_before = build_campaign_plan(before)
    built_after = build_campaign_plan(after)
    before_values: dict[str, Any] = {
        "name": built_before.name,
        "requiredPlatforms": list(built_before.required_platforms),
    }
    after_values: dict[str, Any] = {
        "name": built_after.name,
        "requiredPlatforms": list(built_after.required_platforms),
    }
    field_changes = tuple(
        PlanFieldChange(field, before_values[field], after_values[field])
        for field in _PLAN_DIFF_FIELDS
        if before_values[field] != after_values[field]
    )

    item_changes: list[PlanItemChange] = []
    item_count = max(len(built_before.items), len(built_after.items))
    for index in range(item_count):
        old = built_before.items[index] if index < len(built_before.items) else None
        new = built_after.items[index] if index < len(built_after.items) else None
        sequence = index + 1
        if old is None:
            assert new is not None
            item_changes.append(
                PlanItemChange(
                    sequence=sequence,
                    change="added",
                    fields=_PLAN_ITEM_DIFF_FIELDS,
                    before=None,
                    after=_snapshot(new),
                )
            )
            continue
        if new is None:
            item_changes.append(
                PlanItemChange(
                    sequence=sequence,
                    change="removed",
                    fields=_PLAN_ITEM_DIFF_FIELDS,
                    before=_snapshot(old),
                    after=None,
                )
            )
            continue

        fields: list[str] = []
        if old.source != new.source:
            fields.append("source")
        if old.intended_at != new.intended_at:
            fields.append("intendedAt")
        campaign_diff: CampaignDiff | None = None
        if old.bundle.source_hash != new.bundle.source_hash:
            fields.append("campaign")
            campaign_diff = diff_campaigns(
                before.items[index].campaign,
                after.items[index].campaign,
            )
        if fields:
            item_changes.append(
                PlanItemChange(
                    sequence=sequence,
                    change="modified",
                    fields=tuple(fields),
                    before=_snapshot(old),
                    after=_snapshot(new),
                    campaign_diff=campaign_diff,
                )
            )

    return CampaignPlanDiff(
        before_plan_id=built_before.plan_id,
        after_plan_id=built_after.plan_id,
        before_source_hash=built_before.source_hash,
        after_source_hash=built_after.source_hash,
        fields=field_changes,
        items=tuple(item_changes),
    )


@dataclass(frozen=True, slots=True)
class CampaignPlanApproval:
    """Human-readable plan approval metadata; it is not a digital signature."""

    plan_id: str
    source_hash: str
    approved_by: str
    approved_at: datetime
    warnings_as_errors: bool = False
    note: str | None = None
    content_policy: ContentPolicyBinding | None = None

    @property
    def quality_policy(self) -> str:
        return "warnings-as-errors" if self.warnings_as_errors else "errors-only"

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "schemaVersion": 1,
            "artifactType": "plan",
            "planId": self.plan_id,
            "sourceHash": self.source_hash,
            "approvedBy": self.approved_by,
            "approvedAt": _format_utc(self.approved_at),
            "qualityPolicy": self.quality_policy,
        }
        if self.note is not None:
            result["note"] = self.note
        if self.content_policy is not None:
            result["contentPolicy"] = self.content_policy.to_dict()
        return result

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> CampaignPlanApproval:
        issues: list[str] = []
        unknown = sorted(str(key) for key in raw if key not in _PLAN_APPROVAL_KEYS)
        if unknown:
            issues.append(f"unknown plan approval field(s): {', '.join(unknown)}")
        if raw.get("schemaVersion") != 1 or isinstance(raw.get("schemaVersion"), bool):
            issues.append("schemaVersion must be 1")
        if raw.get("artifactType") != "plan":
            issues.append("artifactType must be plan")

        plan_id_value = raw.get("planId")
        plan_id = plan_id_value if isinstance(plan_id_value, str) else ""
        if not _PLAN_ID_RE.fullmatch(plan_id):
            issues.append("planId must be a Samsarix campaign plan ID")
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

        content_policy = None
        if "contentPolicy" in raw:
            content_policy = ContentPolicyBinding.from_dict(
                raw["contentPolicy"], field="contentPolicy", issues=issues
            )

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
            plan_id=plan_id,
            source_hash=source_hash,
            approved_by=approved_by,
            approved_at=approved_at,
            warnings_as_errors=policy == "warnings-as-errors",
            note=note,
            content_policy=content_policy,
        )


@dataclass(frozen=True, slots=True)
class PlanApprovalCheck:
    """Verification result for a plan and a local approval record."""

    plan_id: str
    approval: CampaignPlanApproval
    valid: bool
    issues: tuple[ApprovalIssue, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": 1,
            "valid": self.valid,
            "planId": self.plan_id,
            "approval": self.approval.to_dict(),
            "issues": [issue.to_dict() for issue in self.issues],
        }


def _quality_error_summary(quality_issues: tuple[PlanIssue, ...]) -> str:
    errors = [
        f"item {issue.item}: {issue.message}"
        for issue in quality_issues
        if issue.severity == "error"
    ]
    if len(errors) > 10:
        return ", ".join(errors[:10]) + f", and {len(errors) - 10} more"
    return ", ".join(errors)


def create_campaign_plan_approval(
    bundle: CampaignPlanBundle,
    *,
    approved_by: str,
    approved_at: datetime | None = None,
    warnings_as_errors: bool = False,
    note: str | None = None,
    content_policy: ContentPolicy | None = None,
) -> CampaignPlanApproval:
    """Create plan approval metadata only when the selected quality policy passes."""
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
    quality = check_campaign_plan(
        bundle,
        warnings_as_errors=warnings_as_errors,
        content_policy=content_policy,
    )
    if not quality.publishable:
        issues.append(
            "plan does not pass the selected quality policy: "
            + _quality_error_summary(quality.issues)
        )
    if issues:
        raise ConfigError(issues)
    return CampaignPlanApproval(
        plan_id=bundle.plan_id,
        source_hash=bundle.source_hash,
        approved_by=normalized_approver,
        approved_at=timestamp.astimezone(timezone.utc),
        warnings_as_errors=warnings_as_errors,
        note=normalized_note,
        content_policy=content_policy.binding if content_policy is not None else None,
    )


def load_campaign_plan_approval(path: str | Path) -> CampaignPlanApproval:
    """Load and validate one bounded local plan approval JSON file."""
    return CampaignPlanApproval.from_dict(_load_json_object(path, kind="plan approval"))


def export_campaign_plan_approval(approval: CampaignPlanApproval, path: str | Path) -> Path:
    """Write a plan approval record to a new file without replacing existing evidence."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(approval.to_dict(), ensure_ascii=False, indent=2) + "\n"
    try:
        with destination.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
    except FileExistsError:
        raise ConfigError(
            f"refusing to overwrite existing plan approval file: {destination}"
        ) from None
    return destination


def verify_campaign_plan_approval(
    bundle: CampaignPlanBundle,
    approval: CampaignPlanApproval,
    *,
    content_policy: ContentPolicy | None = None,
) -> PlanApprovalCheck:
    """Verify plan identity and re-run the approval record's quality policy."""
    issues: list[ApprovalIssue] = []
    if approval.source_hash != bundle.source_hash:
        issues.append(
            ApprovalIssue("source-changed", "Plan source no longer matches the approved hash.")
        )
    if approval.plan_id != bundle.plan_id:
        issues.append(ApprovalIssue("plan-id-changed", "Plan ID no longer matches the approval."))
    issues.extend(
        ApprovalIssue(code, message)
        for code, message in content_policy_binding_issues(approval.content_policy, content_policy)
    )
    quality = check_campaign_plan(
        bundle,
        warnings_as_errors=approval.warnings_as_errors,
        content_policy=content_policy,
    )
    if not quality.publishable:
        issues.append(
            ApprovalIssue(
                "quality-policy-failed",
                "Plan no longer passes the quality policy recorded by the approval.",
            )
        )
    return PlanApprovalCheck(
        plan_id=bundle.plan_id,
        approval=approval,
        valid=not issues,
        issues=tuple(issues),
    )
