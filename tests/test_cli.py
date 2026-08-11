from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from media_helpers import png_image
from samsarix_creative_spirals.cli import main


def _write_campaign(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data), encoding="utf-8")


def _write_policy(path: Path, phrase: str = "internal only") -> None:
    path.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "name": "Release guardrails",
                "rules": [
                    {
                        "id": "no-internal",
                        "kind": "blockedPhrase",
                        "phrase": phrase,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def test_cli_core_journey(tmp_path: Path, capsys: Any, campaign_data: dict[str, Any]) -> None:
    config_path = tmp_path / "campaign.json"
    assert main(["init", str(config_path)]) == 0
    assert config_path.is_file()
    capsys.readouterr()

    assert main(["validate", str(config_path), "--json"]) == 0
    validation = json.loads(capsys.readouterr().out)
    assert validation["valid"] is True

    assert main(["preview", str(config_path)]) == 0
    assert "[x]" in capsys.readouterr().out

    output = tmp_path / "outbox"
    assert main(["export", str(config_path), "--output", str(output)]) == 0
    assert list(output.glob("*/manifest.json"))


def test_cli_json_preview(tmp_path: Path, capsys: Any, campaign_data: dict[str, Any]) -> None:
    campaign_data["media"] = [{"path": "media/launch.png", "altText": "Launch review dashboard"}]
    path = tmp_path / "campaign.json"
    _write_campaign(path, campaign_data)

    assert main(["preview", str(path), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["campaignId"].startswith("scs_")
    assert payload["media"][0]["path"] == "media/launch.png"
    assert payload["drafts"][0]["media"][0]["altText"] == "Launch review dashboard"
    assert len(payload["drafts"]) == 3


def test_cli_preview_uses_platform_native_variants(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    campaign_data: dict[str, Any],
) -> None:
    campaign_data["platformVariants"] = {
        "linkedin": {
            "title": "LinkedIn release",
            "body": "A detailed release note for professional teams.",
            "hashtags": ["release_ops"],
        }
    }
    path = tmp_path / "campaign.json"
    _write_campaign(path, campaign_data)

    assert main(["preview", str(path), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    drafts = {draft["platform"]: draft for draft in payload["drafts"]}

    assert "LinkedIn release" in drafts["linkedin"]["content"]
    assert "#release_ops" in drafts["linkedin"]["content"]
    assert campaign_data["body"] in drafts["x"]["content"]


def test_cli_reports_validation_failure(
    tmp_path: Path, capsys: Any, campaign_data: dict[str, Any]
) -> None:
    campaign_data["platforms"] = ["unknown"]
    path = tmp_path / "campaign.json"
    _write_campaign(path, campaign_data)

    assert main(["validate", str(path)]) == 1
    assert "error:" in capsys.readouterr().err


def test_init_refuses_to_overwrite(tmp_path: Path, capsys: Any) -> None:
    path = tmp_path / "campaign.json"
    path.write_text("keep me", encoding="utf-8")

    assert main(["init", str(path)]) == 1
    assert path.read_text(encoding="utf-8") == "keep me"
    assert "refusing to overwrite" in capsys.readouterr().err


def test_cli_without_command_returns_usage_error(capsys: Any) -> None:
    assert main([]) == 2
    assert "usage:" in capsys.readouterr().err


def test_cli_prints_and_writes_schema(tmp_path: Path, capsys: Any) -> None:
    assert main(["schema"]) == 0
    schema = json.loads(capsys.readouterr().out)
    assert schema["title"] == "Samsarix Creative Spirals campaign"

    output = tmp_path / "schemas" / "campaign.schema.json"
    assert main(["schema", "--output", str(output)]) == 0
    capsys.readouterr()
    assert json.loads(output.read_text(encoding="utf-8"))["additionalProperties"] is False

    assert main(["schema", "--output", str(output)]) == 1
    assert "refusing to overwrite" in capsys.readouterr().err


def test_cli_check_supports_quality_gate_exit_codes(
    tmp_path: Path, capsys: Any, campaign_data: dict[str, Any]
) -> None:
    path = tmp_path / "campaign.json"
    _write_campaign(path, campaign_data)

    assert main(["check", str(path), "--json"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["publishable"] is True
    assert report["issues"]

    assert main(["check", str(path), "--warnings-as-errors"]) == 3
    assert "Quality check failed" in capsys.readouterr().out

    campaign_data["body"] = "long content " * 100
    _write_campaign(path, campaign_data)
    assert main(["check", str(path), "--json"]) == 3
    report = json.loads(capsys.readouterr().out)
    assert any(issue["code"] == "truncated" for issue in report["issues"])


def test_cli_plan_journey(tmp_path: Path, capsys: Any, campaign_data: dict[str, Any]) -> None:
    campaign_path = tmp_path / "campaign.json"
    plan_path = tmp_path / "plan.json"
    _write_campaign(campaign_path, campaign_data)
    plan_path.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "name": "Release sequence",
                "requiredPlatforms": ["x", "linkedin", "discord"],
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

    assert main(["plan", "validate", str(plan_path), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["items"] == 1

    assert main(["plan", "preview", str(plan_path)]) == 0
    assert "Release sequence" in capsys.readouterr().out

    assert main(["plan", "check", str(plan_path), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["publishable"] is True

    output = tmp_path / "plan-outbox"
    assert main(["plan", "export", str(plan_path), "--output", str(output), "--json"]) == 0
    exported = Path(json.loads(capsys.readouterr().out)["path"])
    assert (exported / "calendar.ics").is_file()
    assert (exported / "csv" / "x.csv").is_file()


def test_cli_emits_plan_schema(capsys: Any) -> None:
    assert main(["schema", "--kind", "plan"]) == 0
    schema = json.loads(capsys.readouterr().out)
    assert schema["title"] == "Samsarix Creative Spirals campaign plan"


def test_cli_creates_and_verifies_source_bound_plan_review(
    tmp_path: Path, capsys: Any, campaign_data: dict[str, Any]
) -> None:
    campaign = tmp_path / "campaign.json"
    plan = tmp_path / "plan.json"
    review = tmp_path / "review.json"
    _write_campaign(campaign, campaign_data)
    plan.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "name": "Review workflow",
                "items": [{"campaign": "campaign.json"}],
            }
        ),
        encoding="utf-8",
    )

    assert (
        main(
            [
                "plan",
                "review",
                "create",
                str(plan),
                "--decision",
                "request-changes",
                "--by",
                "Brand reviewer",
                "--at",
                "2026-08-08T15:30:00Z",
                "--finding",
                "The opening claim needs evidence.",
                "--item",
                "1",
                "--platform",
                "linkedin",
                "--suggestion",
                "Link the benchmark or narrow the claim.",
                "--output",
                str(review),
                "--json",
            ]
        )
        == 0
    )
    created = json.loads(capsys.readouterr().out)
    assert created["review"]["artifactType"] == "plan-review"
    assert created["review"]["reviewId"].startswith("scr_")
    assert created["review"]["findings"][0]["platform"] == "linkedin"

    assert main(["plan", "review", "verify", str(plan), str(review), "--json"]) == 0
    verified = json.loads(capsys.readouterr().out)
    assert verified["valid"] is True
    assert verified["blocking"] is True
    assert (
        main(
            [
                "plan",
                "review",
                "verify",
                str(plan),
                str(review),
                "--fail-on-blocking",
                "--json",
            ]
        )
        == 4
    )
    assert json.loads(capsys.readouterr().out)["blocking"] is True

    campaign_data["body"] = "A revised and supported launch claim."
    _write_campaign(campaign, campaign_data)
    assert main(["plan", "review", "verify", str(plan), str(review), "--json"]) == 4
    stale = json.loads(capsys.readouterr().out)
    assert stale["valid"] is False
    assert stale["blocking"] is False


def test_cli_review_rejects_ambiguous_finding_options(
    tmp_path: Path, capsys: Any, campaign_data: dict[str, Any]
) -> None:
    campaign = tmp_path / "campaign.json"
    plan = tmp_path / "plan.json"
    _write_campaign(campaign, campaign_data)
    plan.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "name": "Review workflow",
                "items": [{"campaign": "campaign.json"}],
            }
        ),
        encoding="utf-8",
    )
    base = [
        "plan",
        "review",
        "create",
        str(plan),
        "--decision",
        "comment",
        "--by",
        "Reviewer",
    ]
    assert main([*base, "--finding", "One", "--finding", "Two", "--suggestion", "Edit"]) == 1
    assert "exactly one --finding" in capsys.readouterr().err
    assert main([*base, "--finding", "Targeted", "--platform", "x"]) == 1
    assert "platform requires an item" in capsys.readouterr().err
    assert main([*base, "--finding", "Observation", "--at", "yesterday"]) == 1
    timestamp_error = capsys.readouterr().err
    assert "reviewed_at" in timestamp_error
    assert "approved_at" not in timestamp_error


def test_cli_emits_plan_review_schema(capsys: Any) -> None:
    assert main(["schema", "--kind", "plan-review"]) == 0
    schema = json.loads(capsys.readouterr().out)
    assert schema["properties"]["artifactType"]["const"] == "plan-review"
    assert schema["properties"]["findings"]["maxItems"] == 50


def test_cli_writes_plan_schema_with_kind_aware_message(tmp_path: Path, capsys: Any) -> None:
    output = tmp_path / "plan.schema.json"

    assert main(["schema", "--kind", "plan", "--output", str(output)]) == 0

    assert f"Wrote plan schema to {output}" in capsys.readouterr().out
    assert json.loads(output.read_text(encoding="utf-8"))["title"].endswith("campaign plan")


def test_cli_plan_status_supports_evidence_html_and_ci_gates(
    tmp_path: Path, capsys: Any, campaign_data: dict[str, Any]
) -> None:
    campaign = tmp_path / "campaign.json"
    plan = tmp_path / "plan.json"
    approval = tmp_path / "approval.json"
    handoff_root = tmp_path / "handoffs"
    html = tmp_path / "status.html"
    _write_campaign(campaign, campaign_data)
    plan.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "name": "Status sequence",
                "requiredPlatforms": ["x", "linkedin", "discord"],
                "items": [{"campaign": "campaign.json", "intendedAt": "2026-08-10T13:00:00Z"}],
            }
        ),
        encoding="utf-8",
    )

    assert main(["plan", "status", str(plan), "--at", "2026-08-05T12:00:00Z", "--json"]) == 0
    initial = json.loads(capsys.readouterr().out)
    assert initial["stage"] == "ready-for-approval"
    assert (
        main(
            [
                "plan",
                "status",
                str(plan),
                "--at",
                "2026-08-05T12:00:00Z",
                "--require-stage",
                "approval",
            ]
        )
        == 4
    )
    capsys.readouterr()

    assert (
        main(
            [
                "plan",
                "approval",
                "create",
                str(plan),
                "--by",
                "Launch reviewer",
                "--at",
                "2026-08-04T12:00:00Z",
                "--output",
                str(approval),
            ]
        )
        == 0
    )
    capsys.readouterr()
    assert (
        main(
            [
                "plan",
                "status",
                str(plan),
                "--approval",
                str(approval),
                "--at",
                "2026-08-05T12:00:00Z",
                "--require-stage",
                "approval",
                "--json",
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["stage"] == "approved"
    assert (
        main(
            [
                "plan",
                "handoff",
                "create",
                str(plan),
                str(approval),
                "--at",
                "2026-08-05T10:00:00Z",
                "--output",
                str(handoff_root),
                "--json",
            ]
        )
        == 0
    )
    handoff_path = json.loads(capsys.readouterr().out)["path"]
    assert (
        main(
            [
                "plan",
                "status",
                str(plan),
                "--handoff",
                handoff_path,
                "--at",
                "2026-08-05T12:00:00Z",
                "--require-stage",
                "handoff",
                "--html",
                str(html),
                "--json",
            ]
        )
        == 0
    )
    ready = json.loads(capsys.readouterr().out)
    assert ready["stage"] == "handoff-ready"
    assert html.is_file()


def test_cli_plan_status_quality_gate_and_readiness_schema(
    tmp_path: Path, capsys: Any, campaign_data: dict[str, Any]
) -> None:
    campaign = tmp_path / "campaign.json"
    plan = tmp_path / "plan.json"
    _write_campaign(campaign, campaign_data)
    plan.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "name": "Unscheduled sequence",
                "items": [{"campaign": "campaign.json"}],
            }
        ),
        encoding="utf-8",
    )
    assert (
        main(
            [
                "plan",
                "status",
                str(plan),
                "--at",
                "2026-08-05T12:00:00Z",
                "--require-scheduled",
                "--require-stage",
                "quality",
                "--json",
            ]
        )
        == 3
    )
    assert json.loads(capsys.readouterr().out)["stage"] == "schedule-blocked"

    assert main(["schema", "--kind", "readiness"]) == 0
    schema = json.loads(capsys.readouterr().out)
    assert schema["properties"]["artifactType"]["const"] == "plan-readiness"


def test_cli_diff_supports_human_json_and_optional_exit_code(
    tmp_path: Path, capsys: Any, campaign_data: dict[str, Any]
) -> None:
    before = tmp_path / "before.json"
    after = tmp_path / "after.json"
    _write_campaign(before, campaign_data)
    revised = dict(campaign_data)
    revised["body"] = "Revised campaign copy"
    _write_campaign(after, revised)

    assert main(["diff", str(before), str(after)]) == 0
    assert "field body" in capsys.readouterr().out

    assert main(["diff", str(before), str(after), "--json", "--exit-code"]) == 4
    payload = json.loads(capsys.readouterr().out)
    assert payload["changed"] is True
    assert payload["fields"][0]["field"] == "body"

    assert main(["diff", str(before), str(before), "--exit-code"]) == 0
    assert "No semantic changes" in capsys.readouterr().out


def test_cli_approval_create_verify_and_stale_exit(
    tmp_path: Path, capsys: Any, campaign_data: dict[str, Any]
) -> None:
    campaign = tmp_path / "campaign.json"
    approval = tmp_path / "approval.json"
    _write_campaign(campaign, campaign_data)

    assert (
        main(
            [
                "approval",
                "create",
                str(campaign),
                "--by",
                "Release reviewer",
                "--at",
                "2026-08-02T12:30:00Z",
                "--output",
                str(approval),
                "--json",
            ]
        )
        == 0
    )
    created = json.loads(capsys.readouterr().out)
    assert created["approval"]["approvedBy"] == "Release reviewer"
    assert approval.is_file()

    assert main(["approval", "verify", str(campaign), str(approval), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["valid"] is True

    campaign_data["body"] = "Changed after approval"
    _write_campaign(campaign, campaign_data)
    assert main(["approval", "verify", str(campaign), str(approval)]) == 4
    assert "Approval invalid" in capsys.readouterr().out


def test_cli_approval_uses_default_output_and_refuses_failed_quality(
    tmp_path: Path, capsys: Any, campaign_data: dict[str, Any]
) -> None:
    campaign = tmp_path / "campaign.json"
    _write_campaign(campaign, campaign_data)

    assert main(["approval", "create", str(campaign), "--by", "Reviewer"]) == 0
    capsys.readouterr()
    assert Path(f"{campaign}.approval.json").is_file()

    strict_campaign = tmp_path / "strict.json"
    _write_campaign(strict_campaign, campaign_data)
    assert (
        main(
            [
                "approval",
                "create",
                str(strict_campaign),
                "--by",
                "Reviewer",
                "--warnings-as-errors",
            ]
        )
        == 1
    )
    assert "selected quality policy" in capsys.readouterr().err


def test_cli_emits_approval_schema(capsys: Any) -> None:
    assert main(["schema", "--kind", "approval"]) == 0
    schema = json.loads(capsys.readouterr().out)
    assert schema["properties"]["artifactType"]["const"] == "campaign"


def test_cli_emits_adapter_schema(capsys: Any) -> None:
    assert main(["schema", "--kind", "adapter"]) == 0
    schema = json.loads(capsys.readouterr().out)
    assert schema["properties"]["schemaVersion"]["const"] == 2
    assert schema["properties"]["contract"]["const"] == "samsarix.plan-drafts"


def test_cli_plan_diff_and_approval_journey(
    tmp_path: Path, capsys: Any, campaign_data: dict[str, Any]
) -> None:
    campaign = tmp_path / "campaign.json"
    before = tmp_path / "before-plan.json"
    after = tmp_path / "after-plan.json"
    approval = tmp_path / "plan.approval.json"
    _write_campaign(campaign, campaign_data)
    base_plan = {
        "schemaVersion": 1,
        "name": "Release sequence",
        "items": [
            {
                "campaign": "campaign.json",
                "intendedAt": "2026-08-10T13:00:00Z",
            }
        ],
    }
    before.write_text(json.dumps(base_plan), encoding="utf-8")
    revised_plan = dict(base_plan)
    revised_plan["items"] = [
        {
            "campaign": "campaign.json",
            "intendedAt": "2026-08-10T14:00:00Z",
        }
    ]
    after.write_text(json.dumps(revised_plan), encoding="utf-8")

    assert main(["plan", "diff", str(before), str(after)]) == 0
    assert "item 1: modified (intendedAt)" in capsys.readouterr().out

    assert main(["plan", "diff", str(before), str(after), "--json", "--exit-code"]) == 4
    assert json.loads(capsys.readouterr().out)["items"][0]["fields"] == ["intendedAt"]

    assert (
        main(
            [
                "plan",
                "approval",
                "create",
                str(after),
                "--by",
                "Launch reviewer",
                "--at",
                "2026-08-03T14:15:00Z",
                "--output",
                str(approval),
                "--json",
            ]
        )
        == 0
    )
    created = json.loads(capsys.readouterr().out)
    assert created["approval"]["artifactType"] == "plan"
    assert created["approval"]["approvedBy"] == "Launch reviewer"

    assert main(["plan", "approval", "verify", str(after), str(approval), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["valid"] is True

    after.write_text(json.dumps(base_plan), encoding="utf-8")
    assert main(["plan", "approval", "verify", str(after), str(approval)]) == 4
    assert "Plan approval invalid" in capsys.readouterr().out


def test_cli_plan_approval_uses_default_output_and_quality_gate(
    tmp_path: Path, capsys: Any, campaign_data: dict[str, Any]
) -> None:
    campaign = tmp_path / "campaign.json"
    plan = tmp_path / "plan.json"
    _write_campaign(campaign, campaign_data)
    plan.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "name": "Release sequence",
                "items": [{"campaign": "campaign.json"}],
            }
        ),
        encoding="utf-8",
    )

    assert main(["plan", "approval", "create", str(plan), "--by", "Reviewer"]) == 0
    capsys.readouterr()
    assert Path(f"{plan}.approval.json").is_file()

    strict_plan = tmp_path / "strict-plan.json"
    strict_plan.write_text(plan.read_text(encoding="utf-8"), encoding="utf-8")
    assert (
        main(
            [
                "plan",
                "approval",
                "create",
                str(strict_plan),
                "--by",
                "Reviewer",
                "--warnings-as-errors",
            ]
        )
        == 1
    )
    assert "selected quality policy" in capsys.readouterr().err


def test_cli_emits_plan_approval_schema(capsys: Any) -> None:
    assert main(["schema", "--kind", "plan-approval"]) == 0
    schema = json.loads(capsys.readouterr().out)
    assert schema["properties"]["artifactType"]["const"] == "plan"


def test_cli_creates_and_verifies_approved_handoff(
    tmp_path: Path, capsys: Any, campaign_data: dict[str, Any]
) -> None:
    campaign = tmp_path / "campaign.json"
    plan = tmp_path / "plan.json"
    approval = tmp_path / "plan.approval.json"
    outbox = tmp_path / "handoff-outbox"
    _write_campaign(campaign, campaign_data)
    plan.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "name": "Release sequence",
                "requiredPlatforms": ["x", "linkedin", "discord"],
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
    assert (
        main(
            [
                "plan",
                "approval",
                "create",
                str(plan),
                "--by",
                "Launch reviewer",
                "--at",
                "2026-08-03T14:15:00Z",
                "--output",
                str(approval),
                "--json",
            ]
        )
        == 0
    )
    capsys.readouterr()

    assert (
        main(
            [
                "plan",
                "handoff",
                "create",
                str(plan),
                str(approval),
                "--at",
                "2026-08-04T09:30:00Z",
                "--output",
                str(outbox),
                "--json",
            ]
        )
        == 0
    )
    created = json.loads(capsys.readouterr().out)
    packet = Path(created["path"])
    assert created["handoff"]["artifactType"] == "plan-handoff"
    assert packet.is_dir()

    assert main(["plan", "handoff", "verify", str(plan), str(packet), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["valid"] is True

    adapter = packet / "adapter.json"
    payload = adapter.read_bytes()
    adapter.write_bytes(payload.replace(b"{", b"[", 1))
    assert main(["plan", "handoff", "verify", str(plan), str(packet)]) == 4
    assert "Approved handoff invalid" in capsys.readouterr().out
    assert main(["plan", "handoff", "verify", str(plan), str(packet), "--json"]) == 4
    invalid = json.loads(capsys.readouterr().out)
    assert any(issue["code"] == "artifact-content-changed" for issue in invalid["issues"])


def test_cli_emits_handoff_schema(capsys: Any) -> None:
    assert main(["schema", "--kind", "handoff"]) == 0
    schema = json.loads(capsys.readouterr().out)
    assert schema["properties"]["artifactType"]["const"] == "plan-handoff"


def test_cli_collects_policy_approvals_into_handoff_and_readiness(
    tmp_path: Path, capsys: Any, campaign_data: dict[str, Any]
) -> None:
    campaign = tmp_path / "campaign.json"
    plan = tmp_path / "plan.json"
    policy = tmp_path / "approval-policy.json"
    brand = tmp_path / "brand.approval.json"
    legal = tmp_path / "legal.approval.json"
    approval_set = tmp_path / "approval-set.json"
    _write_campaign(campaign, campaign_data)
    plan.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "name": "Governed release",
                "requiredPlatforms": ["x", "linkedin", "discord"],
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
    policy.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "name": "Brand and legal release review",
                "minimumTotal": 2,
                "distinctReviewers": True,
                "requirements": [
                    {"role": "brand", "minimum": 1},
                    {"role": "legal", "minimum": 1},
                ],
            }
        ),
        encoding="utf-8",
    )
    for reviewer, timestamp, output in (
        ("Brand reviewer", "2026-08-03T14:15:00Z", brand),
        ("Legal reviewer", "2026-08-03T15:00:00Z", legal),
    ):
        assert (
            main(
                [
                    "plan",
                    "approval",
                    "create",
                    str(plan),
                    "--by",
                    reviewer,
                    "--at",
                    timestamp,
                    "--output",
                    str(output),
                    "--json",
                ]
            )
            == 0
        )
        capsys.readouterr()

    assert (
        main(
            [
                "plan",
                "approval",
                "collect",
                str(plan),
                "--approval-policy",
                str(policy),
                "--approval",
                f"legal={legal}",
                "--approval",
                f"brand={brand}",
                "--output",
                str(approval_set),
                "--json",
            ]
        )
        == 0
    )
    collected = json.loads(capsys.readouterr().out)
    assert collected["approvalSet"]["artifactType"] == "plan-approval-set"
    assert [item["role"] for item in collected["approvalSet"]["approvals"]] == [
        "brand",
        "legal",
    ]
    assert main(["plan", "approval", "verify", str(plan), str(approval_set), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["valid"] is True

    outbox = tmp_path / "handoffs"
    assert (
        main(
            [
                "plan",
                "handoff",
                "create",
                str(plan),
                str(approval_set),
                "--at",
                "2026-08-04T09:30:00Z",
                "--output",
                str(outbox),
                "--json",
            ]
        )
        == 0
    )
    packet = Path(json.loads(capsys.readouterr().out)["path"])
    assert json.loads((packet / "approval.json").read_text())["approvalSetId"].startswith("scas_")
    assert (
        main(
            [
                "plan",
                "status",
                str(plan),
                "--handoff",
                str(packet),
                "--at",
                "2026-08-05T12:00:00Z",
                "--require-stage",
                "handoff",
                "--json",
            ]
        )
        == 0
    )
    status = json.loads(capsys.readouterr().out)
    assert status["stage"] == "handoff-ready"
    assert status["approval"]["artifactType"] == "plan-approval-set"
    ledger = tmp_path / "publication.json"
    assert (
        main(
            [
                "plan",
                "publication",
                "init",
                str(plan),
                str(packet),
                "--at",
                "2026-08-04T10:00:00Z",
                "--output",
                str(ledger),
                "--json",
            ]
        )
        == 0
    )
    publication = json.loads(capsys.readouterr().out)
    assert publication["publication"]["handoffId"].startswith("sch_")
    assert len(publication["publication"]["records"]) == 3


def test_cli_rejects_unsatisfied_or_malformed_approval_collection(
    tmp_path: Path, capsys: Any, campaign_data: dict[str, Any]
) -> None:
    campaign = tmp_path / "campaign.json"
    plan = tmp_path / "plan.json"
    approval = tmp_path / "approval.json"
    policy = tmp_path / "policy.json"
    _write_campaign(campaign, campaign_data)
    plan.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "name": "Incomplete review",
                "items": [{"campaign": "campaign.json"}],
            }
        ),
        encoding="utf-8",
    )
    policy.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "name": "Two roles",
                "minimumTotal": 2,
                "distinctReviewers": True,
                "requirements": [
                    {"role": "brand", "minimum": 1},
                    {"role": "legal", "minimum": 1},
                ],
            }
        ),
        encoding="utf-8",
    )
    assert (
        main(
            [
                "plan",
                "approval",
                "create",
                str(plan),
                "--by",
                "Only reviewer",
                "--output",
                str(approval),
            ]
        )
        == 0
    )
    capsys.readouterr()
    base = [
        "plan",
        "approval",
        "collect",
        str(plan),
        "--approval-policy",
        str(policy),
        "--approval",
    ]
    assert main([*base, str(approval)]) == 1
    assert "ROLE=PATH" in capsys.readouterr().err
    assert main([*base, f"brand={approval}"]) == 1
    assert "role legal requires" in capsys.readouterr().err


