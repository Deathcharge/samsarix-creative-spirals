from __future__ import annotations

import helix_creative_spirals as package


def test_public_api_is_deliberate() -> None:
    assert package.__version__ == "0.1.0"
    assert package.__all__ == [
        "CampaignBundle",
        "CampaignConfig",
        "ConfigError",
        "PlatformDraft",
        "build_campaign",
        "export_campaign",
        "load_campaign",
    ]
