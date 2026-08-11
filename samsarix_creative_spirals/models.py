# Copyright (c) 2026 Samsarix LLC
# SPDX-License-Identifier: MPL-2.0

"""Validated data models for local Samsarix campaign packaging."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit

if TYPE_CHECKING:
    from .policy import ContentPolicyBinding

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
MAX_TRACKING_PARAMETERS = 20
MAX_TRACKING_PARAMETER_VALUE_LENGTH = 200
MAX_TRACKED_LINK_LENGTH = 2_000

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
    "linkTracking",
    "media",
}
_HASHTAG_RE = re.compile(r"^[\w]+$", re.UNICODE)
_TRACKING_PARAMETER_RE = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")
_WINDOWS_RESERVED_NAMES = {
    "con",
    "prn",
    "aux",
    "nul",
    *(f"com{index}" for index in range(1, 10)),
    *(f"lpt{index}" for index in range(1, 10)),
}
MAX_CONFIG_ISSUES = 200
MAX_UNKNOWN_FIELDS = 20


def _diagnostic_key(value: object) -> str:
    """Render an untrusted mapping key without terminal control characters."""
    return ascii(str(value))[1:-1]


def _unknown_fields(value: Mapping[Any, Any], allowed: set[str]) -> list[str]:
    unknown: list[str] = []
    for key in value:
        if key not in allowed:
            if len(unknown) == MAX_UNKNOWN_FIELDS:
                unknown.append("additional fields omitted")
                break
            unknown.append(_diagnostic_key(key))
    return sorted(unknown)


class ConfigError(ValueError):
    """Raised when a campaign configuration is invalid."""

    def __init__(self, issues: list[str] | tuple[str, ...] | str):
        if isinstance(issues, str):
            issues = [issues]
        bounded = tuple(issues[:MAX_CONFIG_ISSUES])
        if len(issues) > MAX_CONFIG_ISSUES:
            bounded = (*bounded, "additional validation issues omitted")
        self.issues = bounded
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
    for index, item in enumerate(value[:10]):
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


def _tracking_parameter_map(
    value: object,
    *,
    field: str,
    required: bool,
    issues: list[str],
) -> tuple[tuple[str, str], ...]:
    """Parse one bounded map of canonical tracking parameter names and values."""
    if not isinstance(value, Mapping):
        issues.append(f"{field} must be an object mapping parameter names to values")
        return ()
    if required and not value:
        issues.append(f"{field} must contain at least one parameter")
    if len(value) > MAX_TRACKING_PARAMETERS:
        issues.append(f"{field} must contain at most {MAX_TRACKING_PARAMETERS} parameters")
    parameters: dict[str, str] = {}
    for index, (key, raw_value) in enumerate(value.items()):
        if index >= MAX_TRACKING_PARAMETERS:
            break
        if not isinstance(key, str) or not _TRACKING_PARAMETER_RE.fullmatch(key):
            issues.append(f"{field} parameter names must match {_TRACKING_PARAMETER_RE.pattern}")
            continue
        item_field = f"{field}.{key}"
        if not isinstance(raw_value, str):
            issues.append(f"{item_field} must be a string")
            continue
        parameter_value = _normalize_text(raw_value).strip()
        if not parameter_value:
            issues.append(f"{item_field} must not be empty")
        elif len(parameter_value) > MAX_TRACKING_PARAMETER_VALUE_LENGTH:
            issues.append(
                f"{item_field} must be at most {MAX_TRACKING_PARAMETER_VALUE_LENGTH} characters"
            )
        if _has_any_control(parameter_value):
            issues.append(f"{item_field} must be a single line without control characters")
        if parameter_value and not _has_any_control(parameter_value):
            parameters[key] = parameter_value
    return tuple(sorted(parameters.items()))


@dataclass(frozen=True, slots=True)
class LinkTracking:
    """Deterministic query parameters applied to structured campaign links."""

    parameters: tuple[tuple[str, str], ...] = ()
    platform_parameters: tuple[tuple[str, tuple[tuple[str, str], ...]], ...] = ()

    def parameters_for(self, platform: str) -> tuple[tuple[str, str], ...]:
        """Return merged parameters for a platform in canonical name order."""
        if platform not in SUPPORTED_PLATFORMS:
            raise ConfigError(f"unsupported platform: {platform}")
        merged = dict(self.parameters)
        overrides = dict(self.platform_parameters).get(platform, ())
        merged.update(dict(overrides))
        return tuple(sorted(merged.items()))

    def apply_to(self, link: str, platform: str) -> str:
        """Append encoded parameters before a fragment without replacing existing keys."""
        parameters = self.parameters_for(platform)
        try:
            parsed = urlsplit(link)
        except ValueError as error:
            raise ConfigError(f"cannot apply link tracking to invalid URL: {error}") from error
        existing = {name for name, _ in parse_qsl(parsed.query, keep_blank_values=True)}
        conflicts = tuple(name for name, _ in parameters if name in existing)
        if conflicts:
            raise ConfigError(
                "link tracking would duplicate existing query parameter(s): " + ", ".join(conflicts)
            )
        encoded = urlencode(parameters, quote_via=quote, safe="-._~")
        query = f"{parsed.query}&{encoded}" if parsed.query else encoded
        tracked = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, query, parsed.fragment))
        if len(tracked) > MAX_TRACKED_LINK_LENGTH:
            raise ConfigError(
                f"tracked link must be at most {MAX_TRACKED_LINK_LENGTH} characters for {platform}"
            )
        return tracked

    def to_dict(self) -> dict[str, Any]:
        """Return normalized campaign-source representation."""
        result: dict[str, Any] = {}
        if self.parameters:
            result["parameters"] = dict(self.parameters)
        if self.platform_parameters:
            result["platformParameters"] = {
                platform: dict(parameters) for platform, parameters in self.platform_parameters
            }
        return result


def _tracking_platform_parameter_maps(
    value: object,
    *,
    requested_platforms: tuple[str, ...],
    required: bool,
    issues: list[str],
) -> tuple[tuple[str, tuple[tuple[str, str], ...]], ...]:
    """Parse requested-platform tracking maps in canonical platform order."""
    if not isinstance(value, Mapping):
        issues.append("linkTracking.platformParameters must map platforms to parameter objects")
        return ()
    platform_parameters: dict[str, tuple[tuple[str, str], ...]] = {}
    if required and not value:
        issues.append("linkTracking.platformParameters must contain at least one platform")
    if len(value) > len(SUPPORTED_PLATFORMS):
        issues.append(
            "linkTracking.platformParameters must contain at most "
            f"{len(SUPPORTED_PLATFORMS)} platforms"
        )
    for index, (key, parameter_value) in enumerate(value.items()):
        if index >= len(SUPPORTED_PLATFORMS):
            break
        if not isinstance(key, str) or key not in SUPPORTED_PLATFORMS:
            issues.append(
                "linkTracking.platformParameters keys must be canonical platforms: "
                + ", ".join(SUPPORTED_PLATFORMS)
            )
            continue
        field = f"linkTracking.platformParameters.{key}"
        if key not in requested_platforms:
            issues.append(f"{field} is not useful unless {key} is requested")
        parsed = _tracking_parameter_map(
            parameter_value,
            field=field,
            required=True,
            issues=issues,
        )
        if parsed:
            platform_parameters[key] = parsed
    return tuple(
        (platform, platform_parameters[platform])
        for platform in SUPPORTED_PLATFORMS
        if platform in platform_parameters
    )


def _parse_link_tracking(
    value: object,
    *,
    requested_platforms: tuple[str, ...],
    issues: list[str],
) -> LinkTracking | None:
    """Parse campaign-level defaults and per-platform tracking overrides."""
    if value is None:
        return None
    if not isinstance(value, Mapping):
        issues.append("linkTracking must be an object")
        return None
    unknown = _unknown_fields(value, {"parameters", "platformParameters"})
    if unknown:
        issues.append(f"linkTracking has unknown field(s): {', '.join(unknown)}")

    parameters = _tracking_parameter_map(
        value.get("parameters", {}),
        field="linkTracking.parameters",
        required="parameters" in value,
        issues=issues,
    )
    platform_parameters = _tracking_platform_parameter_maps(
        value.get("platformParameters", {}),
        requested_platforms=requested_platforms,
        required="platformParameters" in value,
        issues=issues,
    )

    if not parameters and not platform_parameters:
        issues.append("linkTracking must define at least one parameter")
        return None
    tracking = LinkTracking(
        parameters=parameters,
        platform_parameters=platform_parameters,
    )
    issues.extend(
        f"linkTracking produces more than {MAX_TRACKING_PARAMETERS} parameters for {platform}"
        for platform in requested_platforms
        if len(tracking.parameters_for(platform)) > MAX_TRACKING_PARAMETERS
    )
    return tracking


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
    link_tracking: LinkTracking | None = None
    media: tuple[MediaReference, ...] = ()

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> CampaignConfig:
        """Validate and normalize a JSON-compatible campaign mapping."""
        if not isinstance(raw, Mapping):
            raise ConfigError("campaign configuration must be a JSON object")

        issues: list[str] = []
        unknown = _unknown_fields(raw, _CAMPAIGN_KEYS)
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
            if len(platforms_value) > len(SUPPORTED_PLATFORMS):
                issues.append(f"platforms must contain at most {len(SUPPORTED_PLATFORMS)} items")
            seen_platforms: set[str] = set()
            for index, value in enumerate(platforms_value[: len(SUPPORTED_PLATFORMS)]):
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
            for index, (key, variant_value) in enumerate(platform_variants_value.items()):
                if index >= len(SUPPORTED_PLATFORMS):
                    break
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

                unknown_variant = _unknown_fields(
                    variant_value, {"title", "body", "link", "hashtags"}
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

        link_tracking = _parse_link_tracking(
            raw.get("linkTracking"),
            requested_platforms=tuple(platforms),
            issues=issues,
        )
        if link_tracking is not None:
            variants_by_platform = {variant.platform: variant for variant in platform_variants}
            linked_platforms = 0
            tracked_platforms = {platform for platform, _ in link_tracking.platform_parameters}
            for platform in platforms:
                variant = variants_by_platform.get(platform)
                effective_link = variant.link if variant is not None else link
                if effective_link is None:
                    if platform in tracked_platforms:
                        issues.append(
                            f"linkTracking.platformParameters.{platform} is not useful "
                            f"without an effective link for {platform}"
                        )
                    continue
                linked_platforms += 1
                try:
                    link_tracking.apply_to(effective_link, platform)
                except ConfigError as error:
                    issues.extend(
                        f"linkTracking for {platform}: {message}" for message in error.issues
                    )
            if not linked_platforms:
                issues.append("linkTracking requires at least one effective campaign link")

        platform_limits_value = raw.get("platformLimits", {})
        parsed_limits: dict[str, int] = {}
        if not isinstance(platform_limits_value, Mapping):
            issues.append("platformLimits must be an object mapping platforms to integers")
        else:
            if len(platform_limits_value) > len(SUPPORTED_PLATFORMS):
                issues.append(
                    f"platformLimits must contain at most {len(SUPPORTED_PLATFORMS)} entries"
                )
            for index, (key, value) in enumerate(platform_limits_value.items()):
                if index >= len(SUPPORTED_PLATFORMS):
                    break
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
                unknown_media = _unknown_fields(media_item, {"path", "altText", "platforms"})
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
            link_tracking=link_tracking,
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
        if self.link_tracking is not None:
            result["linkTracking"] = self.link_tracking.to_dict()
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
    rule_id: str | None = None

    def to_dict(self) -> dict[str, str]:
        result = {
            "code": self.code,
            "severity": self.severity,
            "platform": self.platform,
            "message": self.message,
        }
        if self.rule_id is not None:
            result["ruleId"] = self.rule_id
        return result


@dataclass(frozen=True, slots=True)
class CampaignCheck:
    """A quality-gate result for one built campaign."""

    campaign_id: str
    publishable: bool
    issues: tuple[QualityIssue, ...]
    content_policy: ContentPolicyBinding | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "schemaVersion": 1,
            "campaignId": self.campaign_id,
            "publishable": self.publishable,
            "issues": [issue.to_dict() for issue in self.issues],
        }
        if self.content_policy is not None:
            result["contentPolicy"] = self.content_policy.to_dict()
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
