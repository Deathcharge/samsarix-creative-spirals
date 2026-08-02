from __future__ import annotations

from typing import Any

import pytest

from samsarix_creative_spirals import (
    CampaignConfig,
    ConfigError,
    MediaReference,
    PlatformContentVariant,
)


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


def test_platform_limits_are_normalized_and_serialized(campaign_data: dict[str, Any]) -> None:
    campaign_data["platforms"] = ["mastodon", "x"]
    campaign_data["platformLimits"] = {"mastodon": 5_000, "x": 200}

    config = CampaignConfig.from_dict(campaign_data)

    assert config.platform_limits == (("x", 200), ("mastodon", 5_000))
    assert config.limit_for("x") == 200
    assert config.limit_for("mastodon") == 5_000
    assert config.limit_for("discord") == 2_000
    assert config.to_dict()["platformLimits"] == {"x": 200, "mastodon": 5_000}


@pytest.mark.parametrize(
    ("value", "message"),
    [
        ([], "must be an object"),
        ({"unknown": 10}, "must name one of"),
        ({"x": True}, "must be an integer"),
        ({"x": 281}, "between 1 and 280"),
        ({"x": 0}, "between 1 and 280"),
        ({"mastodon": 100_001}, "between 1 and 100000"),
        ({"mastodon": 1_000}, "not useful unless mastodon is requested"),
        ({"X": 200, "x": 180}, "duplicates x"),
    ],
)
def test_campaign_rejects_invalid_platform_limits(
    campaign_data: dict[str, Any], value: object, message: str
) -> None:
    campaign_data["platformLimits"] = value

    with pytest.raises(ConfigError, match=message):
        CampaignConfig.from_dict(campaign_data)


def test_campaign_rejects_non_string_platform_limit_key(campaign_data: dict[str, Any]) -> None:
    campaign_data["platformLimits"] = {42: 10}

    with pytest.raises(ConfigError, match="keys must be platform strings"):
        CampaignConfig.from_dict(campaign_data)


def test_platform_variants_are_complete_normalized_content_blocks(
    campaign_data: dict[str, Any],
) -> None:
    campaign_data["platformVariants"] = {
        "discord": {
            "title": "  Community launch  ",
            "body": "  Hello @here\r\nSee what changed.  ",
        },
        "x": {
            "body": "  Ship cafe\u0301 workflows  ",
            "link": "https://example.com/x",
            "hashtags": ["#Samsarix", "local_first"],
        },
    }

    config = CampaignConfig.from_dict(campaign_data)

    assert config.platform_variants == (
        PlatformContentVariant(
            platform="x",
            body="Ship café workflows",
            link="https://example.com/x",
            hashtags=("Samsarix", "local_first"),
        ),
        PlatformContentVariant(
            platform="discord",
            title="Community launch",
            body="Hello @here\nSee what changed.",
        ),
    )
    assert config.variant_for("linkedin") is None
    assert config.variant_for("x") == config.platform_variants[0]
    assert config.to_dict()["platformVariants"] == {
        "x": {
            "body": "Ship café workflows",
            "hashtags": ["Samsarix", "local_first"],
            "link": "https://example.com/x",
        },
        "discord": {
            "body": "Hello @here\nSee what changed.",
            "hashtags": [],
            "title": "Community launch",
        },
    }


