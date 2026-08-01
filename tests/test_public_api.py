from __future__ import annotations

import samsarix_creative_spirals as package


def test_public_api_is_deliberate() -> None:
    assert package.__version__ == "0.3.0"
    assert package.__all__ == [
        "CampaignBundle",
        "CampaignCheck",
        "CampaignConfig",
        "ConfigError",
        "PlatformDraft",
        "QualityIssue",
        "build_campaign",
        "check_campaign",
        "export_campaign",
        "load_campaign_schema",
        "load_campaign",
    ]


def test_packaged_schema_is_available() -> None:
    schema = package.load_campaign_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["properties"]["schemaVersion"]["const"] == 1
    assert "bluesky" in schema["properties"]["platforms"]["items"]["enum"]
    assert schema["properties"]["platformLimits"]["properties"]["mastodon"]["maximum"] == 100000
    requested_limit_conditions = {
        condition["if"]["properties"]["platformLimits"]["required"][0]: condition["then"][
            "properties"
        ]["platforms"]["contains"]["const"]
        for condition in schema["allOf"]
    }
    assert requested_limit_conditions == {
        "x": "x",
        "linkedin": "linkedin",
        "bluesky": "bluesky",
        "mastodon": "mastodon",
        "discord": "discord",
    }
