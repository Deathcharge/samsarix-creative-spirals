# Copyright (c) 2026 Samsarix LLC
# SPDX-License-Identifier: MPL-2.0

"""Local-first, reviewable social campaign packaging by Samsarix."""

from .models import CampaignBundle, CampaignConfig, ConfigError, PlatformDraft
from .schema import load_campaign_schema
from .workflow import build_campaign, export_campaign, load_campaign

__version__ = "0.2.0"

__all__ = [
    "CampaignBundle",
    "CampaignConfig",
    "ConfigError",
    "PlatformDraft",
    "build_campaign",
    "export_campaign",
    "load_campaign_schema",
    "load_campaign",
]
