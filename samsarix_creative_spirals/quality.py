# Copyright (c) 2026 Samsarix LLC
# SPDX-License-Identifier: MPL-2.0

"""Deterministic quality gates for built campaign drafts."""

from __future__ import annotations

from .models import CampaignBundle, CampaignCheck, QualityIssue

_TRUNCATION_WARNING = "Body was truncated to fit the platform limit."


def check_campaign(
    bundle: CampaignBundle,
    *,
    warnings_as_errors: bool = False,
) -> CampaignCheck:
    """Evaluate whether a built campaign is ready for review or automation."""
    issues: list[QualityIssue] = []
    for draft in bundle.drafts:
        if draft.truncated:
            issues.append(
                QualityIssue(
                    code="truncated",
                    severity="error",
                    platform=draft.platform,
                    message="Draft content was truncated to fit the platform limit.",
                )
            )
        for warning in draft.warnings:
            if draft.truncated and warning == _TRUNCATION_WARNING:
                continue
            issues.append(
                QualityIssue(
                    code="review-warning",
                    severity="error" if warnings_as_errors else "warning",
                    platform=draft.platform,
                    message=warning,
                )
            )
    return CampaignCheck(
        campaign_id=bundle.campaign_id,
        publishable=not any(issue.severity == "error" for issue in issues),
        issues=tuple(issues),
    )
