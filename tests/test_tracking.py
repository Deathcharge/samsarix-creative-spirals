from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from samsarix_creative_spirals import (
    ConfigError,
    LinkTracking,
    build_campaign,
    build_campaign_plan,
    create_campaign_approval,
    create_campaign_plan_approval,
    diff_campaigns,
    export_campaign_plan_handoff,
    load_campaign_plan,
    load_campaign_plan_handoff,
    load_campaign_schema,
    render_plan_adapter,
    verify_campaign_approval,
    verify_campaign_plan_handoff,
)
from samsarix_creative_spirals.models import CampaignConfig


def _with_tracking(campaign_data: dict[str, Any]) -> dict[str, Any]:
    source = deepcopy(campaign_data)
    source["link"] = "https://example.com/release?lang=en#details"
    source["linkTracking"] = {
        "parameters": {
            "utm_campaign": "creative spirals 0.12",
            "utm_medium": "social",
            "utm_source": "samsarix",
        },
        "platformParameters": {
            "x": {"utm_content": "launch/x", "utm_source": "x"},
            "linkedin": {"utm_source": "linkedin"},
        },
    }
    return source


def test_tracking_parameters_are_normalized_encoded_and_platform_specific(
    campaign_data: dict[str, Any],
) -> None:
    source = _with_tracking(campaign_data)
    config = CampaignConfig.from_dict(source)
    bundle = build_campaign(config)
    drafts = {draft.platform: draft.content for draft in bundle.drafts}

    assert config.link_tracking == LinkTracking(
        parameters=(
            ("utm_campaign", "creative spirals 0.12"),
            ("utm_medium", "social"),
            ("utm_source", "samsarix"),
        ),
        platform_parameters=(
            ("x", (("utm_content", "launch/x"), ("utm_source", "x"))),
            ("linkedin", (("utm_source", "linkedin"),)),
        ),
    )
    assert (
        "https://example.com/release?lang=en&utm_campaign=creative%20spirals%200.12"
        "&utm_content=launch%2Fx&utm_medium=social&utm_source=x#details"
    ) in drafts["x"]
    assert "utm_source=linkedin#details" in drafts["linkedin"]
    assert "utm_source=samsarix#details" in drafts["discord"]
    Draft202012Validator(load_campaign_schema()).validate(config.to_dict())


def test_tracking_applies_to_complete_variant_links(campaign_data: dict[str, Any]) -> None:
    source = _with_tracking(campaign_data)
    source["platformVariants"] = {
        "x": {
            "body": "A tracked platform-specific call to action.",
            "link": "https://example.com/x-release#install",
        }
    }

    bundle = build_campaign(source)
    x_content = next(draft.content for draft in bundle.drafts if draft.platform == "x")

    assert "https://example.com/x-release?" in x_content
    assert "utm_source=x#install" in x_content
    assert "lang=en" not in x_content


def test_tracking_is_canonical_and_part_of_identity(campaign_data: dict[str, Any]) -> None:
    source = _with_tracking(campaign_data)
    equivalent = deepcopy(source)
    equivalent["linkTracking"]["parameters"] = {
        "utm_source": "samsarix",
        "utm_campaign": "  creative spirals 0.12  ",
        "utm_medium": "social",
    }

    before = build_campaign(source)
    after = build_campaign(equivalent)

    assert before.source_hash == after.source_hash
    assert before.drafts == after.drafts


def test_tracking_change_is_visible_and_invalidates_approval(
    campaign_data: dict[str, Any],
) -> None:
    source = _with_tracking(campaign_data)
    approval = create_campaign_approval(build_campaign(source), approved_by="Reviewer")
    revised = deepcopy(source)
    revised["linkTracking"]["parameters"]["utm_campaign"] = "creative-spirals-012b"

    difference = diff_campaigns(source, revised)
    approval_check = verify_campaign_approval(build_campaign(revised), approval)

    assert [change.field for change in difference.fields] == ["linkTracking"]
    assert [change.platform for change in difference.drafts] == ["x", "linkedin", "discord"]
    assert all("content" in change.fields for change in difference.drafts)
    assert [issue.code for issue in approval_check.issues] == [
        "source-changed",
        "campaign-id-changed",
    ]


