# Copyright (c) 2026 Samsarix LLC
# SPDX-License-Identifier: MPL-2.0

"""Reusable approval policies and deterministic multi-reviewer plan evidence."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, TypeAlias

from .media_package import CampaignPlanMedia, CampaignPlanMediaBinding
from .models import ConfigError
from .plan_review import (
    CampaignPlanApproval,
    PlanApprovalCheck,
    verify_campaign_plan_approval,
)
from .plans import CampaignPlanBundle
from .policy import ContentPolicy, ContentPolicyBinding
from .review import ApprovalIssue
from .workflow import _load_json_object

MAX_APPROVAL_REQUIREMENTS = 20
MAX_APPROVALS_IN_SET = 50

_POLICY_KEYS = {
    "schemaVersion",
    "name",
    "minimumTotal",
    "distinctReviewers",
    "requirements",
}
_REQUIREMENT_KEYS = {"role", "minimum"}
_SET_KEYS = {
    "schemaVersion",
    "artifactType",
    "approvalSetId",
    "approvalSetHash",
    "planId",
    "sourceHash",
    "approvalPolicy",
    "approvals",
}
_ASSIGNMENT_KEYS = {"role", "approval"}
_ROLE_RE = re.compile(r"^[a-z][a-z0-9-]{0,63}$")
_PLAN_ID_RE = re.compile(r"^scp_[0-9a-f]{12}$")
_SET_ID_RE = re.compile(r"^scas_[0-9a-f]{12}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _normalized_text(value: object, *, field: str, maximum: int, issues: list[str]) -> str:
    if not isinstance(value, str):
        issues.append(f"{field} must be a string")
        return ""
    normalized = unicodedata.normalize("NFC", value).strip()
    if not normalized:
        issues.append(f"{field} must not be empty")
    elif len(normalized) > maximum:
        issues.append(f"{field} must be at most {maximum} characters")
    if any(unicodedata.category(character) in {"Cc", "Cs"} for character in normalized):
        issues.append(f"{field} must be a single line without control characters")
    return normalized


def _bounded_integer(
    value: object,
    *,
    field: str,
    minimum: int,
    maximum: int,
    issues: list[str],
) -> int:
    parsed = value if isinstance(value, int) and not isinstance(value, bool) else 0
    if not minimum <= parsed <= maximum:
        issues.append(f"{field} must be between {minimum} and {maximum}")
    return parsed


@dataclass(frozen=True, slots=True)
class ApprovalRequirement:
    """Minimum number of current approvals assigned to one review role."""

    role: str
    minimum: int

    def to_dict(self) -> dict[str, Any]:
        return {"role": self.role, "minimum": self.minimum}


@dataclass(frozen=True, slots=True)
class ApprovalPolicy:
    """Bounded reusable rules for collecting independent plan approvals."""

    name: str
    minimum_total: int
    distinct_reviewers: bool
    requirements: tuple[ApprovalRequirement, ...]

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> ApprovalPolicy:
        if not isinstance(raw, Mapping):
            raise ConfigError("approval policy must be a JSON object")
        issues: list[str] = []
        unknown = sorted(str(key) for key in raw if key not in _POLICY_KEYS)
        if unknown:
            issues.append(f"unknown approval policy field(s): {', '.join(unknown)}")
        if raw.get("schemaVersion") != 1 or isinstance(raw.get("schemaVersion"), bool):
            issues.append("schemaVersion must be 1")
        name = _normalized_text(raw.get("name"), field="name", maximum=120, issues=issues)
        minimum_total = _bounded_integer(
            raw.get("minimumTotal"),
            field="minimumTotal",
            minimum=1,
            maximum=MAX_APPROVALS_IN_SET,
            issues=issues,
        )
        distinct_value = raw.get("distinctReviewers")
        if not isinstance(distinct_value, bool):
            issues.append("distinctReviewers must be a boolean")
            distinct_reviewers = True
        else:
            distinct_reviewers = distinct_value
        requirements_value = raw.get("requirements")
        requirements: list[ApprovalRequirement] = []
        seen_roles: set[str] = set()
        if not isinstance(requirements_value, list):
            issues.append("requirements must be a non-empty array")
        else:
            if not 1 <= len(requirements_value) <= MAX_APPROVAL_REQUIREMENTS:
                issues.append(
                    "requirements must contain between 1 and " f"{MAX_APPROVAL_REQUIREMENTS} items"
                )
            for index, value in enumerate(requirements_value[:MAX_APPROVAL_REQUIREMENTS]):
                requirement = _parse_requirement(value, index=index, issues=issues)
                if requirement is None:
                    continue
                if requirement.role in seen_roles:
                    issues.append(f"requirements repeats role: {requirement.role}")
                else:
                    seen_roles.add(requirement.role)
                    requirements.append(requirement)
        if sum(requirement.minimum for requirement in requirements) > MAX_APPROVALS_IN_SET:
            issues.append(
                "sum of role minimums must not exceed " f"{MAX_APPROVALS_IN_SET} approvals"
            )
        if issues:
            raise ConfigError(issues)
        return cls(
            name=name,
            minimum_total=minimum_total,
            distinct_reviewers=distinct_reviewers,
            requirements=tuple(sorted(requirements, key=lambda item: item.role)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": 1,
            "name": self.name,
            "minimumTotal": self.minimum_total,
            "distinctReviewers": self.distinct_reviewers,
            "requirements": [requirement.to_dict() for requirement in self.requirements],
        }

    @property
    def source_hash(self) -> str:
        return hashlib.sha256(_canonical_json(self.to_dict())).hexdigest()

    @property
    def policy_id(self) -> str:
        return f"scap_{self.source_hash[:12]}"


def _parse_requirement(
    value: object,
    *,
    index: int,
    issues: list[str],
) -> ApprovalRequirement | None:
    field = f"requirements[{index}]"
    if not isinstance(value, Mapping):
        issues.append(f"{field} must be an object")
        return None
    unknown = sorted(str(key) for key in value if key not in _REQUIREMENT_KEYS)
    if unknown:
        issues.append(f"{field} has unknown field(s): {', '.join(unknown)}")
    role_value = value.get("role")
    role = role_value if isinstance(role_value, str) else ""
    if not _ROLE_RE.fullmatch(role):
        issues.append(f"{field}.role must be a lowercase kebab-case role")
    minimum = _bounded_integer(
        value.get("minimum"),
        field=f"{field}.minimum",
        minimum=1,
        maximum=MAX_APPROVALS_IN_SET,
        issues=issues,
    )
    return ApprovalRequirement(role, minimum)


@dataclass(frozen=True, slots=True)
class CampaignPlanApprovalAssignment:
    """One existing single-reviewer approval assigned to a policy role."""

    role: str
    approval: CampaignPlanApproval

    def to_dict(self) -> dict[str, Any]:
        return {"role": self.role, "approval": self.approval.to_dict()}

    @classmethod
    def from_dict(
        cls,
        raw: object,
        *,
        field: str,
        issues: list[str],
    ) -> CampaignPlanApprovalAssignment | None:
        if not isinstance(raw, Mapping):
            issues.append(f"{field} must be an object")
            return None
        unknown = sorted(str(key) for key in raw if key not in _ASSIGNMENT_KEYS)
        if unknown:
            issues.append(f"{field} has unknown field(s): {', '.join(unknown)}")
        role_value = raw.get("role")
        role = role_value if isinstance(role_value, str) else ""
        if not _ROLE_RE.fullmatch(role):
            issues.append(f"{field}.role must be a lowercase kebab-case role")
        approval_value = raw.get("approval")
        if not isinstance(approval_value, dict):
            issues.append(f"{field}.approval must be a plan approval object")
            return None
        try:
            approval = CampaignPlanApproval.from_dict(approval_value)
        except ConfigError as error:
            issues.extend(f"{field}.approval: {message}" for message in error.issues)
            return None
        return cls(role, approval)


def _assignment_key(assignment: CampaignPlanApprovalAssignment) -> tuple[str, str, str, str]:
    approval = assignment.approval
    return (
        assignment.role,
        approval.approved_at.isoformat(),
        approval.approved_by.casefold(),
        _approval_fingerprint(approval),
    )


def _canonical_json(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )


def _approval_fingerprint(approval: CampaignPlanApproval) -> str:
    return hashlib.sha256(_canonical_json(approval.to_dict())).hexdigest()


def _approval_set_issues(
    policy: ApprovalPolicy,
    assignments: Sequence[CampaignPlanApprovalAssignment],
) -> list[str]:
    issues: list[str] = []
    if not 1 <= len(assignments) <= MAX_APPROVALS_IN_SET:
        issues.append(f"approvals must contain between 1 and {MAX_APPROVALS_IN_SET} items")
        return issues
    required = {requirement.role: requirement.minimum for requirement in policy.requirements}
    counts = {role: 0 for role in required}
    fingerprints: set[str] = set()
    reviewers: set[str] = set()
    first = assignments[0].approval
    for assignment in assignments:
        if assignment.role not in required:
            issues.append(f"approval uses role not declared by policy: {assignment.role}")
        else:
            counts[assignment.role] += 1
        fingerprint = _approval_fingerprint(assignment.approval)
        if fingerprint in fingerprints:
            issues.append("the same approval record must not be assigned more than once")
        fingerprints.add(fingerprint)
        reviewer = assignment.approval.approved_by.casefold()
        if policy.distinct_reviewers and reviewer in reviewers:
            issues.append("approval reviewer labels must be distinct under this policy")
        reviewers.add(reviewer)
        if assignment.approval.plan_id != first.plan_id:
            issues.append("all approvals must reference the same plan ID")
        if assignment.approval.source_hash != first.source_hash:
            issues.append("all approvals must reference the same plan source hash")
        if assignment.approval.warnings_as_errors != first.warnings_as_errors:
            issues.append("all approvals must use the same warning policy")
        if assignment.approval.content_policy != first.content_policy:
            issues.append("all approvals must bind the same content policy")
        if assignment.approval.media != first.media:
            issues.append("all approvals must bind the same exact-media snapshot")
    for role, minimum in required.items():
        if counts[role] < minimum:
            issues.append(f"role {role} requires {minimum} approval(s); found {counts[role]}")
    if len(assignments) < policy.minimum_total:
        issues.append(
            f"policy requires {policy.minimum_total} total approval(s); found {len(assignments)}"
        )
    return issues


@dataclass(frozen=True, slots=True)
class CampaignPlanApprovalSet:
    """Deterministic policy-satisfying collection of current plan approvals."""

    approval_set_id: str
    approval_set_hash: str
    plan_id: str
    source_hash: str
    approval_policy: ApprovalPolicy
    approvals: tuple[CampaignPlanApprovalAssignment, ...]

    def __post_init__(self) -> None:
        if not self.approvals:
            raise ConfigError("plan approval set must contain at least one approval")

    @property
    def approved_at(self) -> datetime:
        return max(assignment.approval.approved_at for assignment in self.approvals)

    @property
    def content_policy(self) -> ContentPolicyBinding | None:
        return self.approvals[0].approval.content_policy

    @property
    def media(self) -> CampaignPlanMediaBinding | None:
        return self.approvals[0].approval.media

    def _core_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": 1,
            "artifactType": "plan-approval-set",
            "planId": self.plan_id,
            "sourceHash": self.source_hash,
            "approvalPolicy": self.approval_policy.to_dict(),
            "approvals": [assignment.to_dict() for assignment in self.approvals],
        }

    def to_dict(self) -> dict[str, Any]:
        core = self._core_dict()
        return {
            "schemaVersion": 1,
            "artifactType": "plan-approval-set",
            "approvalSetId": self.approval_set_id,
            "approvalSetHash": self.approval_set_hash,
            "planId": core["planId"],
            "sourceHash": core["sourceHash"],
            "approvalPolicy": core["approvalPolicy"],
            "approvals": core["approvals"],
        }

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> CampaignPlanApprovalSet:
        if not isinstance(raw, Mapping):
            raise ConfigError("plan approval set must be a JSON object")
        issues: list[str] = []
        unknown = sorted(str(key) for key in raw if key not in _SET_KEYS)
        if unknown:
            issues.append(f"unknown approval set field(s): {', '.join(unknown)}")
        if raw.get("schemaVersion") != 1 or isinstance(raw.get("schemaVersion"), bool):
            issues.append("schemaVersion must be 1")
        if raw.get("artifactType") != "plan-approval-set":
            issues.append("artifactType must be plan-approval-set")
        set_id_value = raw.get("approvalSetId")
        set_id = set_id_value if isinstance(set_id_value, str) else ""
        if not _SET_ID_RE.fullmatch(set_id):
            issues.append("approvalSetId must be a Samsarix plan approval set ID")
        set_hash_value = raw.get("approvalSetHash")
        set_hash = set_hash_value if isinstance(set_hash_value, str) else ""
        if not _SHA256_RE.fullmatch(set_hash):
            issues.append("approvalSetHash must be a lowercase SHA-256 hash")
        plan_id_value = raw.get("planId")
        plan_id = plan_id_value if isinstance(plan_id_value, str) else ""
        if not _PLAN_ID_RE.fullmatch(plan_id):
            issues.append("planId must be a Samsarix campaign plan ID")
        source_hash_value = raw.get("sourceHash")
        source_hash = source_hash_value if isinstance(source_hash_value, str) else ""
        if not _SHA256_RE.fullmatch(source_hash):
            issues.append("sourceHash must be a lowercase SHA-256 hash")
        policy_value = raw.get("approvalPolicy")
        if not isinstance(policy_value, Mapping):
            issues.append("approvalPolicy must be an approval policy object")
            policy = None
        else:
            try:
                policy = ApprovalPolicy.from_dict(policy_value)
            except ConfigError as error:
                issues.extend(f"approvalPolicy: {message}" for message in error.issues)
                policy = None
        assignments_value = raw.get("approvals")
        assignments: list[CampaignPlanApprovalAssignment] = []
        if not isinstance(assignments_value, list):
            issues.append("approvals must be a non-empty array")
        else:
            if not 1 <= len(assignments_value) <= MAX_APPROVALS_IN_SET:
                issues.append(f"approvals must contain between 1 and {MAX_APPROVALS_IN_SET} items")
            for index, value in enumerate(assignments_value[:MAX_APPROVALS_IN_SET]):
                assignment = CampaignPlanApprovalAssignment.from_dict(
                    value,
                    field=f"approvals[{index}]",
                    issues=issues,
                )
                if assignment is not None:
                    assignments.append(assignment)
        normalized_assignments = tuple(sorted(assignments, key=_assignment_key))
        if policy is not None and assignments:
            issues.extend(_approval_set_issues(policy, normalized_assignments))
        if assignments:
            if plan_id != assignments[0].approval.plan_id:
                issues.append("planId does not match embedded approvals")
            if source_hash != assignments[0].approval.source_hash:
                issues.append("sourceHash does not match embedded approvals")
        if not normalized_assignments:
            issues.append("approvals must contain at least one approval")
        if issues:
            raise ConfigError(issues)
        assert policy is not None
        provisional = cls(
            set_id,
            set_hash,
            plan_id,
            source_hash,
            policy,
            normalized_assignments,
        )
        expected_hash = hashlib.sha256(_canonical_json(provisional._core_dict())).hexdigest()
        if set_hash and set_hash != expected_hash:
            issues.append("approvalSetHash does not match canonical approval set content")
        if set_id and set_id != f"scas_{expected_hash[:12]}":
            issues.append("approvalSetId does not match approvalSetHash")
        if issues:
            raise ConfigError(issues)
        return provisional


@dataclass(frozen=True, slots=True)
class PlanApprovalSetCheck:
    """Verification result for a plan and a policy-bound approval set."""

    plan_id: str
    approval_set: CampaignPlanApprovalSet
    valid: bool
    issues: tuple[ApprovalIssue, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": 1,
            "valid": self.valid,
            "planId": self.plan_id,
            "approvalSet": self.approval_set.to_dict(),
            "issues": [issue.to_dict() for issue in self.issues],
        }


CampaignPlanApprovalEvidence: TypeAlias = CampaignPlanApproval | CampaignPlanApprovalSet
PlanApprovalEvidenceCheck: TypeAlias = PlanApprovalCheck | PlanApprovalSetCheck


def create_campaign_plan_approval_set(
    bundle: CampaignPlanBundle,
    approval_policy: ApprovalPolicy,
    approvals: Sequence[CampaignPlanApprovalAssignment],
    *,
    content_policy: ContentPolicy | None = None,
    media: CampaignPlanMedia | None = None,
) -> CampaignPlanApprovalSet:
    """Collect independently valid approvals only when the policy is satisfied."""
    normalized = tuple(sorted(approvals, key=_assignment_key))
    issues = _approval_set_issues(approval_policy, normalized)
    for assignment in normalized:
        check = verify_campaign_plan_approval(
            bundle,
            assignment.approval,
            content_policy=content_policy,
            media=media,
        )
        issues.extend(
            f"{assignment.role} approval by {assignment.approval.approved_by}: {issue.message}"
            for issue in check.issues
        )
    if issues:
        raise ConfigError(issues)
    provisional = CampaignPlanApprovalSet(
        approval_set_id="scas_000000000000",
        approval_set_hash="0" * 64,
        plan_id=bundle.plan_id,
        source_hash=bundle.source_hash,
        approval_policy=approval_policy,
        approvals=normalized,
    )
    set_hash = hashlib.sha256(_canonical_json(provisional._core_dict())).hexdigest()
    return CampaignPlanApprovalSet(
        approval_set_id=f"scas_{set_hash[:12]}",
        approval_set_hash=set_hash,
        plan_id=provisional.plan_id,
        source_hash=provisional.source_hash,
        approval_policy=approval_policy,
        approvals=normalized,
    )


def verify_campaign_plan_approval_set(
    bundle: CampaignPlanBundle,
    approval_set: CampaignPlanApprovalSet,
    *,
    content_policy: ContentPolicy | None = None,
    media: CampaignPlanMedia | None = None,
) -> PlanApprovalSetCheck:
    """Verify every embedded approval and the set's current plan identity."""
    issues: list[ApprovalIssue] = []
    if approval_set.plan_id != bundle.plan_id:
        issues.append(
            ApprovalIssue("plan-id-changed", "Plan ID no longer matches the approval set.")
        )
    if approval_set.source_hash != bundle.source_hash:
        issues.append(
            ApprovalIssue("source-changed", "Plan source no longer matches the approval set hash.")
        )
    try:
        CampaignPlanApprovalSet.from_dict(approval_set.to_dict())
    except ConfigError as error:
        issues.extend(ApprovalIssue("approval-set-invalid", message) for message in error.issues)
    for assignment in approval_set.approvals:
        check = verify_campaign_plan_approval(
            bundle,
            assignment.approval,
            content_policy=content_policy,
            media=media,
        )
        issues.extend(
            ApprovalIssue(
                f"approval-{issue.code}",
                f"{assignment.role} approval by {assignment.approval.approved_by}: {issue.message}",
            )
            for issue in check.issues
        )
    return PlanApprovalSetCheck(bundle.plan_id, approval_set, not issues, tuple(issues))


