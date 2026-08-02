# Copyright (c) 2026 Samsarix LLC
# SPDX-License-Identifier: MPL-2.0

"""Platform-aware Samsarix content formatting with conservative limits."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable, Iterator

from .models import CampaignConfig, ConfigError, PLATFORM_LIMITS, PlatformDraft

_URL_RE = re.compile(r"https?://[^\s<>()]+", re.IGNORECASE)
_URL_TRAILING_PUNCTUATION = ".,!?;:)]}"
BLUESKY_MAX_BYTES = 3_000


def _x_character_weight(character: str) -> int:
    codepoint = ord(character)
    if 0 <= codepoint <= 4351:
        return 1
    if 8192 <= codepoint <= 8205:
        return 1
    if 8208 <= codepoint <= 8223:
        return 1
    if 8242 <= codepoint <= 8247:
        return 1
    return 2


def x_weighted_length(text: str) -> int:
    """Count text using X's published weighting and 23-character URL rule."""
    normalized = unicodedata.normalize("NFC", text)
    total = 0
    position = 0
    for match in _URL_RE.finditer(normalized):
        total += sum(_x_character_weight(char) for char in normalized[position : match.start()])
        token = match.group(0)
        core = token.rstrip(_URL_TRAILING_PUNCTUATION)
        trailing = token[len(core) :]
        total += 23 if core else 0
        total += sum(_x_character_weight(char) for char in trailing)
        position = match.end()
    total += sum(_x_character_weight(char) for char in normalized[position:])
    return total


def mastodon_weighted_length(text: str) -> int:
    """Count text using Mastodon's documented 23-character URL rule."""
    normalized = unicodedata.normalize("NFC", text)
    total = 0
    position = 0
    for match in _URL_RE.finditer(normalized):
        total += len(normalized[position : match.start()])
        token = match.group(0)
        core = token.rstrip(_URL_TRAILING_PUNCTUATION)
        trailing = token[len(core) :]
        total += 23 if core else 0
        total += len(trailing)
        position = match.end()
    total += len(normalized[position:])
    return total


def _utf16_length(text: str) -> int:
    """Conservatively count code units used by common platform backends."""
    return len(text.encode("utf-16-le")) // 2


def _grapheme_clusters(text: str) -> Iterator[str]:
    """Yield conservative clusters so truncation avoids dangling combining marks."""
    cluster = ""
    join_next = False
    for character in text:
        codepoint = ord(character)
        is_modifier = (
            unicodedata.category(character).startswith("M")
            or 0xFE00 <= codepoint <= 0xFE0F
            or 0x1F3FB <= codepoint <= 0x1F3FF
            or 0xE0020 <= codepoint <= 0xE007F
        )
        regional_pair = (
            0x1F1E6 <= codepoint <= 0x1F1FF
            and len(cluster) == 1
            and 0x1F1E6 <= ord(cluster) <= 0x1F1FF
        )
        if not cluster:
            cluster = character
        elif join_next or is_modifier or regional_pair or character == "\u200d":
            cluster += character
        else:
            yield cluster
            cluster = character
        join_next = character == "\u200d"
    if cluster:
        yield cluster


def grapheme_length(text: str) -> int:
    """Count conservative user-perceived characters for Bluesky output."""
    return sum(1 for _ in _grapheme_clusters(unicodedata.normalize("NFC", text)))


def _text_units(text: str) -> list[str]:
    """Return grapheme-like units while keeping complete URLs atomic."""
    units: list[str] = []
    position = 0
    for match in _URL_RE.finditer(text):
        units.extend(_grapheme_clusters(text[position : match.start()]))
        token = match.group(0)
        core = token.rstrip(_URL_TRAILING_PUNCTUATION)
        trailing = token[len(core) :]
        if core:
            units.append(core)
        units.extend(_grapheme_clusters(trailing))
        position = match.end()
    units.extend(_grapheme_clusters(text[position:]))
    return units


