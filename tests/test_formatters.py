from __future__ import annotations

from typing import Any

import pytest

from samsarix_creative_spirals import CampaignConfig, ConfigError
from samsarix_creative_spirals.formatters import format_platform, x_weighted_length


def test_x_weighted_length_handles_unicode_and_urls() -> None:
    assert x_weighted_length("abc") == 3
    assert x_weighted_length("👋") == 2
    assert x_weighted_length("https://example.com/a/very/long/path") == 23
    assert x_weighted_length("https://example.com.") == 24
    assert x_weighted_length("\u2000\u2010\u2032") == 3
    assert x_weighted_length("界") == 2


def test_long_x_body_is_truncated_without_losing_suffix(campaign_data: dict[str, Any]) -> None:
    campaign_data["body"] = "A useful sentence with emoji 👋 and context. " * 30
    config = CampaignConfig.from_dict(campaign_data)

    draft = format_platform(config, "x")

    assert draft.truncated is True
    assert draft.character_count <= draft.character_limit == 280
    assert "https://example.com/release" in draft.content
    assert draft.content.endswith("#shipping #localfirst")
    assert "Body was truncated" in " ".join(draft.warnings)


def test_x_omits_title_and_excess_hashtags(campaign_data: dict[str, Any]) -> None:
    campaign_data["body"] = "Short body"
    campaign_data["hashtags"] = [f"tag{index}{'x' * 40}" for index in range(10)]
    config = CampaignConfig.from_dict(campaign_data)

    draft = format_platform(config, "x")

    assert campaign_data["title"] not in draft.content
    assert any("Omitted" in warning for warning in draft.warnings)
    assert any("Title is omitted" in warning for warning in draft.warnings)


def test_discord_flags_broadcast_mentions(campaign_data: dict[str, Any]) -> None:
    campaign_data["body"] = "Hello @everyone"
    config = CampaignConfig.from_dict(campaign_data)

    draft = format_platform(config, "discord")

    assert any("broadcast mention" in warning for warning in draft.warnings)


def test_discord_uses_conservative_utf16_count(campaign_data: dict[str, Any]) -> None:
    campaign_data.pop("title")
    campaign_data.pop("link")
    campaign_data["hashtags"] = []
    campaign_data["body"] = "👋"
    config = CampaignConfig.from_dict(campaign_data)

    draft = format_platform(config, "discord")

    assert draft.character_count == 2


def test_all_platform_outputs_respect_limits(campaign_data: dict[str, Any]) -> None:
    campaign_data["body"] = "content " * 10_000
    config = CampaignConfig.from_dict(campaign_data)

    for platform in config.platforms:
        draft = format_platform(config, platform)
        assert draft.character_count <= draft.character_limit


def test_formatter_rejects_unknown_platform(campaign_data: dict[str, Any]) -> None:
    config = CampaignConfig.from_dict(campaign_data)

    with pytest.raises(ConfigError, match="unsupported platform"):
        format_platform(config, "unknown")


def test_truncation_keeps_joined_emoji_together(campaign_data: dict[str, Any]) -> None:
    campaign_data["body"] = "👨‍👩‍👧‍👦" * 200
    config = CampaignConfig.from_dict(campaign_data)

    draft = format_platform(config, "x")

    assert not draft.content.split("…", 1)[0].endswith("\u200d")
