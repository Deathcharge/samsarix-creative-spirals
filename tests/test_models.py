from __future__ import annotations

from typing import Any

import pytest

from samsarix_creative_spirals import CampaignConfig, ConfigError


def test_campaign_normalizes_input(campaign_data: dict[str, Any]) -> None:
    campaign_data["body"] = "  cafe\u0301\r\nlaunch  "
    campaign_data["hashtags"] = ["#Launch"]

    config = CampaignConfig.from_dict(campaign_data)

    assert config.body == "café\nlaunch"
    assert config.hashtags == ("Launch",)
    assert config.to_dict()["schemaVersion"] == 1


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("schemaVersion", 2, "schemaVersion must be 1"),
        ("name", 42, "name must be a string"),
        ("name", "", "name must not be empty"),
        ("name", "x" * 121, "at most 120"),
        ("name", "line one\nline two", "single line"),
        ("name", "tab\tname", "single line"),
        ("body", 42, "body must be a string"),
        ("body", "\x00", "unsupported control"),
        ("body", "text\x7f", "unsupported control"),
        ("body", "text\ud800", "unsupported control"),
        ("body", "x" * 100_001, "at most 100000"),
        ("title", 42, "title must be a string"),
        ("title", "", "title must not be empty"),
        ("title", "x" * 201, "at most 200"),
        ("title", "line one\nline two", "single line"),
        ("platforms", [], "at least one"),
        ("platforms", "x", "non-empty array"),
        ("platforms", [42], "must be a string"),
        ("platforms", ["x", "x"], "duplicates x"),
        ("hashtags", "tag", "array of strings"),
        ("hashtags", [f"tag{i}" for i in range(11)], "at most 10"),
        ("hashtags", [42], "must be a string"),
        ("hashtags", ["#"], "must not be empty"),
        ("hashtags", ["x" * 51], "at most 50"),
        ("hashtags", ["bad tag"], "letters, numbers, and underscores"),
        ("hashtags", ["Tag", "tag"], "duplicates an earlier"),
        ("link", 42, "link must be a string"),
        ("link", "file:///secret", "absolute http or https"),
        ("link", "https://[invalid", "absolute http or https"),
        ("link", "https://user:secret@example.com", "embedded credentials"),
        ("link", "https://example.com/a b", "whitespace"),
        ("link", "https://example.com/" + "x" * 500, "at most 500"),
    ],
    ids=lambda value: (
        f"long-string-{len(value)}" if isinstance(value, str) and len(value) > 40 else None
    ),
)
def test_campaign_rejects_invalid_values(
    campaign_data: dict[str, Any], field: str, value: object, message: str
) -> None:
    campaign_data[field] = value

    with pytest.raises(ConfigError, match=message):
        CampaignConfig.from_dict(campaign_data)


def test_campaign_rejects_unknown_fields(campaign_data: dict[str, Any]) -> None:
    campaign_data["publsih"] = True

    with pytest.raises(ConfigError, match="unknown field.*publsih"):
        CampaignConfig.from_dict(campaign_data)


def test_campaign_rejects_non_object() -> None:
    with pytest.raises(ConfigError, match="JSON object"):
        CampaignConfig.from_dict([])  # type: ignore[arg-type]


def test_campaign_rejects_non_string_mapping_key(campaign_data: dict[str, Any]) -> None:
    campaign_data[42] = "unexpected"  # type: ignore[index]

    with pytest.raises(ConfigError, match=r"unknown field\(s\): 42"):
        CampaignConfig.from_dict(campaign_data)


def test_optional_fields_are_omitted(campaign_data: dict[str, Any]) -> None:
    campaign_data.pop("title")
    campaign_data.pop("link")

    serialized = CampaignConfig.from_dict(campaign_data).to_dict()

    assert "title" not in serialized
    assert "link" not in serialized


def test_config_error_accepts_single_issue() -> None:
    error = ConfigError("one problem")

    assert error.issues == ("one problem",)