@pytest.mark.parametrize(
    ("tracking", "message"),
    [
        ("utm_source=samsarix", "linkTracking must be an object"),
        ({}, "must define at least one parameter"),
        ({"parameters": []}, "must be an object mapping"),
        ({"parameters": {}}, "must contain at least one parameter"),
        ({"parameters": {"UTM_Source": "x"}}, "parameter names must match"),
        ({"parameters": {"utm_source": 42}}, "utm_source must be a string"),
        ({"parameters": {"utm_source": "   "}}, "utm_source must not be empty"),
        ({"parameters": {"utm_source": "bad\nvalue"}}, "single line"),
        ({"parameters": {"utm_source": "x" * 201}}, "at most 200"),
        ({"parameters": {"utm_source": "x"}, "unknown": True}, "unknown field"),
        (
            {"platformParameters": []},
            "platformParameters must map platforms to parameter objects",
        ),
        (
            {"platformParameters": {}},
            "platformParameters must contain at least one platform",
        ),
        (
            {"platformParameters": {"X": {"utm_source": "x"}}},
            "keys must be canonical platforms",
        ),
        (
            {"platformParameters": {"mastodon": {"utm_source": "mastodon"}}},
            "not useful unless mastodon is requested",
        ),
    ],
)
def test_campaign_rejects_malformed_tracking(
    campaign_data: dict[str, Any], tracking: object, message: str
) -> None:
    campaign_data["linkTracking"] = tracking

    with pytest.raises(ConfigError, match=message):
        CampaignConfig.from_dict(campaign_data)


def test_campaign_rejects_tracking_without_an_effective_link(
    campaign_data: dict[str, Any],
) -> None:
    campaign_data.pop("link")
    campaign_data["linkTracking"] = {"parameters": {"utm_source": "samsarix"}}

    with pytest.raises(ConfigError, match="requires at least one effective campaign link"):
        CampaignConfig.from_dict(campaign_data)


def test_campaign_rejects_existing_parameter_conflicts(
    campaign_data: dict[str, Any],
) -> None:
    campaign_data["link"] = "https://example.com/release?utm_source=manual"
    campaign_data["linkTracking"] = {
        "parameters": {"utm_source": "samsarix", "utm_medium": "social"}
    }

    with pytest.raises(ConfigError, match="duplicate existing query parameter.*utm_source"):
        CampaignConfig.from_dict(campaign_data)


def test_campaign_rejects_more_than_twenty_merged_parameters(
    campaign_data: dict[str, Any],
) -> None:
    campaign_data["linkTracking"] = {
        "parameters": {f"param_{index}": str(index) for index in range(20)},
        "platformParameters": {"x": {"extra": "value"}},
    }

    with pytest.raises(ConfigError, match="more than 20 parameters for x"):
        CampaignConfig.from_dict(campaign_data)


def test_campaign_rejects_oversized_rendered_tracking_link(
    campaign_data: dict[str, Any],
) -> None:
    campaign_data["link"] = "https://example.com/" + "a" * 450
    campaign_data["linkTracking"] = {
        "parameters": {f"parameter_{index}": "v" * 100 for index in range(20)}
    }

    with pytest.raises(ConfigError, match="tracked link must be at most 2000 characters"):
        CampaignConfig.from_dict(campaign_data)


def test_link_tracking_rejects_unknown_platform_and_direct_conflict() -> None:
    tracking = LinkTracking(parameters=(("utm_source", "samsarix"),))

    with pytest.raises(ConfigError, match="unsupported platform"):
        tracking.parameters_for("instagram")
    with pytest.raises(ConfigError, match="duplicate existing query parameter"):
        tracking.apply_to("https://example.com/?utm_source=manual", "x")


def test_link_tracking_encodes_unicode_and_detects_encoded_name_conflicts() -> None:
    tracking = LinkTracking(parameters=(("audience", "Café launch"),))

    assert tracking.apply_to("https://example.com/release", "x") == (
        "https://example.com/release?audience=Caf%C3%A9%20launch"
    )

    conflicting = LinkTracking(parameters=(("utm_source", "samsarix"),))
    with pytest.raises(ConfigError, match="duplicate existing query parameter"):
        conflicting.apply_to("https://example.com/?%75tm_source=manual", "x")


def test_tracking_propagates_through_plan_adapter_approval_and_handoff(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    campaign_path = tmp_path / "campaign.json"
    campaign_path.write_text(json.dumps(_with_tracking(campaign_data)), encoding="utf-8")
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "name": "Attributed release plan",
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
    adapter = render_plan_adapter(bundle)
    approval = create_campaign_plan_approval(
        bundle,
        approved_by="Reviewer",
        approved_at=datetime(2026, 8, 13, tzinfo=timezone.utc),
    )

    packet_path = export_campaign_plan_handoff(
        bundle,
        approval,
        tmp_path / "handoffs",
        generated_at=datetime(2026, 8, 14, tzinfo=timezone.utc),
    )
    packet = load_campaign_plan_handoff(packet_path)

    assert "utm_campaign=creative%20spirals%200.12" in adapter
    assert "utm_source=x#details" in adapter
    assert verify_campaign_plan_handoff(bundle, packet).valid