@pytest.mark.parametrize(
    ("variants", "message"),
    [
        ([], "platformVariants must be an object"),
        ({42: {"body": "Copy"}}, "keys must be platform strings"),
        ({"X": {"body": "Copy"}}, "canonical platform name"),
        (
            {
                "x": {"body": "Copy"},
                "linkedin": {"body": "Copy"},
                "bluesky": {"body": "Copy"},
                "mastodon": {"body": "Copy"},
                "discord": {"body": "Copy"},
                "extra": {"body": "Copy"},
            },
            "platformVariants must contain at most 5 entries",
        ),
        ({"mastodon": {"body": "Copy"}}, "not useful unless mastodon is requested"),
        ({"x": "Copy"}, "platformVariants.x must be an object"),
        ({"x": {}}, "platformVariants.x.body must be a string"),
        ({"x": {"body": ""}}, "platformVariants.x.body must not be empty"),
        ({"x": {"body": "x" * 100_001}}, "body must be at most 100000"),
        ({"x": {"body": "Copy\x00"}}, "body contains unsupported control"),
        ({"x": {"body": "Copy", "title": 42}}, "title must be a string"),
        ({"x": {"body": "Copy", "title": ""}}, "title must not be empty"),
        ({"x": {"body": "Copy", "title": "x" * 201}}, "title must be at most 200"),
        ({"x": {"body": "Copy", "title": "two\nlines"}}, "title must be a single line"),
        ({"x": {"body": "Copy", "link": 42}}, "link must be a string"),
        ({"x": {"body": "Copy", "link": "file:///secret"}}, "absolute http or https"),
        ({"x": {"body": "Copy", "link": "https://[invalid"}}, "absolute http or https"),
        (
            {"x": {"body": "Copy", "link": "https://example.com/" + "x" * 500}},
            "link must be at most 500",
        ),
        (
            {"x": {"body": "Copy", "link": "https://user:secret@example.com"}},
            "embedded credentials",
        ),
        ({"x": {"body": "Copy", "link": "https://example.com/a b"}}, "whitespace"),
        ({"x": {"body": "Copy", "hashtags": "tag"}}, "hashtags must be an array"),
        (
            {"x": {"body": "Copy", "hashtags": [f"tag{i}" for i in range(11)]}},
            "hashtags must contain at most 10",
        ),
        ({"x": {"body": "Copy", "hashtags": [42]}}, "hashtags\\[0\\] must be a string"),
        ({"x": {"body": "Copy", "hashtags": ["#"]}}, "hashtags\\[0\\] must not be empty"),
        (
            {"x": {"body": "Copy", "hashtags": ["x" * 51]}},
            "hashtags\\[0\\] must be at most 50",
        ),
        ({"x": {"body": "Copy", "hashtags": ["bad tag"]}}, "letters, numbers"),
        (
            {"x": {"body": "Copy", "hashtags": ["Tag", "tag"]}},
            "duplicates an earlier hashtag",
        ),
        ({"x": {"body": "Copy", "caption": "nope"}}, "unknown field.*caption"),
    ],
)
def test_campaign_rejects_invalid_platform_variants(
    campaign_data: dict[str, Any], variants: object, message: str
) -> None:
    campaign_data["platformVariants"] = variants

    with pytest.raises(ConfigError, match=message):
        CampaignConfig.from_dict(campaign_data)


def test_media_references_are_normalized_without_reading_files(
    campaign_data: dict[str, Any],
) -> None:
    campaign_data["media"] = [
        {
            "path": "media/hero.PNG",
            "altText": "  Cafe\u0301 launch dashboard  ",
        },
        {
            "path": "media/linkedin.jpg",
            "altText": "Product workflow diagram",
            "platforms": ["DISCORD", "x"],
        },
    ]

    config = CampaignConfig.from_dict(campaign_data)

    assert config.media == (
        MediaReference(
            "media/hero.PNG",
            "Café launch dashboard",
            ("x", "linkedin", "discord"),
        ),
        MediaReference(
            "media/linkedin.jpg",
            "Product workflow diagram",
            ("x", "discord"),
        ),
    )
    assert config.to_dict()["media"] == [reference.to_dict() for reference in config.media]


