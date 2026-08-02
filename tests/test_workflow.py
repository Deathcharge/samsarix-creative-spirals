from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from samsarix_creative_spirals import ConfigError, build_campaign, export_campaign, load_campaign


def _write_campaign(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data), encoding="utf-8")


def test_build_is_deterministic(campaign_data: dict[str, Any]) -> None:
    first = build_campaign(campaign_data)
    second = build_campaign(campaign_data)

    assert first == second
    assert first.campaign_id.startswith("scs_")
    assert len(first.source_hash) == 64


def test_load_reports_json_location(tmp_path: Path) -> None:
    config_path = tmp_path / "broken.json"
    config_path.write_text('{"schemaVersion":', encoding="utf-8")

    with pytest.raises(ConfigError, match=r"invalid campaign JSON at line 1, column"):
        load_campaign(config_path)


def test_load_rejects_duplicate_json_fields(tmp_path: Path) -> None:
    config_path = tmp_path / "duplicate.json"
    config_path.write_text(
        '{"schemaVersion":1,"name":"first","name":"second","body":"text","platforms":["x"]}',
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="duplicate JSON field: name"):
        load_campaign(config_path)


def test_load_rejects_excessive_json_nesting(tmp_path: Path) -> None:
    config_path = tmp_path / "nested.json"
    config_path.write_text("[" * 2_000 + "]" * 2_000, encoding="utf-8")

    with pytest.raises(ConfigError, match="nesting is too deep"):
        load_campaign(config_path)


def test_load_ignores_json_delimiters_inside_strings(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    config_path = tmp_path / "string-delimiters.json"
    campaign_data["body"] = ("[{" * 200) + '\\"quoted\\"' + ("]}" * 200)
    _write_campaign(config_path, campaign_data)

    assert load_campaign(config_path).body == campaign_data["body"]


def test_load_reports_missing_and_non_file_paths(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="cannot read campaign file"):
        load_campaign(tmp_path / "missing.json")

    with pytest.raises(ConfigError, match="must be a file"):
        load_campaign(tmp_path)


def test_load_rejects_non_utf8(tmp_path: Path) -> None:
    config_path = tmp_path / "binary.json"
    config_path.write_bytes(b"\xff\xfe\xfa")

    with pytest.raises(ConfigError, match="UTF-8"):
        load_campaign(config_path)


def test_load_rejects_oversized_input(tmp_path: Path) -> None:
    config_path = tmp_path / "large.json"
    config_path.write_bytes(b"x" * 1_000_001)

    with pytest.raises(ConfigError, match="exceeds"):
        load_campaign(config_path)


def test_export_writes_copy_ready_bundle(tmp_path: Path, campaign_data: dict[str, Any]) -> None:
    campaign_data["media"] = [{"path": "media/nonexistent.png", "altText": "Release dashboard"}]
    bundle = build_campaign(campaign_data)
    exported_at = datetime(2026, 7, 28, 12, 0, tzinfo=timezone.utc)

    destination = export_campaign(bundle, tmp_path / "outbox", exported_at=exported_at)

    assert destination.parent == (tmp_path / "outbox").resolve()
    assert ".." not in destination.name
    assert (destination / "x.md").read_text(encoding="utf-8").endswith("\n")
    manifest = json.loads((destination / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["campaignId"] == bundle.campaign_id
    assert manifest["exportedAt"] == "2026-07-28T12:00:00Z"
    assert manifest["media"] == [
        {
            "path": "media/nonexistent.png",
            "altText": "Release dashboard",
            "platforms": ["x", "linkedin", "discord"],
        }
    ]
    assert manifest["drafts"][0]["media"] == [
        {"path": "media/nonexistent.png", "altText": "Release dashboard"}
    ]
    assert not (destination / "media").exists()
    assert {item["file"] for item in manifest["drafts"]} == {
        "x.md",
        "linkedin.md",
        "discord.md",
    }


def test_export_refuses_existing_bundle_without_opt_in(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    bundle = build_campaign(campaign_data)
    export_campaign(bundle, tmp_path)

    with pytest.raises(FileExistsError, match="--overwrite"):
        export_campaign(bundle, tmp_path)

    destination = export_campaign(bundle, tmp_path, overwrite=True)
    assert (destination / "manifest.json").is_file()


def test_generated_bundle_name_prevents_traversal(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    campaign_data["name"] = "../../outside"
    bundle = build_campaign(campaign_data)

    destination = export_campaign(bundle, tmp_path)

    assert destination.parent == tmp_path.resolve()
    assert destination.name.startswith("outside-")


def test_generated_bundle_name_has_safe_fallback(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    campaign_data["name"] = "你好"
    bundle = build_campaign(campaign_data)

    destination = export_campaign(bundle, tmp_path)

    assert destination.name.startswith("campaign-")


def test_export_rejects_output_file(tmp_path: Path, campaign_data: dict[str, Any]) -> None:
    output = tmp_path / "not-a-directory"
    output.write_text("occupied", encoding="utf-8")

    with pytest.raises(FileExistsError):
        export_campaign(build_campaign(campaign_data), output)


def test_export_rejects_non_directory_bundle_path(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    bundle = build_campaign(campaign_data)
    target = tmp_path / f"release-note-{bundle.campaign_id}"
    target.write_text("occupied", encoding="utf-8")

    with pytest.raises(OSError, match="non-directory"):
        export_campaign(bundle, tmp_path, overwrite=True)


def test_export_rejects_dangling_symlink_bundle_path(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    bundle = build_campaign(campaign_data)
    target = tmp_path / f"release-note-{bundle.campaign_id}"
    try:
        target.symlink_to(tmp_path / "missing-target", target_is_directory=True)
    except OSError:
        pytest.skip("symbolic links are not available in this environment")

    with pytest.raises(OSError, match="non-directory"):
        export_campaign(bundle, tmp_path, overwrite=True)


def test_load_valid_campaign(tmp_path: Path, campaign_data: dict[str, Any]) -> None:
    path = tmp_path / "campaign.json"
    _write_campaign(path, campaign_data)

    assert load_campaign(path).name == campaign_data["name"]
