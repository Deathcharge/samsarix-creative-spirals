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

SUPPORTED_PLATFORMS = ("x", "linkedin", "discord")
PLATFORM_LIMITS = {"x": 280, "linkedin": 3000, "discord": 2000}

_CAMPAIGN_KEYS = {
    "schemaVersion",
    "name",
    "title",
    "body",
    "link",
    "hashtags",
    "platforms",
}
_HASHTAG_RE = re.compile(r"^[\w]+$", re.UNICODE)


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


@dataclass(frozen=True, slots=True)
class CampaignConfig:
    """A single source draft and its requested output platforms."""

    schema_version: int
    name: str
    body: str
    platforms: tuple[str, ...]
    title: str | None = None
    link: str | None = None
    hashtags: tuple[str, ...] = ()

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

        body_value = raw.get("body")
        if not isinstance(body_value, str):
            issues.append("body must be a string")
            body = ""
        else:
            body = _normalize_text(body_value).strip()
            if not body:
                issues.append("body must not be empty")
            elif len(body) > 100_000:
                issues.append("body must be at most 100000 characters")
            if _has_forbidden_control(body):
                issues.append("body contains unsupported control characters")

        title_value = raw.get("title")
        title: str | None
        if title_value is None:
            title = None
        elif not isinstance(title_value, str):
            issues.append("title must be a string when provided")
            title = None
        else:
            title = _normalize_text(title_value).strip()
            if not title:
                issues.append("title must not be empty when provided")
            elif len(title) > 200:
                issues.append("title must be at most 200 characters")
            if _has_any_control(title):
                issues.append("title must be a single line without control characters")

        link_value = raw.get("link")
        link: str | None
        if link_value is None:
            link = None
        elif not isinstance(link_value, str):
            issues.append("link must be a string when provided")
            link = None
        else:
            link = _normalize_text(link_value).strip()
            if len(link) > 500:
                issues.append("link must be at most 500 characters")
            try:
                parsed = urlsplit(link)
                valid_http_url = parsed.scheme in {"http", "https"} and bool(parsed.hostname)
            except ValueError:
                parsed = None
                valid_http_url = False
            if not valid_http_url:
                issues.append("link must be an absolute http or https URL")
            if parsed is not None and (parsed.username is not None or parsed.password is not None):
                issues.append("link must not contain embedded credentials")
            if _has_forbidden_control(link) or any(char.isspace() for char in link):
                issues.append("link must not contain whitespace or control characters")

        hashtags_value = raw.get("hashtags", [])
        hashtags: list[str] = []
        if not isinstance(hashtags_value, list):
            issues.append("hashtags must be an array of strings")
        else:
            if len(hashtags_value) > 10:
                issues.append("hashtags must contain at most 10 items")
            seen: set[str] = set()
            for index, value in enumerate(hashtags_value):
                if not isinstance(value, str):
                    issues.append(f"hashtags[{index}] must be a string")
                    continue
                tag = _normalize_text(value).strip().lstrip("#")
                if not tag:
                    issues.append(f"hashtags[{index}] must not be empty")
                elif len(tag) > 50:
                    issues.append(f"hashtags[{index}] must be at most 50 characters")
                elif not _HASHTAG_RE.fullmatch(tag):
                    issues.append(
                        f"hashtags[{index}] may contain only letters, numbers, and underscores"
                    )
                elif tag.casefold() in seen:
                    issues.append(f"hashtags[{index}] duplicates an earlier hashtag")
                else:
                    seen.add(tag.casefold())
                    hashtags.append(tag)

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
        return result


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

    def to_dict(self) -> dict[str, Any]:
        return {
            "platform": self.platform,
            "content": self.content,
            "characterCount": self.character_count,
            "originalCharacterCount": self.original_character_count,
            "characterLimit": self.character_limit,
            "truncated": self.truncated,
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True, slots=True)
class CampaignBundle:
    """Deterministic result of packaging one campaign."""

    campaign_id: str
    source_hash: str
    name: str
    drafts: tuple[PlatformDraft, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": 1,
            "campaignId": self.campaign_id,
            "sourceHash": self.source_hash,
            "name": self.name,
            "drafts": [draft.to_dict() for draft in self.drafts],
        }
