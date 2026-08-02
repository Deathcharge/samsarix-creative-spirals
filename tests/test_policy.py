from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from samsarix_creative_spirals import (
    ConfigError,
    CampaignBundle,
    ContentPolicy,
    build_campaign,
    build_campaign_plan,
    build_campaign_plan_readiness,
    check_campaign,
    check_campaign_plan,
    create_campaign_approval,
    create_campaign_plan_approval,
    export_campaign_plan_handoff,
    load_campaign_plan,
    load_campaign_plan_handoff,
    load_approval_schema,
    load_content_policy,
    load_content_policy_schema,
    load_readiness_schema,
    load_plan_approval_schema,
    verify_campaign_approval,
    verify_campaign_plan_approval,
    verify_campaign_plan_handoff,
)
from samsarix_creative_spirals.models import CampaignConfig


def _policy(*rules: dict[str, Any], name: str = "Release guardrails") -> ContentPolicy:
    return ContentPolicy.from_dict({"schemaVersion": 1, "name": name, "rules": list(rules)})


def _bundle(campaign_data: dict[str, Any]) -> CampaignBundle:
    return build_campaign(CampaignConfig.from_dict(campaign_data))


def test_policy_normalizes_defaults_and_has_stable_identity() -> None:
    first = _policy({"id": "no-internal", "kind": "blockedPhrase", "phrase": " Internal only "})
    second = ContentPolicy.from_dict(
        {
            "rules": [
                {
                    "phrase": "Internal only",
                    "caseSensitive": False,
                    "severity": "error",
                    "platforms": ["X", "linkedin", "bluesky", "mastodon", "discord"],
                    "kind": "blockedPhrase",
                    "id": "no-internal",
                }
            ],
            "name": "Release guardrails",
            "schemaVersion": 1,
        }
    )

    assert first == second
    assert first.source_hash == second.source_hash
    assert first.policy_id == f"scpol_{first.source_hash[:12]}"
    assert first.binding.to_dict() == {
        "policyId": first.policy_id,
        "sourceHash": first.source_hash,
        "name": "Release guardrails",
    }


def test_policy_checks_final_variants_targets_case_and_severity(
    campaign_data: dict[str, Any],
) -> None:
    campaign_data["body"] = "Public release"
    campaign_data["platformVariants"] = {
        "x": {"body": "INTERNAL ONLY draft"},
        "linkedin": {"body": "Public release without the marker"},
    }
    policy = _policy(
        {
            "id": "no-internal",
            "kind": "blockedPhrase",
            "phrase": "internal only",
            "platforms": ["x"],
        },
        {
            "id": "require-release-link",
            "kind": "requiredPhrase",
            "phrase": "Public release",
            "platforms": ["linkedin"],
            "caseSensitive": True,
        },
        {
            "id": "discourage-made",
            "kind": "blockedPhrase",
            "phrase": "public release",
            "platforms": ["discord"],
            "severity": "warning",
        },
    )

    result = check_campaign(_bundle(campaign_data), content_policy=policy)

    assert result.publishable is False
    assert result.content_policy == policy.binding
    policy_issues = [issue for issue in result.issues if issue.rule_id]
    assert [(issue.rule_id, issue.platform, issue.severity) for issue in policy_issues] == [
        ("no-internal", "x", "error"),
        ("discourage-made", "discord", "warning"),
    ]
    assert policy_issues[0].to_dict()["ruleId"] == "no-internal"
    strict = check_campaign(_bundle(campaign_data), content_policy=policy, warnings_as_errors=True)
    assert next(
        issue for issue in strict.issues if issue.rule_id == "discourage-made"
    ).severity == ("error")


def test_required_phrase_fails_every_targeted_rendered_draft(
    campaign_data: dict[str, Any],
) -> None:
    campaign_data["platforms"] = ["x", "linkedin"]
    policy = _policy(
        {
            "id": "required-disclosure",
            "kind": "requiredPhrase",
            "phrase": "#ad",
        }
    )

    result = check_campaign(_bundle(campaign_data), content_policy=policy)

    assert {issue.platform for issue in result.issues if issue.rule_id} == {"x", "linkedin"}
    assert all(
        issue.code == "policy-required-phrase"
        for issue in result.issues
        if issue.rule_id is not None
    )


