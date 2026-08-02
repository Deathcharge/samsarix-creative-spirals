from __future__ import annotations

import json
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator, FormatChecker

from samsarix_creative_spirals import (
    CampaignPlanApproval,
    CampaignPlanBundle,
    ConfigError,
    build_campaign_plan,
    build_campaign_plan_readiness,
    create_campaign_plan_approval,
    export_campaign_plan_handoff,
    export_campaign_plan_readiness_html,
    load_campaign_plan,
    load_campaign_plan_handoff,
    load_readiness_schema,
    load_plan_approval_schema,
    render_campaign_plan_readiness_html,
)

ASSESSMENT = datetime(2026, 8, 5, 12, tzinfo=timezone.utc)
APPROVED = datetime(2026, 8, 4, 12, tzinfo=timezone.utc)


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _bundle(
    root: Path,
    campaign_data: dict[str, Any],
    *,
    intended_at: str | None = "2026-08-10T13:00:00Z",
) -> CampaignPlanBundle:
    _write_json(root / "campaign.json", campaign_data)
    item: dict[str, Any] = {"campaign": "campaign.json"}
    if intended_at is not None:
        item["intendedAt"] = intended_at
    plan = root / "plan.json"
    _write_json(
        plan,
        {
            "schemaVersion": 1,
            "name": "Release readiness",
            "requiredPlatforms": ["x", "linkedin", "discord"],
            "items": [item],
        },
    )
    return build_campaign_plan(load_campaign_plan(plan))


def _approval(bundle: CampaignPlanBundle) -> CampaignPlanApproval:
    return create_campaign_plan_approval(
        bundle,
        approved_by="Launch reviewer",
        approved_at=APPROVED,
        note="Copy and schedule reviewed.",
    )


