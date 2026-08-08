from __future__ import annotations

import json
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, cast

import pytest
from jsonschema import Draft202012Validator

from samsarix_creative_spirals.approval_policy import (
    ApprovalPolicy,
    ApprovalRequirement,
    CampaignPlanApprovalAssignment,
    CampaignPlanApprovalSet,
    create_campaign_plan_approval_set,
    export_campaign_plan_approval_set,
    load_campaign_plan_approval_evidence,
    load_campaign_plan_approval_set,
    verify_campaign_plan_approval_evidence,
    verify_campaign_plan_approval_set,
)
from samsarix_creative_spirals.models import ConfigError
from samsarix_creative_spirals.media_package import CampaignPlanMediaBinding
from samsarix_creative_spirals.plan_review import create_campaign_plan_approval
from samsarix_creative_spirals.plans import build_campaign_plan, load_campaign_plan
from samsarix_creative_spirals.policy import ContentPolicyBinding

APPROVED_AT = datetime(2026, 8, 4, 12, tzinfo=timezone.utc)


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _bundle(tmp_path: Path, campaign_data: dict[str, Any]) -> Any:
    campaign = dict(campaign_data)
    campaign["platforms"] = ["x", "linkedin"]
    _write_json(tmp_path / "campaigns" / "release.json", campaign)
    _write_json(
        tmp_path / "plan.json",
        {
            "schemaVersion": 1,
            "name": "Governed release",
            "requiredPlatforms": ["x", "linkedin"],
            "items": [{"campaign": "campaigns/release.json"}],
        },
    )
    return build_campaign_plan(load_campaign_plan(tmp_path / "plan.json"))


def _policy(*, total: int = 2, distinct: bool = True) -> ApprovalPolicy:
    return ApprovalPolicy.from_dict(
        {
            "schemaVersion": 1,
            "name": "Release approval policy",
            "minimumTotal": total,
            "distinctReviewers": distinct,
            "requirements": [
                {"role": "legal", "minimum": 1},
                {"role": "brand", "minimum": 1},
            ],
        }
    )


def _assignments(bundle: Any) -> tuple[CampaignPlanApprovalAssignment, ...]:
    brand = create_campaign_plan_approval(
        bundle,
        approved_by="Brand reviewer",
        approved_at=APPROVED_AT,
    )
    legal = create_campaign_plan_approval(
        bundle,
        approved_by="Legal reviewer",
        approved_at=APPROVED_AT + timedelta(minutes=5),
    )
    return (
        CampaignPlanApprovalAssignment("brand", brand),
        CampaignPlanApprovalAssignment("legal", legal),
    )


def test_policy_is_normalized_and_content_addressed() -> None:
    policy = _policy()

    assert [requirement.role for requirement in policy.requirements] == ["brand", "legal"]
    assert policy.policy_id == f"scap_{policy.source_hash[:12]}"
    assert ApprovalPolicy.from_dict(policy.to_dict()) == policy


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"extra": True}, "unknown approval policy"),
        ({"schemaVersion": 2}, "schemaVersion"),
        ({"name": "\t"}, "name must not be empty"),
        ({"minimumTotal": True}, "minimumTotal"),
        ({"distinctReviewers": "yes"}, "distinctReviewers"),
        ({"requirements": []}, "requirements must contain"),
        (
            {
                "requirements": [
                    {"role": "brand", "minimum": 1},
                    {"role": "brand", "minimum": 1},
                ]
            },
            "repeats role",
        ),
        ({"requirements": [{"role": "Brand", "minimum": 1}]}, "kebab-case"),
        (
            {
                "requirements": [
                    {"role": "brand", "minimum": 50},
                    {"role": "legal", "minimum": 1},
                ]
            },
            "sum of role minimums",
        ),
    ],
)
def test_policy_rejects_invalid_source(change: dict[str, Any], message: str) -> None:
    source = _policy().to_dict()
    source.update(change)

    with pytest.raises(ConfigError, match=message):
        ApprovalPolicy.from_dict(source)