@pytest.mark.parametrize(
    ("patch", "message"),
    [
        ({"schemaVersion": False}, "schemaVersion must be 1"),
        ({"extra": True}, "unknown content policy field"),
        ({"name": "\n"}, "name must not be empty"),
        ({"name": "bad\tname"}, "single line"),
        ({"rules": []}, "at least one rule"),
        ({"rules": [{}]}, r"rules\[0\]\.id"),
        (
            {"rules": [{"id": "UPPER", "kind": "blockedPhrase", "phrase": "x"}]},
            "must match",
        ),
        (
            {"rules": [{"id": "r", "kind": "regex", "phrase": "x"}]},
            "blockedPhrase or requiredPhrase",
        ),
        (
            {"rules": [{"id": "r", "kind": "blockedPhrase", "phrase": "\t"}]},
            "phrase must not be empty",
        ),
        (
            {
                "rules": [
                    {
                        "id": "r",
                        "kind": "blockedPhrase",
                        "phrase": "x",
                        "platforms": [],
                    }
                ]
            },
            "at least one platform",
        ),
        (
            {
                "rules": [
                    {
                        "id": "r",
                        "kind": "blockedPhrase",
                        "phrase": "x",
                        "platforms": ["threads"],
                    }
                ]
            },
            "must be one of",
        ),
        (
            {
                "rules": [
                    {
                        "id": "r",
                        "kind": "blockedPhrase",
                        "phrase": "x",
                        "severity": "notice",
                    }
                ]
            },
            "severity must be warning or error",
        ),
        (
            {
                "rules": [
                    {
                        "id": "r",
                        "kind": "blockedPhrase",
                        "phrase": "x",
                        "caseSensitive": 1,
                    }
                ]
            },
            "caseSensitive must be a boolean",
        ),
    ],
)
def test_policy_runtime_rejects_invalid_values(patch: dict[str, Any], message: str) -> None:
    raw: dict[str, Any] = {
        "schemaVersion": 1,
        "name": "Policy",
        "rules": [{"id": "r", "kind": "blockedPhrase", "phrase": "x"}],
    }
    raw.update(patch)

    with pytest.raises(ConfigError, match=message):
        ContentPolicy.from_dict(raw)


def test_policy_rejects_duplicate_ids_and_excessive_rules() -> None:
    duplicate = {"id": "same", "kind": "blockedPhrase", "phrase": "x"}
    with pytest.raises(ConfigError, match="duplicates same"):
        _policy(duplicate, duplicate)
    with pytest.raises(ConfigError, match="at most 50"):
        _policy(
            *(
                {"id": f"rule-{index}", "kind": "blockedPhrase", "phrase": "x"}
                for index in range(51)
            )
        )


def test_policy_loader_rejects_duplicate_keys_and_invalid_json(tmp_path: Path) -> None:
    duplicate = tmp_path / "duplicate.json"
    duplicate.write_text(
        '{"schemaVersion":1,"name":"one","name":"two","rules":[]}',
        encoding="utf-8",
    )
    broken = tmp_path / "broken.json"
    broken.write_text('{"schemaVersion":', encoding="utf-8")

    with pytest.raises(ConfigError, match="duplicate JSON field"):
        load_content_policy(duplicate)
    with pytest.raises(ConfigError, match="invalid content policy JSON"):
        load_content_policy(broken)


def test_policy_schema_is_valid_and_accepts_normalized_source() -> None:
    schema = load_content_policy_schema()
    Draft202012Validator.check_schema(schema)
    policy = _policy({"id": "no-internal", "kind": "blockedPhrase", "phrase": "internal only"})

    Draft202012Validator(schema).validate(policy.to_dict())
    assert not Draft202012Validator(schema).is_valid(
        {
            "schemaVersion": 1,
            "name": "   ",
            "rules": [{"id": "rule", "kind": "blockedPhrase", "phrase": "   "}],
        }
    )


