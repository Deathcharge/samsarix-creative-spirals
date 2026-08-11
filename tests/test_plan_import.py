from __future__ import annotations

import csv
import io
import json
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Any, cast

import pytest
from jsonschema import Draft202012Validator

from samsarix_creative_spirals import (
    CampaignPlanImport,
    CampaignPlanImportCheck,
    ConfigError,
    ImportedCampaign,
    PLAN_IMPORT_FIELDS,
    PlanImportIssue,
    build_campaign_plan,
    export_campaign_plan_import,
    inspect_campaign_plan_csv,
    load_campaign_plan,
    load_plan_import_schema,
)
from samsarix_creative_spirals.cli import main


def _csv_text(rows: list[list[str]], *, bom: bool = False) -> str:
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(PLAN_IMPORT_FIELDS)
    writer.writerows(rows)
    return ("\ufeff" if bom else "") + stream.getvalue()


def _valid_rows() -> list[list[str]]:
    return [
        [
            "Launch announcement",
            "A reviewable launch",
            "First paragraph.\n\nSecond paragraph.",
            "https://example.com/launch",
            "Samsarix|contentops",
            "x|linkedin",
            "2026-08-10T09:00:00-04:00",
            "media/launch.png",
            "A campaign operations dashboard",
            "linkedin",
        ],
        [
            "Launch follow-up",
            "",
            "Follow up with the implementation details.",
            "",
            "Samsarix",
            "x|linkedin",
            "2026-08-12T13:00:00Z",
            "",
            "",
            "",
        ],
    ]


def test_inspect_export_and_reload_canonical_csv_package(tmp_path: Path) -> None:
    source = tmp_path / "launch.csv"
    source.write_text(_csv_text(_valid_rows(), bom=True), encoding="utf-8")

    check = inspect_campaign_plan_csv(
        source,
        name="Q3 launch sequence",
        required_platforms=("linkedin", "x"),
    )

    assert check.valid is True
    assert check.row_count == 2
    assert check.issues == ()
    assert check.imported is not None
    assert check.imported.required_platforms == ("x", "linkedin")
    assert check.imported.items[0].source == "campaigns/001-launch-announcement.json"
    assert check.imported.items[0].campaign.body.endswith("Second paragraph.")
    assert check.imported.items[0].campaign.media[0].platforms == ("linkedin",)
    assert check.imported.plan_dict()["items"][0]["intendedAt"] == "2026-08-10T13:00:00Z"
    Draft202012Validator(load_plan_import_schema()).validate(check.to_dict())

    plan_path = export_campaign_plan_import(check.imported, tmp_path / "imported")
    plan = load_campaign_plan(plan_path)
    bundle = build_campaign_plan(plan)

    assert plan_path == tmp_path / "imported" / "plan.json"
    assert len(bundle.items) == 2
    assert bundle.required_platforms == ("x", "linkedin")
    assert (
        json.loads(
            (tmp_path / "imported" / "campaigns" / "001-launch-announcement.json").read_text(
                encoding="utf-8"
            )
        )["media"][0]["path"]
        == "media/launch.png"
    )
    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        export_campaign_plan_import(check.imported, tmp_path / "imported")


def test_inspection_aggregates_row_diagnostics_without_writing(tmp_path: Path) -> None:
    source = tmp_path / "invalid.csv"
    rows = [
        [
            " ",
            "",
            " ",
            "ftp://example.com",
            "bad tag|",
            "x||unknown",
            "2026-08-10 09:00",
            "media/launch.gif",
            "",
            "linkedin",
        ],
        ["", "", "", "", "", "", "", "", "", ""],
        ["too", "few"],
    ]
    source.write_text(_csv_text(rows), encoding="utf-8")

    check = inspect_campaign_plan_csv(
        source,
        name=" ",
        required_platforms=("linkedin",),
    )

    assert check.valid is False
    assert check.imported is None
    assert check.row_count == 3
    codes = {issue.code for issue in check.issues}
    assert {
        "invalid-plan-name",
        "invalid-list",
        "invalid-timestamp",
        "incomplete-media",
        "invalid-campaign",
        "blank-row",
        "invalid-row-shape",
    } <= codes
    assert {issue.row for issue in check.issues if issue.row is not None} == {2, 3, 4}
    Draft202012Validator(load_plan_import_schema()).validate(check.to_dict())
    assert not (tmp_path / "output").exists()


