from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator, FormatChecker

from samsarix_creative_spirals import (
    CampaignPlanApproval,
    ConfigError,
    build_campaign_plan,
    create_campaign_plan_approval,
    diff_campaign_plans,
    export_campaign_plan_approval,
    load_campaign_plan,
    load_campaign_plan_approval,
    load_plan_approval_schema,
    verify_campaign_plan_approval,
)


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _write_plan(
    root: Path,
    campaign_data: dict[str, Any],
    *,
    name: str = "Release sequence",
    required_platforms: list[str] | None = None,
    intended_at: str = "2026-08-10T13:00:00Z",
    extra_items: list[dict[str, Any]] | None = None,
) -> Path:
    _write_json(root / "campaigns" / "release.json", campaign_data)
    items: list[dict[str, Any]] = [
        {"campaign": "campaigns/release.json", "intendedAt": intended_at}
    ]
    if extra_items:
        items.extend(extra_items)
    plan: dict[str, Any] = {
        "schemaVersion": 1,
        "name": name,
        "items": items,
    }
    if required_platforms is not None:
        plan["requiredPlatforms"] = required_platforms
    path = root / "plan.json"
    _write_json(path, plan)
    return path


def test_plan_diff_ignores_equivalent_normalization(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    before_path = _write_plan(
        tmp_path / "before",
        campaign_data,
        required_platforms=["x", "linkedin"],
        intended_at="2026-08-10T09:00:00-04:00",
    )
    equivalent = dict(campaign_data)
    equivalent["name"] = f"  {campaign_data['name']}  "
    equivalent["platforms"] = ["X", "LinkedIn", "Discord"]
    after_path = _write_plan(
        tmp_path / "after",
        equivalent,
        name="  Release sequence  ",
        required_platforms=["X", "LinkedIn"],
        intended_at="2026-08-10T13:00:00Z",
    )

    result = diff_campaign_plans(
        load_campaign_plan(before_path),
        load_campaign_plan(after_path),
    )

    assert result.changed is False
    assert result.before_plan_id == result.after_plan_id
    assert result.fields == ()
    assert result.items == ()


def test_plan_diff_reports_metadata_schedule_and_nested_campaign_changes(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    before_path = _write_plan(
        tmp_path / "before",
        campaign_data,
        required_platforms=["x"],
    )
    revised = dict(campaign_data)
    revised["body"] = "Revised launch message"
    after_path = _write_plan(
        tmp_path / "after",
        revised,
        name="Renamed sequence",
        required_platforms=["x", "linkedin"],
        intended_at="2026-08-10T14:00:00Z",
        extra_items=[{"campaign": "campaigns/release.json"}],
    )

    result = diff_campaign_plans(
        load_campaign_plan(before_path),
        load_campaign_plan(after_path),
    )
    payload = result.to_dict()

    assert result.changed is True
    assert [change.field for change in result.fields] == ["name", "requiredPlatforms"]
    assert result.items[0].change == "modified"
    assert result.items[0].fields == ("intendedAt", "campaign")
    assert result.items[0].campaign_diff is not None
    assert [change.field for change in result.items[0].campaign_diff.fields] == ["body"]
    assert result.items[1].change == "added"
    assert payload["items"][0]["before"]["intendedAt"] == "2026-08-10T13:00:00Z"
    assert payload["items"][0]["campaignDiff"]["changed"] is True
    assert payload["beforeSourceHash"] != payload["afterSourceHash"]


def test_plan_diff_reports_source_only_and_removed_positions(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    before_root = tmp_path / "before"
    after_root = tmp_path / "after"
    for root in (before_root, after_root):
        _write_json(root / "campaigns" / "release.json", campaign_data)
        _write_json(root / "campaigns" / "alias.json", campaign_data)
    _write_json(
        before_root / "plan.json",
        {
            "schemaVersion": 1,
            "name": "Release sequence",
            "items": [
                {"campaign": "campaigns/release.json"},
                {"campaign": "campaigns/release.json"},
            ],
        },
    )
    _write_json(
        after_root / "plan.json",
        {
            "schemaVersion": 1,
            "name": "Release sequence",
            "items": [{"campaign": "campaigns/alias.json"}],
        },
    )

    result = diff_campaign_plans(
        load_campaign_plan(before_root / "plan.json"),
        load_campaign_plan(after_root / "plan.json"),
    )

    assert result.items[0].change == "modified"
    assert result.items[0].fields == ("source",)
    assert result.items[0].campaign_diff is None
    assert result.items[1].change == "removed"
    assert result.items[1].after is None


def test_create_export_load_and_verify_plan_approval(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    plan_path = _write_plan(tmp_path, campaign_data, required_platforms=["x"])
    bundle = build_campaign_plan(load_campaign_plan(plan_path))
    timestamp = datetime(2026, 8, 3, 14, 15, tzinfo=timezone.utc)
    approval = create_campaign_plan_approval(
        bundle,
        approved_by="Launch reviewer",
        approved_at=timestamp,
        note="Schedule, channels, and copy reviewed.",
    )
    path = export_campaign_plan_approval(approval, tmp_path / "plan.approval.json")

    loaded = load_campaign_plan_approval(path)
    result = verify_campaign_plan_approval(bundle, loaded)

    assert loaded == approval
    assert loaded.to_dict()["artifactType"] == "plan"
    assert loaded.to_dict()["approvedAt"] == "2026-08-03T14:15:00Z"
    assert result.valid is True
    assert result.to_dict()["issues"] == []
    payload = approval.to_dict()
    Draft202012Validator(
        load_plan_approval_schema(),
        format_checker=FormatChecker(),
    ).validate(payload)
    assert CampaignPlanApproval.from_dict(payload) == approval

    with pytest.raises(ConfigError, match="refusing to overwrite"):
        export_campaign_plan_approval(approval, path)


def test_plan_approval_invalidates_on_schedule_and_campaign_changes(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    plan_path = _write_plan(tmp_path, campaign_data)
    original = build_campaign_plan(load_campaign_plan(plan_path))
    approval = create_campaign_plan_approval(original, approved_by="Reviewer")
    _write_plan(
        tmp_path,
        {**campaign_data, "body": "Changed after approval"},
        intended_at="2026-08-10T15:00:00Z",
    )

    result = verify_campaign_plan_approval(
        build_campaign_plan(load_campaign_plan(plan_path)),
        approval,
    )

    assert result.valid is False
    assert [issue.code for issue in result.issues] == ["source-changed", "plan-id-changed"]

    _write_plan(
        tmp_path,
        {
            **campaign_data,
            "platformVariants": {"discord": {"body": "Changed community copy"}},
        },
    )
    variant_result = verify_campaign_plan_approval(
        build_campaign_plan(load_campaign_plan(plan_path)),
        approval,
    )
    assert [issue.code for issue in variant_result.issues] == [
        "source-changed",
        "plan-id-changed",
    ]


def test_plan_review_propagates_platform_variant_changes(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    before_path = _write_plan(tmp_path / "before", campaign_data)
    revised = dict(campaign_data)
    revised["platformVariants"] = {"discord": {"body": "Hello launch community"}}
    after_path = _write_plan(tmp_path / "after", revised)

    result = diff_campaign_plans(
        load_campaign_plan(before_path),
        load_campaign_plan(after_path),
    )

    assert result.items[0].campaign_diff is not None
    assert [change.field for change in result.items[0].campaign_diff.fields] == ["platformVariants"]
    assert [change.platform for change in result.items[0].campaign_diff.drafts] == ["discord"]


def test_plan_approval_verification_rechecks_recorded_quality_policy(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    bundle = build_campaign_plan(load_campaign_plan(_write_plan(tmp_path, campaign_data)))
    approval = CampaignPlanApproval(
        plan_id=bundle.plan_id,
        source_hash=bundle.source_hash,
        approved_by="Reviewer",
        approved_at=datetime(2026, 8, 3, tzinfo=timezone.utc),
        warnings_as_errors=True,
    )

    result = verify_campaign_plan_approval(bundle, approval)

    assert result.valid is False
    assert [issue.code for issue in result.issues] == ["quality-policy-failed"]


def test_plan_approval_enforces_selected_quality_policy(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    bundle = build_campaign_plan(load_campaign_plan(_write_plan(tmp_path, campaign_data)))

    with pytest.raises(ConfigError) as strict:
        create_campaign_plan_approval(
            bundle,
            approved_by="Strict reviewer",
            warnings_as_errors=True,
        )
    assert "selected quality policy" in str(strict.value)
    assert "item 1: Title is omitted from the x draft." in str(strict.value)

    failing = dict(campaign_data)
    failing["body"] = "long content " * 1_000
    failing_bundle = build_campaign_plan(
        load_campaign_plan(_write_plan(tmp_path / "failing", failing))
    )
    with pytest.raises(ConfigError, match="selected quality policy"):
        create_campaign_plan_approval(failing_bundle, approved_by="Reviewer")


def test_load_plan_approval_rejects_unknown_and_invalid_fields(tmp_path: Path) -> None:
    path = tmp_path / "invalid-plan-approval.json"
    _write_json(
        path,
        {
            "schemaVersion": False,
            "artifactType": "campaign",
            "planId": "bad",
            "sourceHash": "bad",
            "approvedBy": "line\nbreak",
            "approvedAt": "yesterday",
            "qualityPolicy": "anything",
            "note": "",
            "extra": True,
        },
    )

    with pytest.raises(ConfigError) as caught:
        load_campaign_plan_approval(path)

    message = str(caught.value)
    assert "unknown plan approval field" in message
    assert "schemaVersion must be 1" in message
    assert "artifactType must be plan" in message
    assert "planId must be" in message
    assert "sourceHash must be" in message
    assert "approvedBy must be a single line" in message
    assert "approvedAt must be" in message
    assert "qualityPolicy must be" in message
    assert "note must not be empty" in message


def test_plan_approval_schema_and_runtime_reject_divergent_optional_values() -> None:
    approval = CampaignPlanApproval(
        plan_id="scp_0123456789ab",
        source_hash="0" * 64,
        approved_by="Reviewer",
        approved_at=datetime(2026, 8, 3, tzinfo=timezone.utc),
    ).to_dict()
    validator = Draft202012Validator(
        load_plan_approval_schema(),
        format_checker=FormatChecker(),
    )

    whitespace_reviewer = {**approval, "approvedBy": " "}
    assert validator.is_valid(whitespace_reviewer) is False
    with pytest.raises(ConfigError, match="approvedBy must not be empty"):
        CampaignPlanApproval.from_dict(whitespace_reviewer)

    null_note = {**approval, "note": None}
    assert validator.is_valid(null_note) is False
    with pytest.raises(ConfigError, match="note must be a string"):
        CampaignPlanApproval.from_dict(null_note)


def test_plan_approval_rejects_naive_time_and_invalid_reviewer(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    bundle = build_campaign_plan(load_campaign_plan(_write_plan(tmp_path, campaign_data)))

    with pytest.raises(ConfigError) as caught:
        create_campaign_plan_approval(
            bundle,
            approved_by="\t",
            approved_at=datetime(2026, 8, 3, 14, 15),
        )

    assert "approved_by" in str(caught.value)
    assert "timezone" in str(caught.value)


def test_plan_approval_record_omits_absent_note() -> None:
    approval = CampaignPlanApproval(
        plan_id="scp_0123456789ab",
        source_hash="0" * 64,
        approved_by="Reviewer",
        approved_at=datetime(2026, 8, 3, tzinfo=timezone.utc),
    )

    assert "note" not in approval.to_dict()
