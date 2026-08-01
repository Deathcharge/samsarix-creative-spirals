# Copyright (c) 2026 Samsarix LLC
# SPDX-License-Identifier: MPL-2.0

"""Starter Samsarix campaign configuration."""

from __future__ import annotations

from typing import Any


def starter_campaign() -> dict[str, Any]:
    """Return a complete example suitable for JSON serialization."""
    return {
        "schemaVersion": 1,
        "name": "Product launch",
        "title": "We shipped something useful",
        "body": (
            "Today we are sharing a focused release that turns one approved draft "
            "into reviewable, platform-ready content."
        ),
        "link": "https://example.com/launch",
        "hashtags": ["buildinpublic", "product"],
        "platforms": ["x", "linkedin", "bluesky", "mastodon", "discord"],
    }