@pytest.mark.parametrize(
    ("content", "code"),
    [
        (b"", "empty-file"),
        (b"\xff\xfe", "invalid-encoding"),
        (b"wrong,header\nvalue,row\n", "invalid-header"),
        (b'"unterminated', "invalid-csv"),
    ],
)
def test_inspection_rejects_invalid_file_envelopes(
    tmp_path: Path, content: bytes, code: str
) -> None:
    source = tmp_path / "source.csv"
    source.write_bytes(content)

    check = inspect_campaign_plan_csv(source, name="Import")

    assert check.valid is False
    assert check.issues[0].code == code


def test_inspection_enforces_file_and_row_bounds(tmp_path: Path) -> None:
    oversized = tmp_path / "oversized.csv"
    oversized.write_bytes(b"x" * 1_000_001)
    assert inspect_campaign_plan_csv(oversized, name="Import").issues[0].code == "file-too-large"

    rows = _valid_rows()[:1] * 101
    source = tmp_path / "too-many.csv"
    source.write_text(_csv_text(rows), encoding="utf-8")
    check = inspect_campaign_plan_csv(source, name="Import")
    assert check.row_count == 101
    assert any(issue.code == "too-many-rows" for issue in check.issues)

    header_only = tmp_path / "header-only.csv"
    header_only.write_text(_csv_text([]), encoding="utf-8")
    assert inspect_campaign_plan_csv(header_only, name="Import").issues[0].code == "missing-rows"


def test_inspection_covers_time_media_platform_and_metadata_diagnostics(tmp_path: Path) -> None:
    source = tmp_path / "diagnostics.csv"
    rows = [
        [
            "Missing fields",
            "",
            "Body",
            "",
            "",
            "",
            "2026-08-10T09:00:00-00:00",
            "",
            "Alt text without a path",
            "",
        ],
        [
            "Bad calendar date",
            "",
            "Body",
            "",
            "",
            "x",
            "2026-02-30T09:00:00Z",
            "",
            "",
            "",
        ],
    ]
    source.write_text(_csv_text(rows), encoding="utf-8")

    check = inspect_campaign_plan_csv(
        source,
        name="x" * 121 + "\n",
        required_platforms=cast(Any, ("x", "x", "unknown", object(), "linkedin", "bluesky")),
    )

    codes = {issue.code for issue in check.issues}
    assert {
        "invalid-plan-name",
        "too-many-required-platforms",
        "duplicate-required-platform",
        "invalid-required-platform",
        "missing-field",
        "unknown-offset",
        "incomplete-media",
        "invalid-timestamp",
        "missing-required-platform",
    } <= codes

    with pytest.raises(ConfigError, match="control characters"):
        PlanImportIssue("bad-message", "line one\nline two")


def test_export_cleans_private_stage_when_authoritative_reload_fails(
    tmp_path: Path, monkeypatch: Any
) -> None:
    source = tmp_path / "launch.csv"
    source.write_text(_csv_text(_valid_rows()), encoding="utf-8")
    check = inspect_campaign_plan_csv(source, name="Launch")
    assert check.imported is not None

    def fail_reload(path: Path) -> None:
        raise ConfigError(f"forced staged reload failure: {path.name}")

    monkeypatch.setattr("samsarix_creative_spirals.plan_import.load_campaign_plan", fail_reload)
    output = tmp_path / "output"
    with pytest.raises(ConfigError, match="forced staged reload failure"):
        export_campaign_plan_import(check.imported, output)

    assert not output.exists()
    assert not list(tmp_path.glob(".output.*.tmp"))

    class EmptyPlan:
        items: tuple[()] = ()

    monkeypatch.setattr(
        "samsarix_creative_spirals.plan_import.load_campaign_plan",
        lambda path: cast(Any, EmptyPlan()),
    )
    with pytest.raises(OSError, match="unexpected item count"):
        export_campaign_plan_import(check.imported, output)
    assert not output.exists()
    assert not list(tmp_path.glob(".output.*.tmp"))


