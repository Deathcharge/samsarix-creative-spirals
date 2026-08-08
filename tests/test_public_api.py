from __future__ import annotations

import re
from typing import Any

import samsarix_creative_spirals as package
from jsonschema import Draft202012Validator


def test_public_api_is_deliberate() -> None:
    assert package.__version__ == "0.15.0"
    assert package.__all__ == [
        "__version__",
        "ApprovalCheck",
        "ApprovalIssue",
        "ApprovalPolicy",
        "ApprovalRequirement",
        "CampaignApproval",
        "CampaignBundle",
        "CampaignCheck",
        "CampaignConfig",
        "CampaignDiff",
        "CampaignDraftChange",
        "CampaignFieldChange",
        "CampaignPlan",
        "CampaignPlanApproval",
        "CampaignPlanApprovalAssignment",
        "CampaignPlanApprovalSet",
        "CampaignPlanBundle",
        "CampaignPlanCheck",
        "CampaignPlanDiff",
        "CampaignPlanHandoff",
        "CampaignPlanHandoffPacket",
        "CampaignPlanItem",
        "CampaignPlanMedia",
        "CampaignPlanMediaAsset",
        "CampaignPlanMediaBinding",
        "CampaignPlanPublication",
        "CampaignPlanReadiness",
        "CampaignPlanReadinessItem",
        "ConfigError",
        "CollectedCampaignPlanMedia",
        "ContentPolicy",
        "ContentPolicyBinding",
        "ContentPolicyRule",
        "HandoffArtifact",
        "HandoffCheck",
        "HandoffIssue",
        "LinkTracking",
        "MediaReference",
        "PlanApprovalCheck",
        "PlanApprovalSetCheck",
        "PlanFieldChange",
        "PlanItemChange",
        "PlanItemSnapshot",
        "PlanIssue",
        "PlannedCampaign",
        "PlatformContentVariant",
        "PlatformDraft",
        "PublicationCheck",
        "PublicationIssue",
        "PublicationRecord",
        "QualityIssue",
        "ReadinessIssue",
        "build_campaign",
        "build_campaign_plan",
        "build_campaign_plan_handoff",
        "build_campaign_plan_readiness",
        "check_campaign",
        "check_campaign_plan",
        "collect_campaign_plan_media",
        "create_campaign_approval",
        "create_campaign_plan_approval",
        "create_campaign_plan_approval_set",
        "diff_campaigns",
        "diff_campaign_plans",
        "export_campaign",
        "export_campaign_approval",
        "export_campaign_plan",
        "export_campaign_plan_approval",
        "export_campaign_plan_approval_set",
        "export_campaign_plan_handoff",
        "export_campaign_plan_publication",
        "export_campaign_plan_readiness_html",
        "evaluate_content_policy",
        "initialize_campaign_plan_publication",
        "load_adapter_schema",
        "load_approval_policy",
        "load_approval_policy_schema",
        "load_approval_schema",
        "load_campaign",
        "load_campaign_approval",
        "load_campaign_plan",
        "load_campaign_plan_approval",
        "load_campaign_plan_approval_evidence",
        "load_campaign_plan_approval_set",
        "load_campaign_plan_handoff",
        "load_campaign_plan_media",
        "load_campaign_plan_publication",
        "load_campaign_schema",
        "load_content_policy",
        "load_content_policy_schema",
        "load_handoff_schema",
        "load_media_package_schema",
        "load_plan_approval_schema",
        "load_plan_approval_set_schema",
        "load_plan_schema",
        "load_publication_schema",
        "load_readiness_schema",
        "parse_approval_timestamp",
        "render_campaign_plan_readiness_html",
        "render_plan_adapter",
        "render_plan_calendar",
        "verify_campaign_approval",
        "verify_campaign_plan_approval",
        "verify_campaign_plan_approval_evidence",
        "verify_campaign_plan_approval_set",
        "verify_campaign_plan_handoff",
        "verify_campaign_plan_publication",
    ]


