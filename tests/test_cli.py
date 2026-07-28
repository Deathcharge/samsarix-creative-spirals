from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from helix_creative_spirals.cli import main


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
    assert payload["campaignId"].startswith("csp_")
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
