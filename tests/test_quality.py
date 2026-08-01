from __future__ import annotations

from typing import Any

from samsarix_creative_spirals import CampaignConfig, build_campaign, check_campaign


def test_quality_gate_passes_clean_campaign(campaign_data: dict[str, Any]) -> None:
    campaign_data["platforms"] = ["linkedin"]
    result = check_campaign(build_campaign(CampaignConfig.from_dict(campaign_data)))

    assert result.publishable is True
    assert result.issues == ()
    assert result.to_dict()["publishable"] is True


def test_quality_gate_fails_once_for_truncation(campaign_data: dict[str, Any]) -> None:
    campaign_data.pop("title")
    campaign_data.pop("link")
    campaign_data["hashtags"] = []
    campaign_data["platforms"] = ["x"]
    campaign_data["body"] = "long content " * 100

    result = check_campaign(build_campaign(campaign_data))

    assert result.publishable is False
    assert [(issue.code, issue.severity) for issue in result.issues] == [("truncated", "error")]


def test_quality_gate_can_promote_warnings_to_errors(campaign_data: dict[str, Any]) -> None:
    campaign_data["platforms"] = ["x"]
    bundle = build_campaign(campaign_data)

    normal = check_campaign(bundle)
    strict = check_campaign(bundle, warnings_as_errors=True)

    assert normal.publishable is True
    assert normal.issues[0].severity == "warning"
    assert strict.publishable is False
    assert strict.issues[0].severity == "error"
