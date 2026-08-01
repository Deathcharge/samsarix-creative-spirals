from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from samsarix_creative_spirals.cli import main


def _write_campaign(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data), encoding="utf-8")


def test_cli_core_journey(tmp_path: Path, capsys: Any, campaign_data: dict[str, Any]) -> None:
    config_path = tmp_path / "campaign.json"
    assert main(["init", str(config_path)]) == 0
    assert config_path.is_file()
    capsys.readouterr()

    assert main(["validate", str(config_path), "--json"]) == 0
    validation = json.loads(capsys.readouterr().out)
    assert validation["valid"] is True

    assert main(["preview", str(config_path)]) == 0
    assert "[x]" in capsys.readouterr().out

    output = tmp_path / "outbox"
    assert main(["export", str(config_path), "--output", str(output)]) == 0
    assert list(output.glob("*/manifest.json"))


def test_cli_json_preview(tmp_path: Path, capsys: Any, campaign_data: dict[str, Any]) -> None:
    path = tmp_path / "campaign.json"
    _write_campaign(path, campaign_data)

    assert main(["preview", str(path), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["campaignId"].startswith("scs_")
    assert len(payload["drafts"]) == 3


def test_cli_reports_validation_failure(
    tmp_path: Path, capsys: Any, campaign_data: dict[str, Any]
) -> None:
    campaign_data["platforms"] = ["unknown"]
    path = tmp_path / "campaign.json"
    _write_campaign(path, campaign_data)

    assert main(["validate", str(path)]) == 1
    assert "error:" in capsys.readouterr().err


def test_init_refuses_to_overwrite(tmp_path: Path, capsys: Any) -> None:
    path = tmp_path / "campaign.json"
    path.write_text("keep me", encoding="utf-8")

    assert main(["init", str(path)]) == 1
    assert path.read_text(encoding="utf-8") == "keep me"
    assert "refusing to overwrite" in capsys.readouterr().err


def test_cli_without_command_returns_usage_error(capsys: Any) -> None:
    assert main([]) == 2
    assert "usage:" in capsys.readouterr().err


def test_cli_prints_and_writes_schema(tmp_path: Path, capsys: Any) -> None:
    assert main(["schema"]) == 0
    schema = json.loads(capsys.readouterr().out)
    assert schema["title"] == "Samsarix Creative Spirals campaign"

    output = tmp_path / "schemas" / "campaign.schema.json"
    assert main(["schema", "--output", str(output)]) == 0
    capsys.readouterr()
    assert json.loads(output.read_text(encoding="utf-8"))["additionalProperties"] is False

    assert main(["schema", "--output", str(output)]) == 1
    assert "refusing to overwrite" in capsys.readouterr().err


def test_cli_check_supports_quality_gate_exit_codes(
    tmp_path: Path, capsys: Any, campaign_data: dict[str, Any]
) -> None:
    path = tmp_path / "campaign.json"
    _write_campaign(path, campaign_data)

    assert main(["check", str(path), "--json"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["publishable"] is True
    assert report["issues"]

    assert main(["check", str(path), "--warnings-as-errors"]) == 3
    assert "Quality check failed" in capsys.readouterr().out

    campaign_data["body"] = "long content " * 100
    _write_campaign(path, campaign_data)
    assert main(["check", str(path), "--json"]) == 3
    report = json.loads(capsys.readouterr().out)
    assert any(issue["code"] == "truncated" for issue in report["issues"])


def test_cli_plan_journey(tmp_path: Path, capsys: Any, campaign_data: dict[str, Any]) -> None:
    campaign_path = tmp_path / "campaign.json"
    plan_path = tmp_path / "plan.json"
    _write_campaign(campaign_path, campaign_data)
    plan_path.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "name": "Release sequence",
                "requiredPlatforms": ["x", "linkedin", "discord"],
                "items": [
                    {
                        "campaign": "campaign.json",
                        "intendedAt": "2026-08-10T13:00:00Z",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    assert main(["plan", "validate", str(plan_path), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["items"] == 1

    assert main(["plan", "preview", str(plan_path)]) == 0
    assert "Release sequence" in capsys.readouterr().out

    assert main(["plan", "check", str(plan_path), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["publishable"] is True

    output = tmp_path / "plan-outbox"
    assert main(["plan", "export", str(plan_path), "--output", str(output), "--json"]) == 0
    exported = Path(json.loads(capsys.readouterr().out)["path"])
    assert (exported / "calendar.ics").is_file()
    assert (exported / "csv" / "x.csv").is_file()


def test_cli_emits_plan_schema(capsys: Any) -> None:
    assert main(["schema", "--kind", "plan"]) == 0
    schema = json.loads(capsys.readouterr().out)
    assert schema["title"] == "Samsarix Creative Spirals campaign plan"