def test_approval_set_is_deterministic_and_schema_valid(
    tmp_path: Path,
    campaign_data: dict[str, Any],
) -> None:
    bundle = _bundle(tmp_path, campaign_data)
    assignments = _assignments(bundle)

    first = create_campaign_plan_approval_set(bundle, _policy(), assignments)
    second = create_campaign_plan_approval_set(bundle, _policy(), tuple(reversed(assignments)))

    assert first == second
    assert first.approval_set_id == f"scas_{first.approval_set_hash[:12]}"
    assert first.approved_at == APPROVED_AT + timedelta(minutes=5)
    assert [assignment.role for assignment in first.approvals] == ["brand", "legal"]
    Draft202012Validator(_load_schema("plan-approval-set.schema.json")).validate(first.to_dict())
    Draft202012Validator(_load_schema("approval-policy.schema.json")).validate(
        first.approval_policy.to_dict()
    )


def _load_schema(name: str) -> dict[str, Any]:
    path = Path(__file__).parents[1] / "samsarix_creative_spirals" / name
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def test_approval_set_tie_breaker_is_input_order_independent(
    tmp_path: Path,
    campaign_data: dict[str, Any],
) -> None:
    bundle = _bundle(tmp_path, campaign_data)
    first = create_campaign_plan_approval(
        bundle,
        approved_by="Shared reviewer",
        approved_at=APPROVED_AT,
        note="First discipline",
    )
    second = create_campaign_plan_approval(
        bundle,
        approved_by="Shared reviewer",
        approved_at=APPROVED_AT,
        note="Second discipline",
    )
    policy = ApprovalPolicy.from_dict(
        {
            "schemaVersion": 1,
            "name": "Two reviews in one role",
            "minimumTotal": 2,
            "distinctReviewers": False,
            "requirements": [{"role": "review", "minimum": 2}],
        }
    )
    assignments = (
        CampaignPlanApprovalAssignment("review", first),
        CampaignPlanApprovalAssignment("review", second),
    )

    forward = create_campaign_plan_approval_set(bundle, policy, assignments)
    reverse = create_campaign_plan_approval_set(bundle, policy, tuple(reversed(assignments)))

    assert forward == reverse


def test_approval_set_export_load_and_generic_verify(
    tmp_path: Path,
    campaign_data: dict[str, Any],
) -> None:
    bundle = _bundle(tmp_path, campaign_data)
    approval_set = create_campaign_plan_approval_set(bundle, _policy(), _assignments(bundle))
    path = export_campaign_plan_approval_set(approval_set, tmp_path / "approval-set.json")

    loaded = load_campaign_plan_approval_set(path)
    generic = load_campaign_plan_approval_evidence(path)
    check = verify_campaign_plan_approval_evidence(bundle, generic)

    assert loaded == approval_set == generic
    assert check.valid is True
    assert check.to_dict()["approvalSet"]["approvalSetId"] == approval_set.approval_set_id
    with pytest.raises(ConfigError, match="refusing to overwrite"):
        export_campaign_plan_approval_set(approval_set, path)


@pytest.mark.parametrize(
    ("assignments_factory", "message"),
    [
        (lambda assignments: assignments[:1], "role legal requires"),
        (
            lambda assignments: (
                assignments[0],
                replace(
                    assignments[1],
                    approval=replace(assignments[1].approval, approved_by="brand REVIEWER"),
                ),
            ),
            "reviewer labels must be distinct",
        ),
        (
            lambda assignments: (assignments[0], replace(assignments[0], role="legal")),
            "same approval record",
        ),
        (
            lambda assignments: (assignments[0], replace(assignments[1], role="security")),
            "role not declared",
        ),
    ],
)
def test_create_set_rejects_unsatisfied_policy(
    tmp_path: Path,
    campaign_data: dict[str, Any],
    assignments_factory: Any,
    message: str,
) -> None:
    bundle = _bundle(tmp_path, campaign_data)

    with pytest.raises(ConfigError, match=message):
        create_campaign_plan_approval_set(
            bundle,
            _policy(),
            assignments_factory(_assignments(bundle)),
        )


