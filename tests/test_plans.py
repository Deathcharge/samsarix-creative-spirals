from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from samsarix_creative_spirals import (
    CampaignPlan,
    ConfigError,
    build_campaign_plan,
    check_campaign_plan,
    export_campaign_plan,
    load_campaign_plan,
    render_plan_calendar,
)


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _write_plan(
    root: Path,
    campaign_data: dict[str, Any],
    *,
    items: list[dict[str, Any]] | None = None,
    required_platforms: list[str] | None = None,
) -> Path:
    _write_json(root / "campaigns" / "release.json", campaign_data)
    plan: dict[str, Any] = {
        "schemaVersion": 1,
        "name": "Release sequence",
        "items": items
        or [
            {
                "campaign": "campaigns/release.json",
                "intendedAt": "2026-08-10T09:00:00-04:00",
            }
        ],
    }
    if required_platforms is not None:
        plan["requiredPlatforms"] = required_platforms
    path = root / "plan.json"
    _write_json(path, plan)
    return path


def test_plan_load_and_build_are_deterministic(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    path = _write_plan(tmp_path, campaign_data, required_platforms=["x", "discord"])

    plan = load_campaign_plan(path)
    first = build_campaign_plan(plan)
    second = build_campaign_plan(plan)

    assert first == second
    assert first.plan_id.startswith("scp_")
    assert first.items[0].source == "campaigns/release.json"
    assert first.items[0].intended_at == datetime(2026, 8, 10, 13, 0, tzinfo=timezone.utc)
    assert first.to_dict()["items"][0]["intendedAt"] == "2026-08-10T13:00:00Z"


def test_plan_identity_includes_referenced_campaign(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    path = _write_plan(tmp_path, campaign_data)
    first = build_campaign_plan(load_campaign_plan(path))

    campaign_data["body"] = "A changed approved message"
    _write_json(tmp_path / "campaigns" / "release.json", campaign_data)
    second = build_campaign_plan(load_campaign_plan(path))

    assert first.plan_id != second.plan_id
    assert first.source_hash != second.source_hash


@pytest.mark.parametrize(
    "source",
    [
        "../campaign.json",
        "/campaign.json",
        "C:/campaign.json",
        "campaigns\\release.json",
        "campaigns/bad?.json",
        "campaigns/bad\tname.json",
    ],
)
def test_plan_rejects_non_portable_or_unconfined_paths(
    tmp_path: Path, campaign_data: dict[str, Any], source: str
) -> None:
    path = _write_plan(tmp_path, campaign_data, items=[{"campaign": source}])

    with pytest.raises(ConfigError, match="portable relative"):
        load_campaign_plan(path)


def test_plan_rejects_uppercase_json_suffix(tmp_path: Path, campaign_data: dict[str, Any]) -> None:
    path = _write_plan(
        tmp_path,
        campaign_data,
        items=[{"campaign": "campaigns/release.JSON"}],
    )

    with pytest.raises(ConfigError, match="portable relative"):
        load_campaign_plan(path)


def test_plan_rejects_symlink_escape(tmp_path: Path, campaign_data: dict[str, Any]) -> None:
    outside = tmp_path.parent / f"{tmp_path.name}-outside-campaign.json"
    _write_json(outside, campaign_data)
    plan_root = tmp_path / "plan-root"
    _write_json(plan_root / "campaigns" / "release.json", campaign_data)
    link = plan_root / "campaigns" / "escape.json"
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("symbolic links are not available in this environment")
    _write_json(
        plan_root / "plan.json",
        {
            "schemaVersion": 1,
            "name": "Escaping plan",
            "items": [{"campaign": "campaigns/escape.json"}],
        },
    )

    with pytest.raises(ConfigError, match="outside the plan directory"):
        load_campaign_plan(plan_root / "plan.json")


@pytest.mark.parametrize(
    "intended_at",
    ["2026-08-10T09:00:00", "2026-08-10 09:00:00Z", "2026-13-10T09:00:00Z"],
)
def test_plan_rejects_invalid_or_offsetless_times(
    tmp_path: Path, campaign_data: dict[str, Any], intended_at: str
) -> None:
    path = _write_plan(
        tmp_path,
        campaign_data,
        items=[{"campaign": "campaigns/release.json", "intendedAt": intended_at}],
    )

    with pytest.raises(ConfigError, match="intendedAt"):
        load_campaign_plan(path)


@pytest.mark.parametrize("intended_at", [None, "2026-08-10T09:00:00-00:00"])
def test_plan_rejects_null_or_unknown_offset_times(
    tmp_path: Path, campaign_data: dict[str, Any], intended_at: object
) -> None:
    path = _write_plan(
        tmp_path,
        campaign_data,
        items=[{"campaign": "campaigns/release.json", "intendedAt": intended_at}],
    )

    with pytest.raises(ConfigError, match="intendedAt"):
        load_campaign_plan(path)


@pytest.mark.parametrize(
    ("fraction", "expected_microsecond"),
    [("1", 100_000), ("12345", 123_450), ("123456789", 123_456)],
)
def test_plan_normalizes_rfc3339_fractional_seconds(
    tmp_path: Path,
    campaign_data: dict[str, Any],
    fraction: str,
    expected_microsecond: int,
) -> None:
    path = _write_plan(
        tmp_path,
        campaign_data,
        items=[
            {
                "campaign": "campaigns/release.json",
                "intendedAt": f"2026-08-10T09:00:00.{fraction}Z",
            }
        ],
    )

    plan = load_campaign_plan(path)

    assert plan.items[0].intended_at == datetime(
        2026, 8, 10, 9, 0, 0, expected_microsecond, tzinfo=timezone.utc
    )


def test_plan_rejects_duplicate_json_fields(tmp_path: Path) -> None:
    path = tmp_path / "plan.json"
    path.write_text(
        '{"schemaVersion":1,"name":"first","name":"second","items":[]}',
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="duplicate JSON field: name"):
        load_campaign_plan(path)


def test_plan_reports_kind_and_json_location(tmp_path: Path) -> None:
    path = tmp_path / "broken-plan.json"
    path.write_text('{"schemaVersion":', encoding="utf-8")

    with pytest.raises(ConfigError, match=r"invalid plan JSON at line 1, column"):
        load_campaign_plan(path)


def test_plan_reports_root_shape_errors(tmp_path: Path) -> None:
    with pytest.raises(ConfigError) as caught:
        CampaignPlan.from_dict(
            {
                "schemaVersion": False,
                "name": 123,
                "requiredPlatforms": "x",
                "items": "campaign.json",
                "extra": True,
            },
            base_dir=tmp_path,
        )

    message = str(caught.value)
    assert "unknown plan field" in message
    assert "schemaVersion must be 1" in message
    assert "name must be a string" in message
    assert "requiredPlatforms must be an array" in message
    assert "items must be a non-empty array" in message


@pytest.mark.parametrize(
    ("name", "message"),
    [
        ("", "must not be empty"),
        ("x" * 121, "at most 120"),
        ("line\nbreak", "single line"),
    ],
)
def test_plan_rejects_invalid_names(tmp_path: Path, name: str, message: str) -> None:
    with pytest.raises(ConfigError, match=message):
        CampaignPlan.from_dict(
            {"schemaVersion": 1, "name": name, "items": []},
            base_dir=tmp_path,
        )


def test_plan_reports_platform_and_item_shape_errors(tmp_path: Path) -> None:
    with pytest.raises(ConfigError) as caught:
        CampaignPlan.from_dict(
            {
                "schemaVersion": 1,
                "name": "Invalid plan",
                "requiredPlatforms": ["x", "x", "unknown", 3, "linkedin", "discord"],
                "items": [
                    None,
                    {"campaign": 42, "unexpected": True},
                    {"campaign": "missing.json"},
                ],
            },
            base_dir=tmp_path,
        )

    message = str(caught.value)
    assert "at most 5" in message
    assert "duplicates x" in message
    assert "must be one of" in message
    assert "must be a string" in message
    assert "items[0] must be an object" in message
    assert "unknown field" in message
    assert "relative JSON file path" in message
    assert "cannot read campaign file" in message


def test_plan_rejects_more_than_one_hundred_items(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="at most 100"):
        CampaignPlan.from_dict(
            {
                "schemaVersion": 1,
                "name": "Too many",
                "items": [None] * 101,
            },
            base_dir=tmp_path,
        )


def test_plan_check_reports_missing_platforms(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    campaign_data.pop("title")
    path = _write_plan(tmp_path, campaign_data, required_platforms=["x", "mastodon"])

    result = check_campaign_plan(build_campaign_plan(load_campaign_plan(path)))

    assert result.publishable is False
    assert any(
        issue.code == "missing-platform" and issue.platform == "mastodon" for issue in result.issues
    )


def test_plan_check_reports_duplicate_and_out_of_order_times(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    campaign_data.pop("title")
    campaign_data["platforms"] = ["linkedin"]
    items = [
        {"campaign": "campaigns/release.json", "intendedAt": "2026-08-10T13:00:00Z"},
        {"campaign": "campaigns/release.json", "intendedAt": "2026-08-10T13:00:00Z"},
        {"campaign": "campaigns/release.json", "intendedAt": "2026-08-10T12:00:00Z"},
    ]
    path = _write_plan(tmp_path, campaign_data, items=items)
    bundle = build_campaign_plan(load_campaign_plan(path))

    result = check_campaign_plan(bundle)
    strict = check_campaign_plan(bundle, warnings_as_errors=True)

    assert result.publishable is True
    assert {issue.code for issue in result.issues} == {"duplicate-time", "out-of-order"}
    assert strict.publishable is False
    assert all(issue.severity == "error" for issue in strict.issues)


def test_plan_check_includes_campaign_quality_failures(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    campaign_data["body"] = "long content " * 1_000
    path = _write_plan(tmp_path, campaign_data)

    result = check_campaign_plan(build_campaign_plan(load_campaign_plan(path)))

    assert result.publishable is False
    assert any(issue.code == "campaign-truncated" for issue in result.issues)


def test_calendar_contains_scheduled_events_and_unscheduled_tasks(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    campaign_data["name"] = "Unicode launch " + "🚀" * 30
    items = [
        {"campaign": "campaigns/release.json", "intendedAt": "2026-08-10T13:00:00Z"},
        {"campaign": "campaigns/release.json"},
    ]
    path = _write_plan(tmp_path, campaign_data, items=items)
    bundle = build_campaign_plan(load_campaign_plan(path))

    calendar = render_plan_calendar(
        bundle,
        generated_at=datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc),
    )

    assert calendar.endswith("\r\n")
    assert "BEGIN:VEVENT\r\n" in calendar
    assert "DTSTART:20260810T130000Z\r\n" in calendar
    assert "TRANSP:TRANSPARENT\r\n" in calendar
    assert "BEGIN:VTODO\r\n" in calendar
    assert "STATUS:NEEDS-ACTION\r\n" in calendar
    assert all(len(line.encode("utf-8")) <= 75 for line in calendar.split("\r\n"))


def test_calendar_rejects_naive_generation_time(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    bundle = build_campaign_plan(load_campaign_plan(_write_plan(tmp_path, campaign_data)))

    with pytest.raises(ConfigError, match="timezone"):
        render_plan_calendar(bundle, generated_at=datetime(2026, 8, 1, 12, 0))


def test_plan_export_writes_manifest_calendar_and_platform_csv(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    path = _write_plan(tmp_path, campaign_data)
    bundle = build_campaign_plan(load_campaign_plan(path))
    generated_at = datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc)

    target = export_campaign_plan(bundle, tmp_path / "outbox", generated_at=generated_at)

    manifest = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["planId"] == bundle.plan_id
    assert manifest["generatedAt"] == "2026-08-01T12:00:00Z"
    assert (target / "calendar.ics").read_bytes().endswith(b"\r\n")
    with (target / "csv" / "x.csv").open(encoding="utf-8", newline="") as csv_file:
        rows = list(csv.DictReader(csv_file))
    assert rows[0]["campaign_id"] == bundle.items[0].bundle.campaign_id
    assert rows[0]["intended_at_utc"] == "2026-08-10T13:00:00Z"
    assert rows[0]["content"] == bundle.items[0].bundle.drafts[0].content

    with pytest.raises(FileExistsError):
        export_campaign_plan(bundle, tmp_path / "outbox", generated_at=generated_at)

    overwritten = export_campaign_plan(
        bundle,
        tmp_path / "outbox",
        overwrite=True,
        generated_at=datetime(2026, 8, 2, 12, 0, tzinfo=timezone.utc),
    )
    updated_manifest = json.loads((overwritten / "manifest.json").read_text(encoding="utf-8"))
    assert updated_manifest["generatedAt"] == "2026-08-02T12:00:00Z"


def test_plan_export_neutralizes_spreadsheet_formula_prefixes(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    campaign_data["name"] = "=RELEASE"
    campaign_data["body"] = "@SUM(A1:A2)"
    bundle = build_campaign_plan(load_campaign_plan(_write_plan(tmp_path, campaign_data)))

    target = export_campaign_plan(bundle, tmp_path / "outbox")

    with (target / "csv" / "x.csv").open(encoding="utf-8", newline="") as csv_file:
        row = next(csv.DictReader(csv_file))
    assert row["name"] == "'=RELEASE"
    assert row["content"].startswith("'@SUM(A1:A2)")


def test_plan_export_overwrite_removes_stale_csv(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    bundle = build_campaign_plan(load_campaign_plan(_write_plan(tmp_path, campaign_data)))
    output = tmp_path / "outbox"
    target = export_campaign_plan(bundle, output)
    stale = target / "csv" / "removed-platform.csv"
    stale.write_text("stale\n", encoding="utf-8")

    export_campaign_plan(bundle, output, overwrite=True)

    assert not stale.exists()


def test_plan_export_handles_platforms_missing_from_some_items(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    second = dict(campaign_data)
    campaign_data["platforms"] = ["x"]
    second["platforms"] = ["mastodon"]
    _write_json(tmp_path / "campaigns" / "release.json", campaign_data)
    _write_json(tmp_path / "campaigns" / "follow-up.json", second)
    _write_json(
        tmp_path / "plan.json",
        {
            "schemaVersion": 1,
            "name": "Split channels",
            "items": [
                {"campaign": "campaigns/release.json"},
                {"campaign": "campaigns/follow-up.json"},
            ],
        },
    )
    plan = load_campaign_plan(tmp_path / "plan.json")
    assert "requiredPlatforms" not in plan.to_dict()
    assert plan.items[0].to_dict() == {"campaign": "campaigns/release.json"}

    target = export_campaign_plan(build_campaign_plan(plan), tmp_path / "outbox")

    with (target / "csv" / "x.csv").open(encoding="utf-8", newline="") as csv_file:
        assert len(list(csv.DictReader(csv_file))) == 1
    with (target / "csv" / "mastodon.csv").open(encoding="utf-8", newline="") as csv_file:
        assert len(list(csv.DictReader(csv_file))) == 1


def test_plan_export_rejects_naive_generation_time_and_file_root(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    bundle = build_campaign_plan(load_campaign_plan(_write_plan(tmp_path, campaign_data)))
    with pytest.raises(ConfigError, match="timezone"):
        export_campaign_plan(bundle, tmp_path / "outbox", generated_at=datetime(2026, 8, 1))

    output_file = tmp_path / "not-a-directory"
    output_file.write_text("keep", encoding="utf-8")
    with pytest.raises(OSError, match="not a directory"):
        export_campaign_plan(bundle, output_file)


def test_plan_export_rejects_symbolic_link_root(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    bundle = build_campaign_plan(load_campaign_plan(_write_plan(tmp_path, campaign_data)))
    actual = tmp_path / "actual-output"
    actual.mkdir()
    linked = tmp_path / "linked-output"
    try:
        linked.symlink_to(actual, target_is_directory=True)
    except OSError:
        pytest.skip("symbolic links are not available in this environment")

    with pytest.raises(OSError, match="symbolic-link"):
        export_campaign_plan(bundle, linked)


def test_plan_export_overwrite_refuses_unexpected_entries(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    bundle = build_campaign_plan(load_campaign_plan(_write_plan(tmp_path, campaign_data)))
    output = tmp_path / "outbox"
    target = export_campaign_plan(bundle, output)
    (target / "private.txt").write_text("keep", encoding="utf-8")

    with pytest.raises(OSError, match="unexpected entry"):
        export_campaign_plan(bundle, output, overwrite=True)

    assert (target / "private.txt").read_text(encoding="utf-8") == "keep"


def test_plan_export_overwrite_rejects_invalid_artifact_type(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    bundle = build_campaign_plan(load_campaign_plan(_write_plan(tmp_path, campaign_data)))
    output = tmp_path / "outbox"
    target = export_campaign_plan(bundle, output)
    calendar = target / "calendar.ics"
    calendar.unlink()
    calendar.mkdir()

    with pytest.raises(OSError, match="invalid plan artifact"):
        export_campaign_plan(bundle, output, overwrite=True)