def test_cli_emits_approval_policy_schemas(capsys: Any) -> None:
    assert main(["schema", "--kind", "approval-policy"]) == 0
    policy = json.loads(capsys.readouterr().out)
    assert policy["properties"]["minimumTotal"]["maximum"] == 50
    assert main(["schema", "--kind", "plan-approval-set"]) == 0
    approval_set = json.loads(capsys.readouterr().out)
    assert approval_set["properties"]["artifactType"]["const"] == "plan-approval-set"


def test_cli_binds_packages_and_verifies_exact_media(
    tmp_path: Path, capsys: Any, campaign_data: dict[str, Any]
) -> None:
    campaign_data["media"] = [
        {
            "path": "media/launch.png",
            "altText": "Launch dashboard",
            "platforms": ["x", "linkedin"],
        }
    ]
    campaign = tmp_path / "campaigns" / "release.json"
    campaign.parent.mkdir()
    _write_campaign(campaign, campaign_data)
    image = campaign.parent / "media" / "launch.png"
    image.parent.mkdir()
    image.write_bytes(png_image())
    plan = tmp_path / "plan.json"
    plan.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "name": "Media release",
                "requiredPlatforms": ["x", "linkedin"],
                "items": [
                    {
                        "campaign": "campaigns/release.json",
                        "intendedAt": "2026-08-10T13:00:00Z",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    approval = tmp_path / "approval.json"
    assert (
        main(
            [
                "plan",
                "approval",
                "create",
                str(plan),
                "--by",
                "Visual reviewer",
                "--at",
                "2026-08-03T14:15:00Z",
                "--include-media",
                "--output",
                str(approval),
                "--json",
            ]
        )
        == 0
    )
    created = json.loads(capsys.readouterr().out)
    assert created["approval"]["media"]["assetCount"] == 1
    assert main(["plan", "approval", "verify", str(plan), str(approval)]) == 0
    capsys.readouterr()

    outbox = tmp_path / "handoffs"
    assert (
        main(
            [
                "plan",
                "handoff",
                "create",
                str(plan),
                str(approval),
                "--at",
                "2026-08-04T09:30:00Z",
                "--output",
                str(outbox),
                "--json",
            ]
        )
        == 0
    )
    packet = Path(json.loads(capsys.readouterr().out)["path"])
    assert (packet / "media-index.json").is_file()
    assert len(list((packet / "media").iterdir())) == 1
    assert main(["plan", "handoff", "verify", str(plan), str(packet), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["valid"] is True

    image.write_bytes(png_image()[:-1] + b"x")
    assert main(["plan", "approval", "verify", str(plan), str(approval)]) == 1
    assert "PNG" in capsys.readouterr().err
    assert main(["plan", "handoff", "verify", str(plan), str(packet)]) == 0


def test_cli_emits_media_package_schema(capsys: Any) -> None:
    assert main(["schema", "--kind", "media-package"]) == 0
    schema = json.loads(capsys.readouterr().out)
    assert schema["properties"]["contract"]["const"] == "samsarix.handoff-media"
    assert schema["properties"]["totalBytes"]["maximum"] == 100_000_000


def test_cli_initializes_verifies_and_gates_publication_ledger(
    tmp_path: Path, capsys: Any, campaign_data: dict[str, Any]
) -> None:
    campaign = tmp_path / "campaign.json"
    plan = tmp_path / "plan.json"
    approval = tmp_path / "plan.approval.json"
    ledger = tmp_path / "publication.json"
    _write_campaign(campaign, campaign_data)
    plan.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "name": "Publication release",
                "requiredPlatforms": ["x", "linkedin", "discord"],
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
    assert (
        main(
            [
                "plan",
                "approval",
                "create",
                str(plan),
                "--by",
                "Launch reviewer",
                "--at",
                "2026-08-03T14:15:00Z",
                "--output",
                str(approval),
                "--json",
            ]
        )
        == 0
    )
    capsys.readouterr()
    assert (
        main(
            [
                "plan",
                "handoff",
                "create",
                str(plan),
                str(approval),
                "--at",
                "2026-08-04T09:30:00Z",
                "--output",
                str(tmp_path / "handoffs"),
                "--json",
            ]
        )
        == 0
    )
    packet = Path(json.loads(capsys.readouterr().out)["path"])

    assert (
        main(
            [
                "plan",
                "publication",
                "init",
                str(plan),
                str(packet),
                "--at",
                "2026-08-04T10:00:00Z",
                "--output",
                str(ledger),
                "--json",
            ]
        )
        == 0
    )
    initialized = json.loads(capsys.readouterr().out)
    assert initialized["publicationId"].startswith("scpub_")
    assert len(initialized["publication"]["records"]) == 3

    assert (
        main(
            [
                "plan",
                "publication",
                "verify",
                str(plan),
                str(packet),
                str(ledger),
                "--at",
                "2026-08-05T12:00:00Z",
                "--json",
            ]
        )
        == 4
    )
    pending = json.loads(capsys.readouterr().out)
    assert pending["current"] is True and pending["complete"] is False

    payload = json.loads(ledger.read_text(encoding="utf-8"))
    for index, record in enumerate(payload["records"]):
        record.update(
            {
                "status": "published",
                "recordedBy": "Release operator",
                "occurredAt": "2026-08-10T14:00:00Z",
                "url": f"https://social.example/post/{index + 1}",
            }
        )
    ledger.write_text(json.dumps(payload), encoding="utf-8")

    assert (
        main(
            [
                "plan",
                "publication",
                "verify",
                str(plan),
                str(packet),
                str(ledger),
                "--at",
                "2026-08-11T12:00:00Z",
                "--json",
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["complete"] is True
    assert (
        main(
            [
                "plan",
                "status",
                str(plan),
                "--handoff",
                str(packet),
                "--publication",
                str(ledger),
                "--at",
                "2026-08-11T12:00:00Z",
                "--require-stage",
                "publication",
                "--json",
            ]
        )
        == 0
    )
    status = json.loads(capsys.readouterr().out)
    assert status["stage"] == "publication-complete"
    assert status["publicationCounts"]["published"] == 3
    assert (
        main(
            [
                "plan",
                "status",
                str(plan),
                "--handoff",
                str(packet),
                "--publication",
                str(ledger),
                "--at",
                "2026-08-11T12:00:00Z",
                "--require-stage",
                "quality",
                "--json",
            ]
        )
        == 0
    )
    capsys.readouterr()


def test_cli_emits_publication_schema(capsys: Any) -> None:
    assert main(["schema", "--kind", "publication"]) == 0
    schema = json.loads(capsys.readouterr().out)
    assert schema["properties"]["artifactType"]["const"] == "plan-publication"


def test_cli_content_policy_validation_check_and_bound_approval(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    campaign_data: dict[str, Any],
) -> None:
    campaign = tmp_path / "campaign.json"
    policy = tmp_path / "policy.json"
    approval = tmp_path / "approval.json"
    _write_campaign(campaign, campaign_data)
    _write_policy(policy)

    assert main(["policy", "validate", str(policy), "--json"]) == 0
    validated = json.loads(capsys.readouterr().out)
    assert validated["contentPolicy"]["policyId"].startswith("scpol_")

    assert main(["schema", "--kind", "content-policy"]) == 0
    assert json.loads(capsys.readouterr().out)["title"].endswith("content policy")

    assert main(["check", str(campaign), "--policy", str(policy), "--json"]) == 0
    checked = json.loads(capsys.readouterr().out)
    assert checked["contentPolicy"] == validated["contentPolicy"]

    assert (
        main(
            [
                "approval",
                "create",
                str(campaign),
                "--policy",
                str(policy),
                "--by",
                "Reviewer",
                "--at",
                "2026-08-03T12:00:00Z",
                "--output",
                str(approval),
                "--json",
            ]
        )
        == 0
    )
    created = json.loads(capsys.readouterr().out)
    assert created["approval"]["contentPolicy"] == validated["contentPolicy"]

    assert main(["approval", "verify", str(campaign), str(approval), "--json"]) == 4
    missing = json.loads(capsys.readouterr().out)
    assert missing["issues"][0]["code"] == "content-policy-required"
    assert (
        main(
            [
                "approval",
                "verify",
                str(campaign),
                str(approval),
                "--policy",
                str(policy),
                "--json",
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["valid"] is True

    _write_policy(policy, phrase="core workflow")
    assert main(["check", str(campaign), "--policy", str(policy), "--json"]) == 3
    blocked = json.loads(capsys.readouterr().out)
    assert blocked["issues"][-1]["ruleId"] == "no-internal"
