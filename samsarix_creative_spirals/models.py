# Copyright (c) 2026 Samsarix LLC
# SPDX-License-Identifier: MPL-2.0

"""Validated data models for local Samsarix campaign packaging."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

SUPPORTED_PLATFORMS = ("x", "linkedin", "bluesky", "mastodon", "discord")
PLATFORM_LIMITS = {
    "x": 280,
    "linkedin": 3000,
    "bluesky": 300,
    "mastodon": 500,
    "discord": 2000,
}
MAX_MEDIA_PER_PLATFORM = 4
MAX_MEDIA_REFERENCES = len(SUPPORTED_PLATFORMS) * MAX_MEDIA_PER_PLATFORM
MAX_MEDIA_PATH_LENGTH = 240
MAX_ALT_TEXT_LENGTH = 1_000
SUPPORTED_MEDIA_SUFFIXES = (".jpg", ".jpeg", ".png")

_CAMPAIGN_KEYS = {
    "schemaVersion",
    "name",
    "title",
    "body",
    "link",
    "hashtags",
    "platforms",
    "platformVariants",
    "platformLimits",
    "media",
}
_HASHTAG_RE = re.compile(r"^[\w]+$", re.UNICODE)
_WINDOWS_RESERVED_NAMES = {
    "con",
    "prn",
    "aux",
    "nul",
    *(f"com{index}" for index in range(1, 10)),
    *(f"lpt{index}" for index in range(1, 10)),
}


class ConfigError(ValueError):
    """Raised when a campaign configuration is invalid."""

    def __init__(self, issues: list[str] | tuple[str, ...] | str):
        if isinstance(issues, str):
            issues = [issues]
        self.issues = tuple(issues)
        super().__init__("; ".join(self.issues))


def _normalize_text(value: str) -> str:
    return unicodedata.normalize("NFC", value.replace("\r\n", "\n").replace("\r", "\n"))


def _has_forbidden_control(value: str) -> bool:
    return any(unicodedata.category(char) in {"Cc", "Cs"} and char not in "\n\t" for char in value)


def _has_any_control(value: str) -> bool:
    return any(unicodedata.category(char) in {"Cc", "Cs"} for char in value)


def _portable_media_path(value: object, *, field: str, issues: list[str]) -> str | None:
    if not isinstance(value, str):
        issues.append(f"{field} must be a string")
        return None
    normalized_path = _normalize_text(value)
    path = normalized_path.strip()
    segments = path.split("/")
    invalid_segment = any(
        segment in {"", ".", ".."}
        or segment != segment.strip()
        or segment.endswith(".")
        or len(segment) > 100
        or segment.split(".", 1)[0].casefold() in _WINDOWS_RESERVED_NAMES
        for segment in segments
    )
    if (
        not path
        or normalized_path != path
        or len(path) > MAX_MEDIA_PATH_LENGTH
        or path.startswith("/")
        or "\\" in path
        or ":" in path
        or any(character in '<>"|?*' for character in path)
        or _has_any_control(path)
        or invalid_segment
        or not segments[-1].rsplit(".", 1)[0]
    ):
        issues.append(
            f"{field} must be a portable relative path without empty, dot, parent, "
            "reserved, or whitespace-padded segments"
        )
        return None
    if not path.casefold().endswith(SUPPORTED_MEDIA_SUFFIXES):
        issues.append(f"{field} must end in .jpg, .jpeg, or .png")
        return None
    return path


def _content_body(value: object, *, field: str, issues: list[str]) -> str:
    """Normalize one required body and append bounded-content issues."""
    if not isinstance(value, str):
        issues.append(f"{field} must be a string")
        return ""
    body = _normalize_text(value).strip()
    if not body:
        issues.append(f"{field} must not be empty")
    elif len(body) > 100_000:
        issues.append(f"{field} must be at most 100000 characters")
    if _has_forbidden_control(body):
        issues.append(f"{field} contains unsupported control characters")
    return body


def _content_title(value: object, *, field: str, issues: list[str]) -> str | None:
    """Normalize an optional single-line title and append validation issues."""
    if value is None:
        return None
    if not isinstance(value, str):
        issues.append(f"{field} must be a string when provided")
        return None
    title = _normalize_text(value).strip()
    if not title:
        issues.append(f"{field} must not be empty when provided")
    elif len(title) > 200:
        issues.append(f"{field} must be at most 200 characters")
    if _has_any_control(title):
        issues.append(f"{field} must be a single line without control characters")
    return title


def _content_link(value: object, *, field: str, issues: list[str]) -> str | None:
    """Normalize an optional safe HTTP(S) URL and append validation issues."""
    if value is None:
        return None
    if not isinstance(value, str):
        issues.append(f"{field} must be a string when provided")
        return None
    link = _normalize_text(value).strip()
    if len(link) > 500:
        issues.append(f"{field} must be at most 500 characters")
    try:
        parsed = urlsplit(link)
        valid_http_url = parsed.scheme in {"http", "https"} and bool(parsed.hostname)
    except ValueError:
        parsed = None
        valid_http_url = False
    if not valid_http_url:
        issues.append(f"{field} must be an absolute http or https URL")
    if parsed is not None and (parsed.username is not None or parsed.password is not None):
        issues.append(f"{field} must not contain embedded credentials")
    if _has_forbidden_control(link) or any(char.isspace() for char in link):
        issues.append(f"{field} must not contain whitespace or control characters")
    return link


def _content_hashtags(value: object, *, field: str, issues: list[str]) -> list[str]:
    """Normalize a bounded hashtag list and append validation issues."""
    hashtags: list[str] = []
    if not isinstance(value, list):
        issues.append(f"{field} must be an array of strings")
        return hashtags
    if len(value) > 10:
        issues.append(f"{field} must contain at most 10 items")
    seen: set[str] = set()
    for index, item in enumerate(value):
        item_field = f"{field}[{index}]"
        if not isinstance(item, str):
            issues.append(f"{item_field} must be a string")
            continue
        tag = _normalize_text(item).strip().lstrip("#")
        if not tag:
            issues.append(f"{item_field} must not be empty")
        elif len(tag) > 50:
            issues.append(f"{item_field} must be at most 50 characters")
        elif not _HASHTAG_RE.fullmatch(tag):
            issues.append(f"{item_field} may contain only letters, numbers, and underscores")
        elif tag.casefold() in seen:
            issues.append(f"{item_field} duplicates an earlier hashtag")
        else:
            seen.add(tag.casefold())
            hashtags.append(tag)
    return hashtags


@dataclass(frozen=True, slots=True)
class MediaReference:
    """Portable image metadata that core validates but never dereferences."""

    path: str
    alt_text: str
    platforms: tuple[str, ...]

    def applies_to(self, platform: str) -> bool:
        return platform in self.platforms

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "altText": self.alt_text,
            "platforms": list(self.platforms),
        }

    def to_attachment_dict(self) -> dict[str, str]:
        return {"path": self.path, "altText": self.alt_text}


@dataclass(frozen=True, slots=True)
class PlatformContentVariant:
    """A complete content override for one requested platform."""

    platform: str
    body: str
    title: str | None = None
    link: str | None = None
    hashtags: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        """Return the normalized nested campaign-source representation."""
        result: dict[str, Any] = {
            "body": self.body,
            "hashtags": list(self.hashtags),
        }
        if self.title is not None:
            result["title"] = self.title
        if self.link is not None:
            result["link"] = self.link
        return result


@dataclass(frozen=True, slots=True)
class CampaignConfig:
    """A baseline, optional platform overrides, and requested output platforms."""

    schema_version: int
    name: str
    body: str
    platforms: tuple[str, ...]
    title: str | None = None
    link: str | None = None
    hashtags: tuple[str, ...] = ()
    platform_variants: tuple[PlatformContentVariant, ...] = ()
    platform_limits: tuple[tuple[str, int], ...] = ()
    media: tuple[MediaReference, ...] = ()

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> CampaignConfig:
        """Validate and normalize a JSON-compatible campaign mapping."""
        if not isinstance(raw, Mapping):
            raise ConfigError("campaign configuration must be a JSON object")

        issues: list[str] = []
        unknown = sorted(str(key) for key in raw if key not in _CAMPAIGN_KEYS)
        if unknown:
            issues.append(f"unknown field(s): {', '.join(unknown)}")

        schema_version = raw.get("schemaVersion")
        if isinstance(schema_version, bool) or schema_version != 1:
            issues.append("schemaVersion must be 1")

        name_value = raw.get("name")
        if not isinstance(name_value, str):
            issues.append("name must be a string")
            name = ""
        else:
            name = _normalize_text(name_value).strip()
            if not name:
                issues.append("name must not be empty")
            elif len(name) > 120:
                issues.append("name must be at most 120 characters")
            if _has_any_control(name):
                issues.append("name must be a single line without control characters")

        body = _content_body(raw.get("body"), field="body", issues=issues)
        title = _content_title(raw.get("title"), field="title", issues=issues)
        link = _content_link(raw.get("link"), field="link", issues=issues)
        hashtags = _content_hashtags(raw.get("hashtags", []), field="hashtags", issues=issues)

        platforms_value = raw.get("platforms")
        platforms: list[str] = []
        if not isinstance(platforms_value, list):
            issues.append("platforms must be a non-empty array")
        else:
            if not platforms_value:
                issues.append("platforms must contain at least one platform")
            seen_platforms: set[str] = set()
            for index, value in enumerate(platforms_value):
                if not isinstance(value, str):
                    issues.append(f"platforms[{index}] must be a string")
                    continue
                platform = value.strip().lower()
                if platform not in SUPPORTED_PLATFORMS:
                    supported = ", ".join(SUPPORTED_PLATFORMS)
                    issues.append(f"platforms[{index}] must be one of: {supported}")
                elif platform in seen_platforms:
                    issues.append(f"platforms[{index}] duplicates {platform}")
                else:
                    seen_platforms.add(platform)
                    platforms.append(platform)

        platform_variants_value = raw.get("platformVariants", {})
        platform_variants: list[PlatformContentVariant] = []
        if not isinstance(platform_variants_value, Mapping):
            issues.append("platformVariants must be an object mapping platforms to content")
        else:
            if len(platform_variants_value) > len(SUPPORTED_PLATFORMS):
                issues.append(
                    f"platformVariants must contain at most {len(SUPPORTED_PLATFORMS)} entries"
                )
            parsed_variants: dict[str, PlatformContentVariant] = {}
            for key, variant_value in platform_variants_value.items():
                if not isinstance(key, str):
                    issues.append("platformVariants keys must be platform strings")
                    continue
                field = f"platformVariants.{key}"
                if key not in SUPPORTED_PLATFORMS:
                    issues.append(
                        f"{field} must use a canonical platform name: "
                        f"{', '.join(SUPPORTED_PLATFORMS)}"
                    )
                    continue
                if key not in platforms:
                    issues.append(f"{field} is not useful unless {key} is requested")
                if not isinstance(variant_value, Mapping):
                    issues.append(f"{field} must be an object")
                    continue

                unknown_variant = sorted(
                    str(item_key)
                    for item_key in variant_value
                    if item_key not in {"title", "body", "link", "hashtags"}
                )
                if unknown_variant:
                    issues.append(f"{field} has unknown field(s): {', '.join(unknown_variant)}")

                variant_body = _content_body(
                    variant_value.get("body"), field=f"{field}.body", issues=issues
                )
                variant_title = _content_title(
                    variant_value.get("title"), field=f"{field}.title", issues=issues
                )
                variant_link = _content_link(
                    variant_value.get("link"), field=f"{field}.link", issues=issues
                )
                variant_hashtags = _content_hashtags(
                    variant_value.get("hashtags", []),
                    field=f"{field}.hashtags",
                    issues=issues,
                )

                if variant_body:
                    parsed_variants[key] = PlatformContentVariant(
                        platform=key,
                        title=variant_title,
                        body=variant_body,
                        link=variant_link,
                        hashtags=tuple(variant_hashtags),
                    )

            platform_variants.extend(
                parsed_variants[platform]
                for platform in SUPPORTED_PLATFORMS
                if platform in parsed_variants
            )

        platform_limits_value = raw.get("platformLimits", {})
        parsed_limits: dict[str, int] = {}
        if not isinstance(platform_limits_value, Mapping):
            issues.append("platformLimits must be an object mapping platforms to integers")
        else:
            for key, value in platform_limits_value.items():
                if not isinstance(key, str):
                    issues.append("platformLimits keys must be platform strings")
                    continue
                platform = key.strip().lower()
                if platform not in SUPPORTED_PLATFORMS:
                    supported = ", ".join(SUPPORTED_PLATFORMS)
                    issues.append(f"platformLimits.{key} must name one of: {supported}")
                    continue
                if platform in parsed_limits:
                    issues.append(f"platformLimits.{key} duplicates {platform}")
                    continue
                if platform not in platforms:
                    issues.append(
                        f"platformLimits.{key} is not useful unless {platform} is requested"
                    )
                if isinstance(value, bool) or not isinstance(value, int):
                    issues.append(f"platformLimits.{key} must be an integer")
                elif (
                    not 1
                    <= value
                    <= (100_000 if platform == "mastodon" else PLATFORM_LIMITS[platform])
                ):
                    maximum = 100_000 if platform == "mastodon" else PLATFORM_LIMITS[platform]
                    issues.append(f"platformLimits.{key} must be between 1 and {maximum}")
                else:
                    parsed_limits[platform] = value

        media_value = raw.get("media", [])
        media: list[MediaReference] = []
        seen_media_paths: set[str] = set()
        media_counts = dict.fromkeys(SUPPORTED_PLATFORMS, 0)
        if not isinstance(media_value, list):
            issues.append("media must be an array of image references")
        else:
            if len(media_value) > MAX_MEDIA_REFERENCES:
                issues.append(f"media must contain at most {MAX_MEDIA_REFERENCES} references")
            for index, media_item in enumerate(media_value[:MAX_MEDIA_REFERENCES]):
                field = f"media[{index}]"
                if not isinstance(media_item, Mapping):
                    issues.append(f"{field} must be an object")
                    continue
                unknown_media = sorted(
                    str(key) for key in media_item if key not in {"path", "altText", "platforms"}
                )
                if unknown_media:
                    issues.append(f"{field} has unknown field(s): {', '.join(unknown_media)}")

                path = _portable_media_path(
                    media_item.get("path"), field=f"{field}.path", issues=issues
                )
                if path is not None:
                    path_key = path.casefold()
                    if path_key in seen_media_paths:
                        issues.append(f"{field}.path duplicates an earlier media path")
                        path = None
                    else:
                        seen_media_paths.add(path_key)

                alt_value = media_item.get("altText")
                if not isinstance(alt_value, str):
                    issues.append(f"{field}.altText must be a string")
                    alt_text = ""
                else:
                    alt_text = _normalize_text(alt_value).strip()
                    if not alt_text:
                        issues.append(f"{field}.altText must not be empty")
                    elif len(alt_text) > MAX_ALT_TEXT_LENGTH:
                        issues.append(
                            f"{field}.altText must be at most {MAX_ALT_TEXT_LENGTH} characters"
                        )
                    if _has_any_control(alt_text):
                        issues.append(
                            f"{field}.altText must be a single line without control characters"
                        )

                targets_value = media_item.get("platforms")
                selected_targets: set[str] = set()
                if targets_value is None:
                    selected_targets.update(platforms)
                elif not isinstance(targets_value, list):
                    issues.append(f"{field}.platforms must be a non-empty array")
                else:
                    if not targets_value:
                        issues.append(f"{field}.platforms must contain at least one platform")
                    if len(targets_value) > len(SUPPORTED_PLATFORMS):
                        issues.append(
                            f"{field}.platforms must contain at most "
                            f"{len(SUPPORTED_PLATFORMS)} items"
                        )
                    for target_index, target_value in enumerate(targets_value):
                        target_field = f"{field}.platforms[{target_index}]"
                        if not isinstance(target_value, str):
                            issues.append(f"{target_field} must be a string")
                            continue
                        target = target_value.strip().lower()
                        if target not in SUPPORTED_PLATFORMS:
                            issues.append(
                                f"{target_field} must be one of: {', '.join(SUPPORTED_PLATFORMS)}"
                            )
                        elif target not in platforms:
                            issues.append(f"{target_field} is not requested by the campaign")
                        elif target in selected_targets:
                            issues.append(f"{target_field} duplicates {target}")
                        else:
                            selected_targets.add(target)

                targets = tuple(platform for platform in platforms if platform in selected_targets)
                for target in targets:
                    media_counts[target] += 1
                    if media_counts[target] > MAX_MEDIA_PER_PLATFORM:
                        issues.append(
                            f"media provides more than {MAX_MEDIA_PER_PLATFORM} images for {target}"
                        )
                if path is not None and alt_text and targets:
                    media.append(MediaReference(path, alt_text, targets))

        if issues:
            raise ConfigError(issues)

        return cls(
            schema_version=1,
            name=name,
            title=title,
            body=body,
            link=link,
            hashtags=tuple(hashtags),
            platforms=tuple(platforms),
            platform_variants=tuple(platform_variants),
            platform_limits=tuple(
                (platform, parsed_limits[platform])
                for platform in SUPPORTED_PLATFORMS
                if platform in parsed_limits
            ),
            media=tuple(media),
        )

    def limit_for(self, platform: str) -> int:
        """Return the configured or default character limit for a platform."""
        overrides = dict(self.platform_limits)
        return overrides.get(platform, PLATFORM_LIMITS[platform])

    def variant_for(self, platform: str) -> PlatformContentVariant | None:
        """Return a complete content override for a platform, when configured."""
        return next(
            (variant for variant in self.platform_variants if variant.platform == platform),
            None,
        )

    def to_dict(self) -> dict[str, Any]:
        """Return the normalized, JSON-compatible configuration."""
        result: dict[str, Any] = {
            "schemaVersion": self.schema_version,
            "name": self.name,
            "body": self.body,
            "hashtags": list(self.hashtags),
            "platforms": list(self.platforms),
        }
        if self.title is not None:
            result["title"] = self.title
        if self.link is not None:
            result["link"] = self.link
        if self.platform_variants:
            result["platformVariants"] = {
                variant.platform: variant.to_dict() for variant in self.platform_variants
            }
        if self.platform_limits:
            result["platformLimits"] = dict(self.platform_limits)
        if self.media:
            result["media"] = [reference.to_dict() for reference in self.media]
        return result


@dataclass(frozen=True, slots=True)
class QualityIssue:
    """One stable, machine-readable campaign quality finding."""

    code: str
    severity: str
    platform: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {
            "code": self.code,
            "severity": self.severity,
            "platform": self.platform,
            "message": self.message,
        }


@dataclass(frozen=True, slots=True)
class CampaignCheck:
    """A quality-gate result for one built campaign."""

    campaign_id: str
    publishable: bool
    issues: tuple[QualityIssue, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": 1,
            "campaignId": self.campaign_id,
            "publishable": self.publishable,
            "issues": [issue.to_dict() for issue in self.issues],
        }


@dataclass(frozen=True, slots=True)
class PlatformDraft:
    """Copy-ready content and validation metadata for one platform."""

    platform: str
    content: str
    character_count: int
    original_character_count: int
    character_limit: int
    truncated: bool
    warnings: tuple[str, ...] = ()
    media: tuple[MediaReference, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "platform": self.platform,
            "content": self.content,
            "characterCount": self.character_count,
            "originalCharacterCount": self.original_character_count,
            "characterLimit": self.character_limit,
            "truncated": self.truncated,
            "warnings": list(self.warnings),
            "media": [reference.to_attachment_dict() for reference in self.media],
        }


@dataclass(frozen=True, slots=True)
class CampaignBundle:
    """Deterministic result of packaging one campaign."""

    campaign_id: str
    source_hash: str
    name: str
    drafts: tuple[PlatformDraft, ...]
    media: tuple[MediaReference, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": 1,
            "campaignId": self.campaign_id,
            "sourceHash": self.source_hash,
            "name": self.name,
            "media": [reference.to_dict() for reference in self.media],
            "drafts": [draft.to_dict() for draft in self.drafts],
        }