def test_policy_can_allow_one_reviewer_in_multiple_roles(
    tmp_path: Path,
    campaign_data: dict[str, Any],
) -> None:
    bundle = _bundle(tmp_path, campaign_data)
    assignments = _assignments(bundle)
    same_reviewer = replace(assignments[1].approval, approved_by="Brand Reviewer")

    approval_set = create_campaign_plan_approval_set(
        bundle,
        _policy(distinct=False),
        (assignments[0], replace(assignments[1], approval=same_reviewer)),
    )

    assert len(approval_set.approvals) == 2


def test_create_set_rejects_stale_approval(
    tmp_path: Path,
    campaign_data: dict[str, Any],
) -> None:
    bundle = _bundle(tmp_path, campaign_data)
    assignments = _assignments(bundle)
    stale = replace(assignments[1].approval, source_hash="0" * 64)

    with pytest.raises(ConfigError, match="source no longer matches"):
        create_campaign_plan_approval_set(
            bundle,
            _policy(),
            (assignments[0], replace(assignments[1], approval=stale)),
        )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        (
            "warnings_as_errors",
            True,
            "same warning policy",
        ),
        (
            "content_policy",
            ContentPolicyBinding("scpol_000000000000", "0" * 64, "Different policy"),
            "same content policy",
        ),
        (
            "media",
            CampaignPlanMediaBinding("scm_000000000000", "0" * 64, 1, 10),
            "same exact-media snapshot",
        ),
    ],
)
def test_set_rejects_mixed_policy_or_media_bindings(
    tmp_path: Path,
    campaign_data: dict[str, Any],
    field: str,
    value: object,
    message: str,
) -> None:
    bundle = _bundle(tmp_path, campaign_data)
    assignments = _assignments(bundle)
    if field == "warnings_as_errors":
        changed = replace(assignments[1].approval, warnings_as_errors=cast(bool, value))
    elif field == "content_policy":
        changed = replace(
            assignments[1].approval,
            content_policy=cast(ContentPolicyBinding, value),
        )
    else:
        changed = replace(
            assignments[1].approval,
            media=cast(CampaignPlanMediaBinding, value),
        )

    with pytest.raises(ConfigError, match=message):
        create_campaign_plan_approval_set(
            bundle,
            _policy(),
            (assignments[0], replace(assignments[1], approval=changed)),
        )


def test_verifier_reports_changed_plan(
    tmp_path: Path,
    campaign_data: dict[str, Any],
) -> None:
    bundle = _bundle(tmp_path, campaign_data)
    approval_set = create_campaign_plan_approval_set(bundle, _policy(), _assignments(bundle))
    changed = replace(bundle, source_hash="f" * 64)

    check = verify_campaign_plan_approval_set(changed, approval_set)

    assert check.valid is False
    assert {issue.code for issue in check.issues} >= {"source-changed", "approval-source-changed"}


@pytest.mark.parametrize("field", ["approvalSetId", "approvalSetHash", "planId", "sourceHash"])
def test_approval_set_rejects_tampered_identity(
    tmp_path: Path,
    campaign_data: dict[str, Any],
    field: str,
) -> None:
    bundle = _bundle(tmp_path, campaign_data)
    value = create_campaign_plan_approval_set(bundle, _policy(), _assignments(bundle)).to_dict()
    value[field] = {
        "approvalSetId": "scas_" + "0" * 12,
        "approvalSetHash": "0" * 64,
        "planId": "scp_" + "0" * 12,
        "sourceHash": "0" * 64,
    }[field]

    with pytest.raises(ConfigError):
        CampaignPlanApprovalSet.from_dict(value)