def verify_campaign_plan_approval_evidence(
    bundle: CampaignPlanBundle,
    approval: CampaignPlanApprovalEvidence,
    *,
    content_policy: ContentPolicy | None = None,
    media: CampaignPlanMedia | None = None,
) -> PlanApprovalEvidenceCheck:
    """Verify either legacy single-reviewer or policy-bound approval evidence."""
    if isinstance(approval, CampaignPlanApprovalSet):
        return verify_campaign_plan_approval_set(
            bundle,
            approval,
            content_policy=content_policy,
            media=media,
        )
    return verify_campaign_plan_approval(
        bundle,
        approval,
        content_policy=content_policy,
        media=media,
    )


def load_approval_policy(path: str | Path) -> ApprovalPolicy:
    """Load and validate one bounded approval policy JSON file."""
    return ApprovalPolicy.from_dict(_load_json_object(path, kind="approval policy"))


def load_campaign_plan_approval_set(path: str | Path) -> CampaignPlanApprovalSet:
    """Load and validate one bounded plan approval set JSON file."""
    return CampaignPlanApprovalSet.from_dict(_load_json_object(path, kind="plan approval set"))


def load_campaign_plan_approval_evidence(path: str | Path) -> CampaignPlanApprovalEvidence:
    """Load strict single-reviewer or approval-set evidence based on artifact type."""
    raw = _load_json_object(path, kind="plan approval evidence")
    if raw.get("artifactType") == "plan-approval-set":
        return CampaignPlanApprovalSet.from_dict(raw)
    return CampaignPlanApproval.from_dict(raw)


def export_campaign_plan_approval_set(
    approval_set: CampaignPlanApprovalSet,
    path: str | Path,
) -> Path:
    """Write a new approval set without replacing existing review evidence."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(approval_set.to_dict(), ensure_ascii=False, indent=2) + "\n"
    try:
        with destination.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
    except FileExistsError:
        raise ConfigError(
            f"refusing to overwrite existing plan approval set file: {destination}"
        ) from None
    return destination