def test_packaged_schema_is_available() -> None:
    schema = package.load_campaign_schema()

    Draft202012Validator.check_schema(schema)
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["properties"]["schemaVersion"]["const"] == 1
    assert "bluesky" in schema["properties"]["platforms"]["items"]["enum"]
    assert schema["properties"]["platformLimits"]["properties"]["mastodon"]["maximum"] == 100000
    assert schema["properties"]["media"]["maxItems"] == 20
    assert schema["properties"]["platformVariants"]["maxProperties"] == 5
    assert schema["$defs"]["trackingParameterMap"]["maxProperties"] == 20
    assert (
        schema["properties"]["linkTracking"]["properties"]["platformParameters"]["maxProperties"]
        == 5
    )
    assert schema["$defs"]["contentVariant"]["required"] == ["body"]
    assert schema["$defs"]["mediaReference"]["properties"]["altText"]["maxLength"] == 1000
    requested_limit_conditions = {
        condition["if"]["properties"]["platformLimits"]["required"][0]: condition["then"][
            "properties"
        ]["platforms"]["contains"]["const"]
        for condition in schema["allOf"]
        if "if" in condition and "platformLimits" in condition["if"]["properties"]
    }
    assert requested_limit_conditions == {
        "x": "x",
        "linkedin": "linkedin",
        "bluesky": "bluesky",
        "mastodon": "mastodon",
        "discord": "discord",
    }
    requested_variant_conditions = {
        condition["if"]["properties"]["platformVariants"]["required"][0]: condition["then"][
            "properties"
        ]["platforms"]["contains"]["const"]
        for condition in schema["allOf"]
        if "if" in condition and "platformVariants" in condition["if"]["properties"]
    }
    assert requested_variant_conditions == requested_limit_conditions
    requested_tracking_conditions = {
        condition["if"]["properties"]["linkTracking"]["properties"]["platformParameters"][
            "required"
        ][0]: condition["then"]["properties"]["platforms"]["contains"]["const"]
        for condition in schema["allOf"]
        if "if" in condition and "linkTracking" in condition["if"]["properties"]
    }
    assert requested_tracking_conditions == requested_limit_conditions
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


def test_campaign_schema_validates_platform_variants() -> None:
    schema = package.load_campaign_schema()
    validator = Draft202012Validator(schema)
    campaign: dict[str, Any] = {
        "schemaVersion": 1,
        "name": "Variant campaign",
        "body": "Baseline copy",
        "platforms": ["x", "linkedin"],
        "platformVariants": {
            "x": {
                "body": "X-native copy",
                "link": "https://example.com/x",
                "hashtags": ["Samsarix"],
            }
        },
    }

    validator.validate(campaign)
    campaign["platformVariants"] = {"discord": {"body": "Unrequested copy"}}

    assert any("does not contain" in error.message for error in validator.iter_errors(campaign))


def test_campaign_schema_validates_link_tracking() -> None:
    validator = Draft202012Validator(package.load_campaign_schema())
    campaign: dict[str, Any] = {
        "schemaVersion": 1,
        "name": "Tracked campaign",
        "body": "Tracked copy",
        "link": "https://example.com/launch",
        "platforms": ["x", "linkedin"],
        "linkTracking": {
            "parameters": {"utm_campaign": "release", "utm_medium": "social"},
            "platformParameters": {"x": {"utm_source": "x"}},
        },
    }

    validator.validate(campaign)
    campaign["linkTracking"]["platformParameters"] = {"discord": {"utm_source": "discord"}}

    assert any("does not contain" in error.message for error in validator.iter_errors(campaign))


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


def test_packaged_approval_policy_schemas_are_available() -> None:
    policy = package.load_approval_policy_schema()
    approval_set = package.load_plan_approval_set_schema()

    Draft202012Validator.check_schema(policy)
    Draft202012Validator.check_schema(approval_set)
    assert policy["properties"]["requirements"]["maxItems"] == 20
    assert policy["properties"]["minimumTotal"]["maximum"] == 50
    assert approval_set["properties"]["artifactType"]["const"] == "plan-approval-set"
    assert approval_set["properties"]["approvals"]["maxItems"] == 50


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


def test_packaged_handoff_schema_is_available() -> None:
    schema = package.load_handoff_schema()

    Draft202012Validator.check_schema(schema)
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["properties"]["artifactType"]["const"] == "plan-handoff"
    assert schema["properties"]["handoffId"]["pattern"] == "^sch_[0-9a-f]{12}$"
    assert schema["properties"]["artifacts"]["minProperties"] == 5
    assert schema["properties"]["producer"]["properties"]["name"]["const"] == (
        "samsarix-creative-spirals"
    )


def test_packaged_readiness_schema_is_available() -> None:
    schema = package.load_readiness_schema()

    Draft202012Validator.check_schema(schema)
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["properties"]["artifactType"]["const"] == "plan-readiness"
    assert schema["properties"]["stage"]["enum"][-1] == "publication-complete"


def test_packaged_publication_schema_is_available() -> None:
    schema = package.load_publication_schema()

    Draft202012Validator.check_schema(schema)
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["properties"]["artifactType"]["const"] == "plan-publication"
    assert schema["properties"]["records"]["maxItems"] == 500
    assert schema["$defs"]["record"]["properties"]["status"]["enum"] == [
        "pending",
        "published",
        "failed",
        "skipped",
    ]
