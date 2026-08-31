# Copyright (c) 2026 Samsarix LLC
# SPDX-License-Identifier: MPL-2.0

"""Starter Samsarix campaign configuration."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from typing import Any

from .models import CampaignConfig, ConfigError, SUPPORTED_PLATFORMS
from .plan_import import CampaignPlanImport, ImportedCampaign


def starter_campaign_plan(
    *,
    name: str = "Release sequence",
    platforms: Sequence[str] = SUPPORTED_PLATFORMS,
    start_at: datetime | None = None,
) -> CampaignPlanImport:
    """Create editable announcement/follow-up sources without I/O or approval.

    Times are absent by default. An explicit aware start time places the follow-up
    48 elapsed hours later in UTC. Save with ``export_campaign_plan_import``.
    """
    if (
        not isinstance(platforms, Sequence)
        or isinstance(platforms, (str, bytes))
        or not 1 <= len(platforms) <= len(SUPPORTED_PLATFORMS)
    ):
        raise ConfigError("platforms must be a sequence of one to five canonical platform names")
    start = None
    follow_up = None
    if start_at is not None:
        if not isinstance(start_at, datetime) or start_at.utcoffset() is None:
            raise ConfigError("start_at must be a datetime with timezone information")
        try:
            start = start_at.astimezone(timezone.utc)
            follow_up = start + timedelta(hours=48)
        except (OverflowError, ValueError) as error:
            raise ConfigError("start_at must leave room for a follow-up 48 hours later") from error

    announcement = CampaignConfig.from_dict(
        {
            "schemaVersion": 1,
            "name": "Release announcement",
            "title": "A new release to explore",
            "body": (
                "Our next release is ready to review. Read the release notes for details "
                "and tell us what you would like to try."
            ),
            "link": "https://example.com/release",
            "hashtags": ["release"],
            "platforms": list(platforms),
        }
    )
    announcement = replace(
        announcement,
        platforms=tuple(
            platform for platform in SUPPORTED_PLATFORMS if platform in announcement.platforms
        ),
    )
    follow_up_campaign = CampaignConfig.from_dict(
        {
            "schemaVersion": 1,
            "name": "Release follow-up",
            "title": "What would help you get started?",
            "body": (
                "Have you explored the release notes? Share a question or a workflow "
                "you would like us to walk through."
            ),
            "link": "https://example.com/release",
            "hashtags": ["release"],
            "platforms": list(announcement.platforms),
        }
    )
    return CampaignPlanImport(
        name=name,
        required_platforms=announcement.platforms,
        items=(
            ImportedCampaign(1, "campaigns/001-announcement.json", announcement, start),
            ImportedCampaign(2, "campaigns/002-follow-up.json", follow_up_campaign, follow_up),
        ),
    )


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