def test_readiness_without_evidence_is_schema_valid_and_ready_for_approval(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    bundle = _bundle(tmp_path, campaign_data)

    report = build_campaign_plan_readiness(bundle, assessed_at=ASSESSMENT)
    payload = report.to_dict()

    assert report.stage == "ready-for-approval"
    assert report.ready is False
    assert report.meets("quality") is True
    assert report.meets("approval") is False
    assert payload["counts"] == {
        "items": 1,
        "scheduled": 1,
        "platformDrafts": 3,
        "issues": len(payload["issues"]),
    }
    Draft202012Validator(load_readiness_schema(), format_checker=FormatChecker()).validate(payload)


def test_readiness_applies_quality_and_schedule_policies(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    unscheduled = _bundle(tmp_path / "unscheduled", campaign_data, intended_at=None)
    optional = build_campaign_plan_readiness(unscheduled, assessed_at=ASSESSMENT)
    required = build_campaign_plan_readiness(
        unscheduled, assessed_at=ASSESSMENT, require_scheduled=True
    )
    strict = build_campaign_plan_readiness(
        _bundle(tmp_path / "strict", campaign_data),
        assessed_at=ASSESSMENT,
        warnings_as_errors=True,
    )
    past = build_campaign_plan_readiness(
        _bundle(tmp_path / "past", campaign_data),
        assessed_at=datetime(2026, 8, 10, 13, tzinfo=timezone.utc),
    )

    assert optional.stage == "ready-for-approval"
    assert optional.schedule_complete is False and optional.schedule_ready is True
    assert required.stage == "schedule-blocked"
    assert required.meets("quality") is False
    assert strict.stage == "quality-blocked"
    assert past.stage == "schedule-blocked"
    assert any(issue.code == "schedule-past" for issue in past.issues)


def test_readiness_tracks_current_and_stale_approval(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    bundle = _bundle(tmp_path, campaign_data)
    approval = _approval(bundle)

    current = build_campaign_plan_readiness(bundle, approval=approval, assessed_at=ASSESSMENT)
    stale = build_campaign_plan_readiness(
        bundle,
        approval=replace(approval, source_hash="0" * 64),
        assessed_at=ASSESSMENT,
    )

    assert current.stage == "approved"
    assert current.approval_status == "valid"
    assert current.to_dict()["approval"]["approvedBy"] == "Launch reviewer"
    assert current.meets("approval") is True
    assert current.meets("handoff") is False
    assert stale.stage == "approval-invalid"
    assert stale.approval_status == "invalid"
    assert any(issue.code == "approval-source-changed" for issue in stale.issues)
    Draft202012Validator(load_readiness_schema(), format_checker=FormatChecker()).validate(
        current.to_dict()
    )


def test_readiness_uses_embedded_approval_and_verifies_exact_handoff(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    bundle = _bundle(tmp_path, campaign_data)
    approval = _approval(bundle)
    packet_path = export_campaign_plan_handoff(
        bundle,
        approval,
        tmp_path / "handoffs",
        generated_at=datetime(2026, 8, 5, 10, tzinfo=timezone.utc),
    )
    packet = load_campaign_plan_handoff(packet_path)

    ready = build_campaign_plan_readiness(bundle, handoff=packet, assessed_at=ASSESSMENT)
    mismatch = build_campaign_plan_readiness(
        bundle,
        approval=replace(approval, approved_by="Different reviewer"),
        handoff=packet,
        assessed_at=ASSESSMENT,
    )
    (packet_path / "adapter.json").write_bytes((packet_path / "adapter.json").read_bytes() + b"\n")
    tampered = build_campaign_plan_readiness(bundle, handoff=packet, assessed_at=ASSESSMENT)

    assert ready.stage == "handoff-ready" and ready.ready is True
    assert ready.approval_status == "valid" and ready.handoff_status == "valid"
    Draft202012Validator(load_readiness_schema(), format_checker=FormatChecker()).validate(
        ready.to_dict()
    )
    assert mismatch.stage == "handoff-invalid"
    assert any(issue.code == "approval-handoff-mismatch" for issue in mismatch.issues)
    assert tampered.stage == "handoff-invalid"
    assert any(issue.code.startswith("handoff-artifact-") for issue in tampered.issues)


def test_readiness_requires_timezone_aware_assessment(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    bundle = _bundle(tmp_path, campaign_data)
    with pytest.raises(ConfigError, match="timezone"):
        build_campaign_plan_readiness(bundle, assessed_at=datetime(2026, 8, 5, 12))


def test_html_report_is_offline_escaped_and_exclusive(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    campaign_data["name"] = "Release <script>alert(1)</script>"
    campaign_data["body"] = "Draft </pre><script>alert('draft')</script>"
    bundle = _bundle(tmp_path, campaign_data)
    approval = create_campaign_plan_approval(
        bundle,
        approved_by="Reviewer <img src=x onerror=alert(1)>",
        approved_at=APPROVED,
    )
    report = build_campaign_plan_readiness(bundle, approval=approval, assessed_at=ASSESSMENT)

    rendered = render_campaign_plan_readiness_html(report, bundle)
    output = tmp_path / "reports" / "readiness.html"
    assert "Content-Security-Policy" in rendered
    assert "default-src 'none'" in rendered
    assert "<script" not in rendered.lower()
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in rendered
    assert "&lt;/pre&gt;&lt;script&gt;" in rendered
    assert "Reviewer &lt;img src=x onerror=alert(1)&gt;" in rendered
    assert "Launch ready: No" in rendered
    assert "No network resources or scripts are used" in rendered

    assert export_campaign_plan_readiness_html(report, bundle, output) == output
    assert output.read_text(encoding="utf-8") == rendered
    with pytest.raises(ConfigError, match="refusing to overwrite"):
        export_campaign_plan_readiness_html(report, bundle, output)


def test_readiness_schema_is_a_valid_packaged_contract() -> None:
    schema = load_readiness_schema()
    Draft202012Validator.check_schema(schema)
    assert schema["properties"]["artifactType"]["const"] == "plan-readiness"
    assert "handoff-ready" in schema["properties"]["stage"]["enum"]


def test_embedded_approval_schema_stays_synchronized() -> None:
    readiness_approval = load_readiness_schema()["$defs"]["approval"]
    plan_approval = load_plan_approval_schema()

    assert readiness_approval == {
        key: plan_approval[key]
        for key in ("type", "additionalProperties", "required", "properties")
    }
