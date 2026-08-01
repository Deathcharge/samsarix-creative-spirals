# Copyright (c) 2026 Samsarix LLC
# SPDX-License-Identifier: MPL-2.0

"""Local-first, reviewable social campaign packaging by Samsarix."""

from .models import (
    CampaignBundle,
    CampaignCheck,
    CampaignConfig,
    ConfigError,
    PlatformDraft,
    QualityIssue,
)
from .quality import check_campaign
from .schema import load_campaign_schema
from .workflow import build_campaign, export_campaign, load_campaign

__version__ = "0.3.0"

__all__ = [
    "CampaignBundle",
    "CampaignCheck",
    "CampaignConfig",
    "ConfigError",
    "PlatformDraft",
    "QualityIssue",
    "build_campaign",
    "check_campaign",
    "export_campaign",
    "load_campaign_schema",
    "load_campaign",
]
