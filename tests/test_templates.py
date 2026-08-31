from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator, FormatChecker

from samsarix_creative_spirals import (
    ConfigError,
    build_campaign_plan,
    check_campaign_plan,
    export_campaign_plan_import,
    load_campaign_plan,
    load_plan_schema,
    starter_campaign_plan,
)
from samsarix_creative_spirals.cli import main


def test_starter_is_independent_unscheduled_and_quality_valid(tmp_path: Path) -> None:
    first = starter_campaign_plan()
    second = starter_campaign_plan()
    assert first == second and first is not second
    assert len(first.items) == 2
    assert all(item.intended_at is None for item in first.items)
    assert first.required_platforms == ("x", "linkedin", "bluesky", "mastodon", "discord")
    Draft202012Validator(load_plan_schema(), format_checker=FormatChecker()).validate(
        first.plan_dict()
    )
    path = export_campaign_plan_import(first, tmp_path / "release")
    bundle = build_campaign_plan(load_campaign_plan(path))
    assert check_campaign_plan(bundle).publishable
    assert len([draft for item in bundle.items for draft in item.bundle.drafts]) == 10
    assert sorted(p.relative_to(path.parent).as_posix() for p in path.parent.rglob("*.json")) == [
        "campaigns/001-announcement.json",
        "campaigns/002-follow-up.json",
        "plan.json",
    ]
    before = path.read_bytes()
    with pytest.raises(FileExistsError, match="overwrite"):
        export_campaign_plan_import(second, path.parent)
    assert path.read_bytes() == before


def test_starter_has_canonical_channels_and_elapsed_utc_follow_up(tmp_path: Path) -> None:
    start = datetime(2030, 3, 9, 9, 30, tzinfo=timezone(timedelta(hours=-5)))
    source = starter_campaign_plan(
        name="  My release  ", platforms=["mastodon", "x"], start_at=start
    )
    assert source.name == "My release"
    assert source.required_platforms == ("x", "mastodon")
    assert source.items[0].intended_at == datetime(2030, 3, 9, 14, 30, tzinfo=timezone.utc)
    assert source.items[1].intended_at == source.items[0].intended_at + timedelta(hours=48)
    assert all(item.campaign.platforms == source.required_platforms for item in source.items)
    path = export_campaign_plan_import(source, tmp_path / "release")
    assert check_campaign_plan(build_campaign_plan(load_campaign_plan(path))).publishable


@pytest.mark.parametrize(
    "arguments, message",
    [
        ({"name": ""}, "name"),
        ({"name": "N" * 121}, "name"),
        ({"name": "bad\x1bname"}, "name"),
        ({"platforms": "x"}, "platforms"),
        ({"platforms": None}, "platforms"),
        ({"platforms": []}, "platforms"),
        ({"platforms": ["x"] * 6}, "platforms"),
        ({"platforms": ["x", "x"]}, "duplicate"),
        ({"platforms": ["other"]}, "platform"),
        ({"platforms": [None]}, "platform"),
        ({"start_at": "2030-01-01T00:00:00Z"}, "datetime"),
        ({"start_at": datetime(2030, 1, 1)}, "timezone"),
        ({"start_at": datetime.max.replace(tzinfo=timezone.utc)}, "48 hours"),
        ({"start_at": datetime.min.replace(tzinfo=timezone(timedelta(hours=1)))}, "48 hours"),
    ],
)
def test_starter_rejects_invalid_options(arguments: dict[str, Any], message: str) -> None:
    with pytest.raises(ConfigError, match=message):
        starter_campaign_plan(**arguments)


def test_cli_plan_init_selects_channels_and_never_overwrites(tmp_path: Path, capsys: Any) -> None:
    output = tmp_path / "release"
    arguments = [
        "plan",
        "init",
        str(output),
        "--name",
        "Example launch",
        "--platform",
        "x",
        "--platform",
        "bluesky",
        "--start-at",
        "2030-01-01T12:00:00+02:00",
        "--json",
    ]
    assert main(arguments) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["items"] == 2 and result["scheduled"] is True
    assert result["requiredPlatforms"] == ["x", "bluesky"]
    path = Path(result["path"])
    assert result["planId"] == build_campaign_plan(load_campaign_plan(path)).plan_id
    before = {p: p.read_bytes() for p in output.rglob("*.json")}
    assert main(arguments) == 1
    assert "overwrite" in capsys.readouterr().err
    assert all(p.read_bytes() == content for p, content in before.items())
    assert main(["plan", "init", str(tmp_path / "default")]) == 0
    assert "No intended times" in capsys.readouterr().out


@pytest.mark.parametrize(
    "start", ["2030-01-01", "2030-01-01T00:00:00-00:00", "nope", "9999-12-31T00:00:00Z"]
)
def test_cli_invalid_start_does_not_create_files(tmp_path: Path, capsys: Any, start: str) -> None:
    target = tmp_path / "no-output"
    assert main(["plan", "init", str(target), "--start-at", start, "--json"]) == 1
    assert not target.exists()
    assert capsys.readouterr().err


def test_cli_invalid_name_and_duplicate_channels_leave_no_output(
    tmp_path: Path, capsys: Any
) -> None:
    target = tmp_path / "no-output"
    for options in (["--name", ""], ["--platform", "x", "--platform", "x"]):
        assert main(["plan", "init", str(target), *options]) == 1
        assert not target.exists()
        assert capsys.readouterr().err


def test_evaluation_runner_works_outside_checkout_and_preserves_existing_output(
    tmp_path: Path,
) -> None:
    script = Path(__file__).resolve().parents[1] / "examples" / "evaluate_release.py"
    output = tmp_path / "evaluation-雪"
    arguments = [sys.executable, str(script), "--output", str(output)]
    result = subprocess.run(arguments, cwd=tmp_path, capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stderr
    summary = json.loads(result.stdout)
    assert summary["kind"] == "synthetic-offline-evaluation"
    assert summary["items"] == 2 and summary["records"] == 10
    assert summary["providerActions"] == 0
    assert summary["staleApprovalRejected"] is True
    assert summary["stage"] == "publication-complete"
    assert Path(summary["board"]).is_file()
    original = (output / "evaluation.json").read_bytes()
    repeated = subprocess.run(arguments, cwd=tmp_path, capture_output=True, text=True, timeout=30)
    assert repeated.returncode == 1
    assert "Evaluation failed" in repeated.stderr
    assert (output / "evaluation.json").read_bytes() == original
