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
from .plans import (
    CampaignPlan,
    CampaignPlanBundle,
    CampaignPlanCheck,
    CampaignPlanItem,
    PlanIssue,
    PlannedCampaign,
    build_campaign_plan,
    check_campaign_plan,
    export_campaign_plan,
    load_campaign_plan,
    render_plan_calendar,
)
from .schema import load_campaign_schema, load_plan_schema
from .workflow import build_campaign, export_campaign, load_campaign

__version__ = "0.4.0"

__all__ = [
    "CampaignBundle",
    "CampaignCheck",
    "CampaignConfig",
    "CampaignPlan",
    "CampaignPlanBundle",
    "CampaignPlanCheck",
    "CampaignPlanItem",
    "ConfigError",
    "PlanIssue",
    "PlannedCampaign",
    "PlatformDraft",
    "QualityIssue",
    "build_campaign",
    "build_campaign_plan",
    "check_campaign",
    "check_campaign_plan",
    "export_campaign",
    "export_campaign_plan",
    "load_campaign_plan",
    "load_campaign_schema",
    "load_campaign",
    "load_plan_schema",
    "render_plan_calendar",
]
