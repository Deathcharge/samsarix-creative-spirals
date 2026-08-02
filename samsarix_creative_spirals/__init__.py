# Copyright (c) 2026 Samsarix LLC
# SPDX-License-Identifier: MPL-2.0

"""Local-first, reviewable social campaign packaging by Samsarix."""

from .models import (
    CampaignBundle,
    CampaignCheck,
    CampaignConfig,
    ConfigError,
    MediaReference,
    PlatformDraft,
    QualityIssue,
)
from .quality import check_campaign
from .review import (
    ApprovalCheck,
    ApprovalIssue,
    CampaignApproval,
    CampaignDiff,
    CampaignDraftChange,
    CampaignFieldChange,
    create_campaign_approval,
    diff_campaigns,
    export_campaign_approval,
    load_campaign_approval,
    parse_approval_timestamp,
    verify_campaign_approval,
)
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
    render_plan_adapter,
    render_plan_calendar,
)
from .schema import (
    load_adapter_schema,
    load_approval_schema,
    load_campaign_schema,
    load_plan_schema,
)
from .workflow import build_campaign, export_campaign, load_campaign

__version__ = "0.6.0"

__all__ = [
    "ApprovalCheck",
    "ApprovalIssue",
    "CampaignApproval",
    "CampaignBundle",
    "CampaignCheck",
    "CampaignConfig",
    "CampaignDiff",
    "CampaignDraftChange",
    "CampaignFieldChange",
    "CampaignPlan",
    "CampaignPlanBundle",
    "CampaignPlanCheck",
    "CampaignPlanItem",
    "ConfigError",
    "MediaReference",
    "PlanIssue",
    "PlannedCampaign",
    "PlatformDraft",
    "QualityIssue",
    "build_campaign",
    "build_campaign_plan",
    "check_campaign",
    "check_campaign_plan",
    "create_campaign_approval",
    "diff_campaigns",
    "export_campaign",
    "export_campaign_approval",
    "export_campaign_plan",
    "load_adapter_schema",
    "load_approval_schema",
    "load_campaign",
    "load_campaign_approval",
    "load_campaign_plan",
    "load_campaign_schema",
    "load_plan_schema",
    "parse_approval_timestamp",
    "render_plan_adapter",
    "render_plan_calendar",
    "verify_campaign_approval",
]
