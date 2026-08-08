from __future__ import annotations

import json
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

import pytest
from jsonschema import Draft202012Validator, FormatChecker

from samsarix_creative_spirals import (
    CampaignPlanReview,
    ConfigError,
    PlanReviewFinding,
    build_campaign_plan,
    collect_campaign_plan_media,
    create_campaign_plan_review,
    export_campaign_plan_review,
    load_campaign_plan,
    load_campaign_plan_review,
    load_plan_review_schema,
    verify_campaign_plan_review,
)

from media_helpers import png_image


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _write_plan(root: Path, campaign_data: dict[str, Any]) -> Path:
    _write_json(root / "campaign.json", campaign_data)
    path = root / "plan.json"
    _write_json(
        path,
        {
            "schemaVersion": 1,
            "name": "Review feedback journey",
            "items": [
                {
                    "campaign": "campaign.json",
                    "intendedAt": "2026-08-10T13:00:00Z",
                }
            ],
        },
    )
    return path


def test_create_export_load_schema_and_verify_blocking_review(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    bundle = build_campaign_plan(load_campaign_plan(_write_plan(tmp_path, campaign_data)))
    review = create_campaign_plan_review(
        bundle,
        decision="request-changes",
        reviewed_by="Brand reviewer",
        reviewed_at=datetime(2026, 8, 8, 15, 30, tzinfo=timezone.utc),
        findings=(
            PlanReviewFinding(
                message="The launch claim needs evidence.",
                item=1,
                platform="linkedin",
                suggestion="Link the supporting benchmark or narrow the claim.",
            ),
        ),
        note="Resolve before release-owner approval.",
    )
    path = export_campaign_plan_review(review, tmp_path / "plan.review.json")
    loaded = load_campaign_plan_review(path)
    result = verify_campaign_plan_review(bundle, loaded)

    assert loaded == review
    assert review.review_id == f"scr_{review.review_hash[:12]}"
    assert result.valid is True
    assert result.blocking is True
    assert result.to_dict()["issues"] == []
    assert review.to_dict()["reviewedAt"] == "2026-08-08T15:30:00Z"
    Draft202012Validator(load_plan_review_schema(), format_checker=FormatChecker()).validate(
        review.to_dict()
    )
    assert CampaignPlanReview.from_dict(review.to_dict()) == review

    with pytest.raises(ConfigError, match="refusing to overwrite"):
        export_campaign_plan_review(review, path)


def test_comment_review_is_current_but_not_blocking(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    bundle = build_campaign_plan(load_campaign_plan(_write_plan(tmp_path, campaign_data)))
    review = create_campaign_plan_review(
        bundle,
        decision="comment",
        reviewed_by="Editorial reviewer",
        findings=(PlanReviewFinding("Consider a shorter opening sentence."),),
    )

    result = verify_campaign_plan_review(bundle, review)

    assert result.valid is True
    assert result.blocking is False
    assert "note" not in review.to_dict()
    assert "media" not in review.to_dict()


def test_review_invalidates_when_exact_source_changes(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    plan_path = _write_plan(tmp_path, campaign_data)
    original = build_campaign_plan(load_campaign_plan(plan_path))
    review = create_campaign_plan_review(
        original,
        decision="reject",
        reviewed_by="Legal reviewer",
        findings=(PlanReviewFinding("The current claim cannot be substantiated."),),
    )
    _write_plan(tmp_path, {**campaign_data, "body": "A narrower, supported launch claim."})

    result = verify_campaign_plan_review(build_campaign_plan(load_campaign_plan(plan_path)), review)

    assert result.valid is False
    assert result.blocking is False
    assert [issue.code for issue in result.issues] == ["source-changed", "plan-id-changed"]


def test_review_can_bind_and_detect_exact_media_changes(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    campaign_data["media"] = [{"path": "media/launch.png", "altText": "Campaign review dashboard"}]
    plan_path = _write_plan(tmp_path, campaign_data)
    image = tmp_path / "media" / "launch.png"
    image.parent.mkdir()
    image.write_bytes(png_image())
    bundle = build_campaign_plan(load_campaign_plan(plan_path))
    media = collect_campaign_plan_media(bundle, tmp_path).index
    review = create_campaign_plan_review(
        bundle,
        decision="request-changes",
        reviewed_by="Visual reviewer",
        findings=(PlanReviewFinding("Increase text contrast in the supplied image.", item=1),),
        media=media,
    )

    assert verify_campaign_plan_review(bundle, review, media=media).valid is True
    assert verify_campaign_plan_review(bundle, review).valid is False
    mismatched = replace(media, media_hash="f" * 64)
    result = verify_campaign_plan_review(bundle, review, media=mismatched)
    assert result.valid is False
    assert any(issue.code == "media-changed" for issue in result.issues)


def test_review_rejects_tampering_and_aggregates_invalid_fields(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    bundle = build_campaign_plan(load_campaign_plan(_write_plan(tmp_path, campaign_data)))
    valid = create_campaign_plan_review(
        bundle,
        decision="comment",
        reviewed_by="Reviewer",
        findings=(PlanReviewFinding("One observation."),),
    ).to_dict()
    tampered = json.loads(json.dumps(valid))
    tampered["findings"][0]["message"] = "Changed after hashing."
    with pytest.raises(ConfigError, match="does not match canonical plan review content"):
        CampaignPlanReview.from_dict(tampered)

    invalid = {
        **valid,
        "schemaVersion": False,
        "artifactType": "plan",
        "reviewId": "bad",
        "reviewHash": "bad",
        "planId": "bad",
        "sourceHash": "bad",
        "decision": "approve",
        "reviewedBy": " ",
        "reviewedAt": "yesterday",
        "findings": [
            {
                "message": " ",
                "platform": "instagram",
                "suggestion": None,
                "extra": True,
            }
        ],
        "note": None,
        "extra": True,
    }
    with pytest.raises(ConfigError) as caught:
        CampaignPlanReview.from_dict(invalid)
    message = str(caught.value)
    for expected in (
        "unknown plan review field",
        "schemaVersion must be 1",
        "artifactType must be plan-review",
        "reviewId must be",
        "reviewHash must be",
        "planId must be",
        "sourceHash must be",
        "decision must be one of",
        "reviewedBy must not be empty",
        "reviewedAt must be",
        "findings[0] has unknown field",
        "findings[0].message must not be empty",
        "findings[0].platform must be",
        "findings[0].suggestion must be a string",
        "note must be a string",
    ):
        assert expected in message


def test_public_review_values_enforce_bounded_invariants(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    with pytest.raises(ConfigError, match="platform requires an item"):
        PlanReviewFinding("Targeted feedback", platform="x")
    with pytest.raises(ConfigError, match="message must not be empty"):
        PlanReviewFinding(" ")

    bundle = build_campaign_plan(load_campaign_plan(_write_plan(tmp_path, campaign_data)))
    with pytest.raises(ConfigError, match="targets item 2, but the plan has 1 item"):
        create_campaign_plan_review(
            bundle,
            decision="request-changes",
            reviewed_by="Reviewer",
            findings=(PlanReviewFinding("Missing target", item=2),),
        )

    with pytest.raises(ConfigError) as caught:
        create_campaign_plan_review(
            bundle,
            decision="approve",
            reviewed_by="\t",
            reviewed_at=datetime(2026, 8, 8, 15, 30),
            findings=(),
        )
    assert "decision" in str(caught.value)
    assert "reviewed_by" in str(caught.value)
    assert "timezone" in str(caught.value)
    assert "findings" in str(caught.value)


def test_review_runtime_guards_cover_direct_and_malformed_values(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    finding_issues: list[str] = []
    assert (
        PlanReviewFinding.from_dict("not-an-object", field="findings[0]", issues=finding_issues)
        is None
    )
    assert finding_issues == ["findings[0] must be an object"]

    with pytest.raises(ConfigError, match="plan review must be a JSON object"):
        CampaignPlanReview.from_dict(cast(Any, []))

    bundle = build_campaign_plan(load_campaign_plan(_write_plan(tmp_path, campaign_data)))
    review = create_campaign_plan_review(
        bundle,
        decision="comment",
        reviewed_by="Reviewer",
        findings=(PlanReviewFinding("Current observation."),),
    )
    malformed_findings = {**review.to_dict(), "findings": {}}
    with pytest.raises(ConfigError, match="findings must be a non-empty array"):
        CampaignPlanReview.from_dict(malformed_findings)

    wrong_id = {**review.to_dict(), "reviewId": "scr_ffffffffffff"}
    with pytest.raises(ConfigError, match="review_id does not match review_hash"):
        CampaignPlanReview.from_dict(wrong_id)

    with pytest.raises(ConfigError) as direct:
        CampaignPlanReview(
            review_id="bad",
            review_hash="bad",
            plan_id="bad",
            source_hash="bad",
            decision="approve",
            reviewed_by=" ",
            reviewed_at=datetime(2026, 8, 8),
            findings=cast(Any, ("not-a-finding",)),
            note=" ",
            media=cast(Any, object()),
        )
    direct_message = str(direct.value)
    assert "review_id must be" in direct_message
    assert "review_hash must be" in direct_message
    assert "plan_id must be" in direct_message
    assert "source_hash must be" in direct_message
    assert "decision must be" in direct_message
    assert "reviewed_at must be" in direct_message
    assert "findings must contain PlanReviewFinding" in direct_message
    assert "media must be" in direct_message

    with pytest.raises(ConfigError, match="findings must contain between"):
        CampaignPlanReview(
            review_id=review.review_id,
            review_hash=review.review_hash,
            plan_id=review.plan_id,
            source_hash=review.source_hash,
            decision=review.decision,
            reviewed_by=review.reviewed_by,
            reviewed_at=review.reviewed_at,
            findings=(),
        )

    with pytest.raises(ConfigError, match="findings must contain PlanReviewFinding"):
        create_campaign_plan_review(
            bundle,
            decision="comment",
            reviewed_by="Reviewer",
            findings=cast(Any, ("not-a-finding",)),
        )