def test_set_rejects_mismatched_embedded_binding(
    tmp_path: Path,
    campaign_data: dict[str, Any],
) -> None:
    bundle = _bundle(tmp_path, campaign_data)
    value = create_campaign_plan_approval_set(bundle, _policy(), _assignments(bundle)).to_dict()
    value["approvals"][1]["approval"]["planId"] = "scp_000000000000"

    with pytest.raises(ConfigError, match="same plan ID"):
        CampaignPlanApprovalSet.from_dict(value)


def test_policy_rejects_additional_malformed_shapes() -> None:
    invalid_sources: tuple[Any, ...] = (
        [],
        {
            **_policy().to_dict(),
            "name": "x" * 121,
        },
        {
            **_policy().to_dict(),
            "name": "Release\npolicy",
        },
        {
            **_policy().to_dict(),
            "requirements": None,
        },
        {
            **_policy().to_dict(),
            "requirements": [None],
        },
        {
            **_policy().to_dict(),
            "requirements": [{"role": "brand", "minimum": 1, "extra": True}],
        },
    )

    for source in invalid_sources:
        with pytest.raises(ConfigError):
            ApprovalPolicy.from_dict(cast(Any, source))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("extra", True),
        ("schemaVersion", 2),
        ("artifactType", "plan"),
        ("approvalSetHash", "A" * 64),
        ("sourceHash", "A" * 64),
        ("approvalPolicy", None),
        ("approvalPolicy", {"schemaVersion": 1}),
        ("approvals", None),
    ],
)
def test_set_rejects_invalid_top_level_shapes(
    tmp_path: Path,
    campaign_data: dict[str, Any],
    field: str,
    value: object,
) -> None:
    bundle = _bundle(tmp_path, campaign_data)
    raw = create_campaign_plan_approval_set(bundle, _policy(), _assignments(bundle)).to_dict()
    raw[field] = value

    with pytest.raises(ConfigError):
        CampaignPlanApprovalSet.from_dict(raw)


@pytest.mark.parametrize(
    "assignment",
    [
        None,
        {"role": "brand", "approval": None},
        {"role": "Brand", "approval": {}},
        {"role": "brand", "approval": {"artifactType": "plan"}},
        {"role": "brand", "approval": {}, "extra": True},
    ],
)
def test_set_rejects_malformed_assignments(
    tmp_path: Path,
    campaign_data: dict[str, Any],
    assignment: object,
) -> None:
    bundle = _bundle(tmp_path, campaign_data)
    raw = create_campaign_plan_approval_set(bundle, _policy(), _assignments(bundle)).to_dict()
    raw["approvals"] = [assignment]

    with pytest.raises(ConfigError):
        CampaignPlanApprovalSet.from_dict(raw)


def test_verifier_reports_tampered_set_and_plan_id(
    tmp_path: Path,
    campaign_data: dict[str, Any],
) -> None:
    bundle = _bundle(tmp_path, campaign_data)
    approval_set = create_campaign_plan_approval_set(bundle, _policy(), _assignments(bundle))
    tampered = replace(approval_set, approval_set_hash="0" * 64)
    changed_bundle = replace(bundle, plan_id="scp_000000000000")

    result = verify_campaign_plan_approval_set(changed_bundle, tampered)

    assert result.valid is False
    assert {issue.code for issue in result.issues} >= {
        "plan-id-changed",
        "approval-set-invalid",
    }


def test_approval_set_public_constructor_rejects_empty_approvals() -> None:
    with pytest.raises(ConfigError, match="at least one approval"):
        CampaignPlanApprovalSet(
            approval_set_id="scas_000000000000",
            approval_set_hash="0" * 64,
            plan_id="scp_000000000000",
            source_hash="0" * 64,
            approval_policy=_policy(),
            approvals=(),
        )


def test_requirement_dataclass_has_stable_shape() -> None:
    assert ApprovalRequirement("legal", 2).to_dict() == {"role": "legal", "minimum": 2}
