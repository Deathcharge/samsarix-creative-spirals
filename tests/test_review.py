from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from samsarix_creative_spirals import (
    CampaignApproval,
    ConfigError,
    build_campaign,
    create_campaign_approval,
    diff_campaigns,
    export_campaign_approval,
    load_campaign_approval,
    parse_approval_timestamp,
    verify_campaign_approval,
)


def test_semantic_diff_ignores_equivalent_source_spelling(campaign_data: dict[str, Any]) -> None:
    equivalent = dict(campaign_data)
    equivalent["name"] = f"  {campaign_data['name']}  "
    equivalent["platforms"] = ["X", "LinkedIn", "Discord"]

    result = diff_campaigns(campaign_data, equivalent)

    assert result.changed is False
    assert result.before_campaign_id == result.after_campaign_id
    assert result.fields == ()
    assert result.drafts == ()


def test_semantic_diff_reports_source_and_generated_changes(
    campaign_data: dict[str, Any],
) -> None:
    revised = dict(campaign_data)
    revised["body"] = "Revised release copy"
    revised["platforms"] = ["x", "bluesky", "discord"]

    result = diff_campaigns(campaign_data, revised)
    payload = result.to_dict()

    assert result.changed is True
    assert [change.field for change in result.fields] == ["body", "platforms"]
    assert [change.platform for change in result.drafts] == [
        "x",
        "linkedin",
        "bluesky",
        "discord",
    ]
    assert next(change for change in result.drafts if change.platform == "linkedin").change == (
        "removed"
    )
    assert next(change for change in result.drafts if change.platform == "bluesky").change == (
        "added"
    )
    assert payload["beforeSourceHash"] != payload["afterSourceHash"]
    assert payload["drafts"][0]["fields"]


def test_semantic_diff_reports_platform_targeted_media_changes(
    campaign_data: dict[str, Any],
) -> None:
    revised = dict(campaign_data)
    revised["media"] = [
        {
            "path": "media/launch.png",
            "altText": "Launch review dashboard",
            "platforms": ["linkedin"],
        }
    ]

    result = diff_campaigns(campaign_data, revised)

    assert [change.field for change in result.fields] == ["media"]
    assert [change.platform for change in result.drafts] == ["linkedin"]
    assert result.drafts[0].fields == ("media",)


def test_create_export_load_and_verify_approval(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    bundle = build_campaign(campaign_data)
    timestamp = datetime(2026, 8, 2, 12, 30, tzinfo=timezone.utc)
    approval = create_campaign_approval(
        bundle,
        approved_by="Release reviewer",
        approved_at=timestamp,
        note="Reviewed against launch brief.",
    )
    path = export_campaign_approval(approval, tmp_path / "campaign.approval.json")

    loaded = load_campaign_approval(path)
    result = verify_campaign_approval(bundle, loaded)

    assert loaded == approval
    assert loaded.to_dict()["approvedAt"] == "2026-08-02T12:30:00Z"
    assert loaded.to_dict()["qualityPolicy"] == "errors-only"
    assert result.valid is True
    assert result.to_dict()["issues"] == []

    with pytest.raises(ConfigError, match="refusing to overwrite"):
        export_campaign_approval(approval, path)


def test_approval_becomes_invalid_when_campaign_changes(campaign_data: dict[str, Any]) -> None:
    original = build_campaign(campaign_data)
    approval = create_campaign_approval(original, approved_by="Reviewer")
    campaign_data["body"] = "Changed after approval"
    revised = build_campaign(campaign_data)

    result = verify_campaign_approval(revised, approval)

    assert result.valid is False
    assert [issue.code for issue in result.issues] == ["source-changed", "campaign-id-changed"]


def test_approval_becomes_invalid_when_media_metadata_changes(
    campaign_data: dict[str, Any],
) -> None:
    original = build_campaign(campaign_data)
    approval = create_campaign_approval(original, approved_by="Reviewer")
    campaign_data["media"] = [{"path": "media/launch.png", "altText": "Launch review dashboard"}]

    result = verify_campaign_approval(build_campaign(campaign_data), approval)

    assert result.valid is False
    assert [issue.code for issue in result.issues] == ["source-changed", "campaign-id-changed"]


def test_approval_enforces_selected_quality_policy(campaign_data: dict[str, Any]) -> None:
    bundle = build_campaign(campaign_data)

    with pytest.raises(ConfigError, match="selected quality policy"):
        create_campaign_approval(
            bundle,
            approved_by="Strict reviewer",
            warnings_as_errors=True,
        )

    campaign_data["body"] = "long content " * 100
    with pytest.raises(ConfigError, match="selected quality policy"):
        create_campaign_approval(build_campaign(campaign_data), approved_by="Reviewer")


@pytest.mark.parametrize(
    ("value", "message"),
    [
        ("2026-08-02T08:30:00-04:00", None),
        ("2026-08-02T12:30:00.123456789Z", None),
        ("2026-08-02T12:30:00", "explicit offset"),
        ("2026-08-02T12:30:00-00:00", "known UTC offset"),
    ],
)
def test_parse_approval_timestamp(value: str, message: str | None) -> None:
    if message is not None:
        with pytest.raises(ConfigError, match=message):
            parse_approval_timestamp(value)
        return

    parsed = parse_approval_timestamp(value)
    assert parsed.utcoffset() == timezone.utc.utcoffset(parsed)


def test_load_approval_rejects_unknown_and_invalid_fields(tmp_path: Path) -> None:
    path = tmp_path / "invalid-approval.json"
    path.write_text(
        json.dumps(
            {
                "schemaVersion": 2,
                "artifactType": "plan",
                "campaignId": "bad",
                "sourceHash": "bad",
                "approvedBy": "line\nbreak",
                "approvedAt": "yesterday",
                "qualityPolicy": "anything",
                "note": "",
                "extra": True,
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ConfigError) as caught:
        load_campaign_approval(path)

    message = str(caught.value)
    assert "unknown approval field" in message
    assert "schemaVersion must be 1" in message
    assert "artifactType must be campaign" in message
    assert "campaignId must be" in message
    assert "sourceHash must be" in message
    assert "approvedBy must be a single line" in message
    assert "approvedAt must be" in message
    assert "qualityPolicy must be" in message
    assert "note must not be empty" in message


def test_campaign_approval_rejects_naive_time_and_invalid_reviewer(
    campaign_data: dict[str, Any],
) -> None:
    bundle = build_campaign(campaign_data)

    with pytest.raises(ConfigError) as caught:
        create_campaign_approval(
            bundle,
            approved_by="\t",
            approved_at=datetime(2026, 8, 2, 12, 30),
        )

    assert "approved_by" in str(caught.value)
    assert "timezone" in str(caught.value)


def test_approval_record_omits_absent_note(campaign_data: dict[str, Any]) -> None:
    approval = CampaignApproval(
        campaign_id="scs_0123456789ab",
        source_hash="0" * 64,
        approved_by="Reviewer",
        approved_at=datetime(2026, 8, 2, tzinfo=timezone.utc),
    )

    assert "note" not in approval.to_dict()