def _format_title(title: str | None, platform: str) -> str | None:
    if title is None or platform in {"x", "bluesky"}:
        return None
    if platform == "discord":
        return f"**{title}**"
    return title


def _compose(
    title: str | None,
    body: str,
    link: str | None,
    hashtags: list[str],
) -> str:
    parts = [part for part in (title, body, link) if part]
    if hashtags:
        parts.append(" ".join(hashtags))
    return "\n\n".join(parts)


def _truncate_body(
    body: str,
    render: Callable[[str], str],
    fits: Callable[[str], bool],
) -> str:
    units = _text_units(body)
    low = 0
    high = len(units)
    best: str | None = None
    while low <= high:
        midpoint = (low + high) // 2
        fragment = "".join(units[:midpoint]).rstrip()
        candidate_body = f"{fragment}…" if fragment else "…"
        if fits(render(candidate_body)):
            best = candidate_body
            low = midpoint + 1
        else:
            high = midpoint - 1
    if best is None:
        raise ConfigError("campaign metadata leaves no room for content on the selected platform")
    return best


def format_platform(config: CampaignConfig, platform: str) -> PlatformDraft:
    """Format and, when needed, safely truncate one platform draft."""
    if platform not in PLATFORM_LIMITS:
        raise ConfigError(f"unsupported platform: {platform}")

    limit = config.limit_for(platform)
    if platform == "x":
        measure = x_weighted_length
    elif platform == "mastodon":
        measure = mastodon_weighted_length
    elif platform == "bluesky":
        measure = grapheme_length
    else:
        measure = _utf16_length

    def fits(value: str) -> bool:
        return measure(value) <= limit and (
            platform != "bluesky" or len(value.encode("utf-8")) <= BLUESKY_MAX_BYTES
        )

    variant = config.variant_for(platform)
    source_title = variant.title if variant is not None else config.title
    source_body = variant.body if variant is not None else config.body
    source_link = variant.link if variant is not None else config.link
    if source_link is not None and config.link_tracking is not None:
        source_link = config.link_tracking.apply_to(source_link, platform)
    source_hashtags = variant.hashtags if variant is not None else config.hashtags
    title = _format_title(source_title, platform)
    hashtags = [f"#{tag}" for tag in source_hashtags]
    warnings: list[str] = []

    def render(body: str, active_hashtags: list[str] | None = None) -> str:
        return _compose(
            title, body, source_link, hashtags if active_hashtags is None else active_hashtags
        )

    original = render(source_body)
    original_count = measure(original)
    active_hashtags = list(hashtags)

    while active_hashtags and not fits(render("…", active_hashtags)):
        active_hashtags.pop()
    if len(active_hashtags) != len(hashtags):
        omitted = len(hashtags) - len(active_hashtags)
        warnings.append(f"Omitted {omitted} hashtag(s) to fit the platform limit.")

    def render_active(body: str) -> str:
        return render(body, active_hashtags)

    content = render_active(source_body)
    truncated = False
    if not fits(content):
        body = _truncate_body(source_body, render_active, fits)
        content = render_active(body)
        truncated = True
        warnings.append("Body was truncated to fit the platform limit.")

    if platform in {"x", "bluesky"} and source_title is not None:
        warnings.append(f"Title is omitted from the {platform} draft.")
    if platform == "mastodon" and any(tag.isdecimal() for tag in source_hashtags):
        warnings.append("Mastodon does not recognize hashtags containing only numbers.")
    if platform == "discord" and ("@everyone" in content or "@here" in content):
        warnings.append("Draft contains a broadcast mention; review before pasting into Discord.")

    character_count = measure(content)
    if not fits(content):
        raise AssertionError(
            f"formatter produced invalid {platform} output for a {limit}-character limit"
        )

    return PlatformDraft(
        platform=platform,
        content=content,
        character_count=character_count,
        original_character_count=original_count,
        character_limit=limit,
        truncated=truncated,
        warnings=tuple(warnings),
        media=tuple(reference for reference in config.media if reference.applies_to(platform)),
    )