@pytest.mark.parametrize(
    ("media", "message"),
    [
        ("media/hero.png", "media must be an array"),
        (["media/hero.png"], r"media\[0\] must be an object"),
        ([{"path": 42, "altText": "Description"}], "path must be a string"),
        ([{"path": "../hero.png", "altText": "Description"}], "portable relative path"),
        ([{"path": "/hero.png", "altText": "Description"}], "portable relative path"),
        ([{"path": "media\\hero.png", "altText": "Description"}], "portable relative path"),
        ([{"path": " media/hero.png ", "altText": "Description"}], "portable relative path"),
        ([{"path": "media/CON.png", "altText": "Description"}], "portable relative path"),
        ([{"path": "media/CON.data.png", "altText": "Description"}], "portable relative path"),
        ([{"path": "media/.png", "altText": "Description"}], "portable relative path"),
        ([{"path": "media/hero.webp", "altText": "Description"}], "must end in"),
        ([{"path": "media/hero.png", "altText": 42}], "altText must be a string"),
        ([{"path": "media/hero.png", "altText": ""}], "altText must not be empty"),
        ([{"path": "media/hero.png", "altText": "line\nbreak"}], "single line"),
        ([{"path": "media/hero.png", "altText": "x" * 1_001}], "at most 1000"),
        (
            [{"path": "media/hero.png", "altText": "Description", "platforms": []}],
            "at least one platform",
        ),
        (
            [{"path": "media/hero.png", "altText": "Description", "platforms": "x"}],
            "non-empty array",
        ),
        (
            [{"path": "media/hero.png", "altText": "Description", "platforms": ["mastodon"]}],
            "not requested by the campaign",
        ),
        (
            [{"path": "media/hero.png", "altText": "Description", "platforms": ["x", "x"]}],
            "duplicates x",
        ),
        (
            [{"path": "media/hero.png", "altText": "Description", "credit": "Samsarix"}],
            "unknown field.*credit",
        ),
    ],
)
def test_campaign_rejects_invalid_media(
    campaign_data: dict[str, Any], media: object, message: str
) -> None:
    campaign_data["media"] = media

    with pytest.raises(ConfigError, match=message):
        CampaignConfig.from_dict(campaign_data)


def test_campaign_rejects_duplicate_and_excess_media(campaign_data: dict[str, Any]) -> None:
    campaign_data["media"] = [
        {"path": "media/HERO.png", "altText": "First"},
        {"path": "media/hero.PNG", "altText": "Second"},
    ]
    with pytest.raises(ConfigError, match="duplicates an earlier media path"):
        CampaignConfig.from_dict(campaign_data)

    campaign_data["media"] = [
        {"path": f"media/image-{index}.png", "altText": f"Image {index}", "platforms": ["x"]}
        for index in range(5)
    ]
    with pytest.raises(ConfigError, match="more than 4 images for x"):
        CampaignConfig.from_dict(campaign_data)

    campaign_data["media"] = [
        {"path": f"media/image-{index}.png", "altText": f"Image {index}"} for index in range(21)
    ]
    with pytest.raises(ConfigError, match="at most 20 references"):
        CampaignConfig.from_dict(campaign_data)


def test_campaign_accepts_four_platform_specific_images_per_platform(
    campaign_data: dict[str, Any],
) -> None:
    campaign_data["platforms"] = ["x", "linkedin", "bluesky", "mastodon", "discord"]
    campaign_data["media"] = [
        {
            "path": f"media/{platform}-{index}.jpg",
            "altText": f"{platform} visual {index}",
            "platforms": [platform],
        }
        for platform in campaign_data["platforms"]
        for index in range(4)
    ]

    config = CampaignConfig.from_dict(campaign_data)

    assert len(config.media) == 20


def test_equivalent_media_target_spelling_has_one_canonical_identity(
    campaign_data: dict[str, Any],
) -> None:
    campaign_data["media"] = [{"path": "media/launch.png", "altText": "Launch dashboard"}]
    implicit = CampaignConfig.from_dict(campaign_data)
    campaign_data["media"][0]["platforms"] = ["Discord", "LINKEDIN", "x"]
    explicit = CampaignConfig.from_dict(campaign_data)

    assert implicit == explicit
    assert implicit.to_dict() == explicit.to_dict()