def test_cli_imports_valid_csv_and_emits_json_diagnostics(tmp_path: Path, capsys: Any) -> None:
    source = tmp_path / "launch.csv"
    source.write_text(_csv_text(_valid_rows()), encoding="utf-8")
    output = tmp_path / "source-package"

    assert (
        main(
            [
                "plan",
                "import",
                str(source),
                "--name",
                "Launch sequence",
                "--required-platform",
                "x",
                "--output",
                str(output),
                "--json",
            ]
        )
        == 0
    )
    result = json.loads(capsys.readouterr().out)
    assert result["check"]["valid"] is True
    assert result["check"]["rowCount"] == 2
    assert result["planId"].startswith("scp_")
    assert Path(result["path"]) == output / "plan.json"

    invalid = tmp_path / "invalid.csv"
    invalid.write_text(_csv_text([["short"]]), encoding="utf-8")
    invalid_output = tmp_path / "invalid-output"
    assert (
        main(
            [
                "plan",
                "import",
                str(invalid),
                "--name",
                "Invalid",
                "--output",
                str(invalid_output),
                "--json",
            ]
        )
        == 1
    )
    diagnostic = json.loads(capsys.readouterr().out)
    assert diagnostic["valid"] is False
    assert diagnostic["issues"][0]["row"] == 2
    assert not invalid_output.exists()


def test_cli_emits_plan_import_schema(capsys: Any) -> None:
    assert main(["schema", "--kind", "plan-import"]) == 0
    schema = json.loads(capsys.readouterr().out)
    assert schema["properties"]["artifactType"]["const"] == "plan-import-check"


def test_public_import_values_enforce_runtime_invariants(tmp_path: Path) -> None:
    source = tmp_path / "launch.csv"
    source.write_text(_csv_text(_valid_rows()), encoding="utf-8")
    valid_check = inspect_campaign_plan_csv(source, name="Launch", required_platforms=("x",))
    assert valid_check.imported is not None
    imported = valid_check.imported
    item = imported.items[0]

    with pytest.raises(ConfigError) as issue_error:
        PlanImportIssue("Bad Code", "", row=0, field="")
    assert "code" in str(issue_error.value)
    assert "message" in str(issue_error.value)
    assert "row" in str(issue_error.value)
    assert "field" in str(issue_error.value)

    with pytest.raises(ConfigError) as item_error:
        ImportedCampaign(
            sequence=0,
            source="../campaign.json",
            campaign=cast(Any, object()),
            intended_at=datetime(2026, 8, 10, 9, 0),
        )
    assert "sequence" in str(item_error.value)
    assert "source" in str(item_error.value)
    assert "campaign" in str(item_error.value)
    assert "timezone" in str(item_error.value)

    with pytest.raises(ConfigError) as package_error:
        CampaignPlanImport(
            name=" ",
            required_platforms=cast(Any, ("linkedin", "x", "x")),
            items=cast(Any, None),
        )
    assert "name" in str(package_error.value)
    assert "canonical platform order" in str(package_error.value)
    assert "items" in str(package_error.value)

    with pytest.raises(ConfigError, match="contiguous"):
        CampaignPlanImport(
            name="Launch",
            required_platforms=(),
            items=(replace(item, sequence=2),),
        )
    with pytest.raises(ConfigError, match="does not request required platform"):
        CampaignPlanImport(
            name="Launch",
            required_platforms=("discord",),
            items=(item,),
        )

    invalid_issue = PlanImportIssue("invalid-file", "Invalid import input")
    with pytest.raises(ConfigError) as check_error:
        CampaignPlanImportCheck(
            row_count=-1,
            issues=(invalid_issue,),
            imported=imported,
        )
    assert "row_count" in str(check_error.value)
    assert "invalid check" in str(check_error.value)
    with pytest.raises(ConfigError, match="valid check"):
        CampaignPlanImportCheck(row_count=0, issues=())

    invalid_required = inspect_campaign_plan_csv(
        source,
        name=cast(Any, None),
        required_platforms=cast(Any, None),
    )
    assert invalid_required.valid is False
    assert {issue.code for issue in invalid_required.issues} == {
        "invalid-plan-name",
        "invalid-required-platform",
    }
