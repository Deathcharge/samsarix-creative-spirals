from __future__ import annotations

import samsarix_creative_spirals as package


def test_public_api_is_deliberate() -> None:
    assert package.__version__ == "0.2.0"
    assert package.__all__ == [
        "CampaignBundle",
        "CampaignConfig",
        "ConfigError",
        "PlatformDraft",
        "build_campaign",
        "export_campaign",
        "load_campaign_schema",
        "load_campaign",
    ]


def test_packaged_schema_is_available() -> None:
    schema = package.load_campaign_schema()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["properties"]["schemaVersion"]["const"] == 1
