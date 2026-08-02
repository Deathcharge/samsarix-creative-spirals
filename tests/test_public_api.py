from __future__ import annotations

import re

import samsarix_creative_spirals as package


def test_public_api_is_deliberate() -> None:
    assert package.__version__ == "0.7.0"
    assert package.__all__ == [
        "ApprovalCheck",
        "ApprovalIssue",
        "CampaignApproval",
        "CampaignBundle",
        "CampaignCheck",
        "CampaignConfig",
        "CampaignDiff",
        "CampaignDraftChange",
        "CampaignFieldChange",
        "CampaignPlan",
        "CampaignPlanApproval",
        "CampaignPlanBundle",
        "CampaignPlanCheck",
        "CampaignPlanDiff",
        "CampaignPlanItem",
        "ConfigError",
        "MediaReference",
        "PlanApprovalCheck",
        "PlanFieldChange",
        "PlanItemChange",
        "PlanItemSnapshot",
        "PlanIssue",
        "PlannedCampaign",
        "PlatformDraft",
        "QualityIssue",
        "build_campaign",
        "build_campaign_plan",
        "check_campaign",
        "check_campaign_plan",
        "create_campaign_approval",
        "create_campaign_plan_approval",
        "diff_campaigns",
        "diff_campaign_plans",
        "export_campaign",
        "export_campaign_approval",
        "export_campaign_plan",
        "export_campaign_plan_approval",
        "load_adapter_schema",
        "load_approval_schema",
        "load_campaign",
        "load_campaign_approval",
        "load_campaign_plan",
        "load_campaign_plan_approval",
        "load_campaign_schema",
        "load_plan_schema",
        "load_plan_approval_schema",
        "parse_approval_timestamp",
        "render_plan_adapter",
        "render_plan_calendar",
        "verify_campaign_approval",
        "verify_campaign_plan_approval",
    ]


def test_packaged_schema_is_available() -> None:
    schema = package.load_campaign_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["properties"]["schemaVersion"]["const"] == 1
    assert "bluesky" in schema["properties"]["platforms"]["items"]["enum"]
    assert schema["properties"]["platformLimits"]["properties"]["mastodon"]["maximum"] == 100000
    assert schema["properties"]["media"]["maxItems"] == 20
    assert schema["$defs"]["mediaReference"]["properties"]["altText"]["maxLength"] == 1000
    requested_limit_conditions = {
        condition["if"]["properties"]["platformLimits"]["required"][0]: condition["then"][
            "properties"
        ]["platforms"]["contains"]["const"]
        for condition in schema["allOf"]
        if "if" in condition
    }
    assert requested_limit_conditions == {
        "x": "x",
        "linkedin": "linkedin",
        "bluesky": "bluesky",
        "mastodon": "mastodon",
        "discord": "discord",
    }
    media_pattern = schema["$defs"]["mediaReference"]["properties"]["path"]["pattern"]
    assert re.fullmatch(media_pattern, "media/launch-dashboard.PNG")
    for invalid in (
        " media/launch.png",
        "media/launch.png ",
        "media/ launch.png",
        "media//launch.png",
        "media/../launch.png",
        "media/CON.data.png",
        "media/Lpt9/launch.png",
    ):
        assert not re.fullmatch(media_pattern, invalid)
    media_conditions = [condition for condition in schema["allOf"] if "if" not in condition]
    assert len(media_conditions) == 5
    assert all(
        condition["properties"]["media"]["maxContains"] == 4 for condition in media_conditions
    )


def test_packaged_plan_schema_is_available() -> None:
    schema = package.load_plan_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["properties"]["items"]["maxItems"] == 100
    assert schema["properties"]["items"]["items"]["properties"]["intendedAt"]["format"] == (
        "date-time"
    )
    intended_pattern = schema["properties"]["items"]["items"]["properties"]["intendedAt"]["pattern"]
    assert re.fullmatch(intended_pattern, "2026-08-02T12:30:00Z")
    assert not re.fullmatch(intended_pattern, "2026-08-02T12:30:00-00:00")
    campaign_pattern = schema["properties"]["items"]["items"]["properties"]["campaign"]["pattern"]
    assert re.fullmatch(campaign_pattern, "campaigns/release.json")
    assert not re.fullmatch(campaign_pattern, "campaigns/release.JSON")


def test_packaged_approval_schema_is_available() -> None:
    schema = package.load_approval_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["properties"]["artifactType"]["const"] == "campaign"
    assert schema["properties"]["qualityPolicy"]["enum"] == [
        "errors-only",
        "warnings-as-errors",
    ]


def test_packaged_plan_approval_schema_is_available() -> None:
    schema = package.load_plan_approval_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["properties"]["artifactType"]["const"] == "plan"
    assert schema["properties"]["planId"]["pattern"] == "^scp_[0-9a-f]{12}$"
    assert schema["properties"]["qualityPolicy"]["enum"] == [
        "errors-only",
        "warnings-as-errors",
    ]


def test_packaged_adapter_schema_is_available() -> None:
    schema = package.load_adapter_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["properties"]["contract"]["const"] == "samsarix.plan-drafts"
    assert schema["properties"]["schemaVersion"]["const"] == 2
    assert schema["properties"]["items"]["maxItems"] == 100
    assert schema["$defs"]["draft"]["properties"]["media"]["maxItems"] == 4
    assert schema["$defs"]["mediaPath"]["pattern"] == (
        package.load_campaign_schema()["$defs"]["mediaReference"]["properties"]["path"]["pattern"]
    )