def test_campaign_approval_requires_the_bound_policy(campaign_data: dict[str, Any]) -> None:
    bundle = _bundle(campaign_data)
    policy = _policy({"id": "no-internal", "kind": "blockedPhrase", "phrase": "internal only"})
    changed = _policy({"id": "no-secret", "kind": "blockedPhrase", "phrase": "secret"})
    approval = create_campaign_approval(bundle, approved_by="Reviewer", content_policy=policy)

    assert approval.content_policy == policy.binding
    Draft202012Validator(load_approval_schema()).validate(approval.to_dict())
    assert verify_campaign_approval(bundle, approval, content_policy=policy).valid
    assert [issue.code for issue in verify_campaign_approval(bundle, approval).issues] == [
        "content-policy-required"
    ]
    assert [
        issue.code
        for issue in verify_campaign_approval(bundle, approval, content_policy=changed).issues
    ] == ["content-policy-changed"]

    legacy = create_campaign_approval(bundle, approved_by="Reviewer")
    assert [
        issue.code
        for issue in verify_campaign_approval(bundle, legacy, content_policy=policy).issues
    ] == ["content-policy-unapproved"]


def test_content_policy_binding_parser_rejects_tampering(
    campaign_data: dict[str, Any],
) -> None:
    bundle = _bundle(campaign_data)
    policy = _policy({"id": "no-internal", "kind": "blockedPhrase", "phrase": "internal only"})
    raw = create_campaign_approval(bundle, approved_by="Reviewer", content_policy=policy).to_dict()
    raw["contentPolicy"] = {
        "policyId": "scpol_bad",
        "sourceHash": "ABC",
        "name": "bad\nname",
        "unknown": True,
    }

    with pytest.raises(ConfigError) as exc:
        from samsarix_creative_spirals import CampaignApproval

        CampaignApproval.from_dict(raw)

    message = str(exc.value)
    assert "unknown field" in message
    assert "Samsarix content policy ID" in message
    assert "lowercase SHA-256" in message
    assert "single line" in message


def test_plan_approval_handoff_and_readiness_require_bound_policy(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    campaign_path = tmp_path / "campaign.json"
    campaign_path.write_text(json.dumps(campaign_data), encoding="utf-8")
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "name": "Policy-bound release",
                "items": [
                    {
                        "campaign": "campaign.json",
                        "intendedAt": "2026-08-10T13:00:00Z",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    bundle = build_campaign_plan(load_campaign_plan(plan_path))
    policy = _policy({"id": "no-internal", "kind": "blockedPhrase", "phrase": "internal only"})
    check = check_campaign_plan(bundle, content_policy=policy)
    assert check.publishable and check.content_policy == policy.binding

    approved_at = datetime(2026, 8, 3, 12, tzinfo=timezone.utc)
    approval = create_campaign_plan_approval(
        bundle,
        approved_by="Reviewer",
        approved_at=approved_at,
        content_policy=policy,
    )
    Draft202012Validator(load_plan_approval_schema()).validate(approval.to_dict())
    assert verify_campaign_plan_approval(bundle, approval, content_policy=policy).valid
    assert [issue.code for issue in verify_campaign_plan_approval(bundle, approval).issues] == [
        "content-policy-required"
    ]

    packet_path = export_campaign_plan_handoff(
        bundle,
        approval,
        tmp_path / "handoffs",
        generated_at=datetime(2026, 8, 4, 12, tzinfo=timezone.utc),
        content_policy=policy,
    )
    packet = load_campaign_plan_handoff(packet_path)
    assert verify_campaign_plan_handoff(bundle, packet, content_policy=policy).valid
    assert "approval-content-policy-required" in {
        issue.code for issue in verify_campaign_plan_handoff(bundle, packet).issues
    }

    readiness = build_campaign_plan_readiness(
        bundle,
        handoff=packet,
        assessed_at=datetime(2026, 8, 5, 12, tzinfo=timezone.utc),
        content_policy=policy,
    )
    assert readiness.stage == "handoff-ready"
    assert readiness.content_policy == policy.binding
    Draft202012Validator(load_readiness_schema()).validate(readiness.to_dict())
