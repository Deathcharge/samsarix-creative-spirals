from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator, FormatChecker

from samsarix_creative_spirals import (
    CampaignPlanHandoff,
    ConfigError,
    build_campaign_plan,
    build_campaign_plan_handoff,
    create_campaign_plan_approval,
    export_campaign_plan_handoff,
    load_campaign_plan,
    load_campaign_plan_handoff,
    load_handoff_schema,
    verify_campaign_plan_handoff,
)

APPROVED_AT = datetime(2026, 8, 3, 14, 15, tzinfo=timezone.utc)
GENERATED_AT = datetime(2026, 8, 4, 9, 30, tzinfo=timezone.utc)


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _write_plan(root: Path, campaign_data: dict[str, Any]) -> Path:
    _write_json(root / "campaigns" / "release.json", campaign_data)
    path = root / "plan.json"
    _write_json(
        path,
        {
            "schemaVersion": 1,
            "name": "Approved release sequence",
            "requiredPlatforms": ["x", "linkedin", "discord"],
            "items": [
                {
                    "campaign": "campaigns/release.json",
                    "intendedAt": "2026-08-10T13:00:00Z",
                }
            ],
        },
    )
    return path


def _approved_bundle(root: Path, campaign_data: dict[str, Any]) -> tuple[Any, Any, Path]:
    plan_path = _write_plan(root, campaign_data)
    bundle = build_campaign_plan(load_campaign_plan(plan_path))
    approval = create_campaign_plan_approval(
        bundle,
        approved_by="Launch reviewer",
        approved_at=APPROVED_AT,
        note="Schedule, channels, and copy reviewed.",
    )
    return bundle, approval, plan_path


def _export_packet(root: Path, campaign_data: dict[str, Any]) -> tuple[Any, Any, Path, Path]:
    bundle, approval, plan_path = _approved_bundle(root, campaign_data)
    packet_path = export_campaign_plan_handoff(
        bundle,
        approval,
        root / "handoff-outbox",
        generated_at=GENERATED_AT,
    )
    return bundle, approval, plan_path, packet_path


def _issue_codes(result: Any) -> set[str]:
    return {issue.code for issue in result.issues}


def test_build_handoff_is_deterministic_and_schema_valid(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    bundle, approval, _ = _approved_bundle(tmp_path, campaign_data)

    first = build_campaign_plan_handoff(bundle, approval, generated_at=GENERATED_AT)
    second = build_campaign_plan_handoff(bundle, approval, generated_at=GENERATED_AT)

    assert first == second
    assert first.handoff_id == f"sch_{first.handoff_hash[:12]}"
    assert first.to_dict()["generatedAt"] == "2026-08-04T09:30:00Z"
    assert [artifact.path for artifact in first.artifacts] == [
        "adapter.json",
        "approval.json",
        "calendar.ics",
        "manifest.json",
        "csv/x.csv",
        "csv/linkedin.csv",
        "csv/discord.csv",
    ]
    Draft202012Validator(
        load_handoff_schema(),
        format_checker=FormatChecker(),
    ).validate(first.to_dict())
    assert CampaignPlanHandoff.from_dict(first.to_dict()) == first


def test_export_load_and_verify_complete_handoff_packet(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    bundle, approval, _, packet_path = _export_packet(tmp_path, campaign_data)

    packet = load_campaign_plan_handoff(packet_path)
    result = verify_campaign_plan_handoff(bundle, packet)
    files = sorted(
        path.relative_to(packet_path).as_posix()
        for path in packet_path.rglob("*")
        if path.is_file()
    )

    assert packet.approval == approval
    assert packet.handoff.handoff_id in packet_path.name
    assert result.valid is True
    assert result.to_dict()["issues"] == []
    assert files == [
        "adapter.json",
        "approval.json",
        "calendar.ics",
        "csv/discord.csv",
        "csv/linkedin.csv",
        "csv/x.csv",
        "handoff.json",
        "manifest.json",
    ]
    with pytest.raises(FileExistsError, match="already exists"):
        export_campaign_plan_handoff(
            bundle,
            approval,
            tmp_path / "handoff-outbox",
            generated_at=GENERATED_AT,
        )


def test_handoff_refuses_invalid_approval_and_invalid_generation_times(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    bundle, approval, plan_path = _approved_bundle(tmp_path, campaign_data)
    revised = dict(campaign_data)
    revised["body"] = "Changed after approval"
    _write_plan(tmp_path, revised)
    changed = build_campaign_plan(load_campaign_plan(plan_path))

    with pytest.raises(ConfigError, match="invalid plan approval"):
        export_campaign_plan_handoff(changed, approval, tmp_path / "invalid")
    assert not (tmp_path / "invalid").exists()

    with pytest.raises(ConfigError, match="timezone"):
        build_campaign_plan_handoff(
            bundle,
            approval,
            generated_at=datetime(2026, 8, 4, 9, 30),
        )
    with pytest.raises(ConfigError, match="approval approved_at"):
        build_campaign_plan_handoff(
            bundle,
            replace(approval, approved_at=datetime(2026, 8, 3, 14, 15)),
            generated_at=GENERATED_AT,
        )
    with pytest.raises(ConfigError, match="earlier than approved_at"):
        build_campaign_plan_handoff(
            bundle,
            approval,
            generated_at=datetime(2026, 8, 3, 14, 14, tzinfo=timezone.utc),
        )


def test_verify_detects_same_size_artifact_tampering(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    bundle, _, _, packet_path = _export_packet(tmp_path, campaign_data)
    adapter = packet_path / "adapter.json"
    original = adapter.read_bytes()
    changed = original.replace(b"{", b"[", 1)
    assert changed != original and len(changed) == len(original)
    adapter.write_bytes(changed)

    result = verify_campaign_plan_handoff(bundle, load_campaign_plan_handoff(packet_path))

    assert result.valid is False
    assert {"artifact-content-changed", "artifact-checksum-mismatch"} <= _issue_codes(result)


def test_verify_detects_missing_and_unexpected_artifacts(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    bundle, _, _, packet_path = _export_packet(tmp_path, campaign_data)
    (packet_path / "calendar.ics").unlink()
    (packet_path / "private.txt").write_text("unexpected", encoding="utf-8")
    (packet_path / "csv" / "other.csv").write_text("unexpected", encoding="utf-8")

    result = verify_campaign_plan_handoff(bundle, load_campaign_plan_handoff(packet_path))

    assert result.valid is False
    assert "artifact-missing" in _issue_codes(result)
    unexpected_paths = {
        issue.path for issue in result.issues if issue.code == "artifact-unexpected"
    }
    assert unexpected_paths == {"private.txt", "csv/other.csv"}


def test_verify_detects_manifest_metadata_and_producer_tampering(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    bundle, _, _, packet_path = _export_packet(tmp_path, campaign_data)
    handoff_path = packet_path / "handoff.json"
    handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
    handoff["producer"]["version"] = "0.7.0"
    handoff["artifacts"]["adapter.json"]["sha256"] = "f" * 64
    handoff_path.write_text(json.dumps(handoff), encoding="utf-8")

    result = verify_campaign_plan_handoff(bundle, load_campaign_plan_handoff(packet_path))

    assert result.valid is False
    assert {
        "producer-version-changed",
        "handoff-hash-invalid",
        "artifact-metadata-changed",
        "artifact-checksum-mismatch",
    } <= _issue_codes(result)


def test_verify_detects_handoff_file_changes_after_load(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    bundle, _, _, packet_path = _export_packet(tmp_path, campaign_data)
    packet = load_campaign_plan_handoff(packet_path)
    handoff_path = packet_path / "handoff.json"
    payload = handoff_path.read_bytes()
    changed = payload.replace(b"{", b"[", 1)
    assert changed != payload and len(changed) == len(payload)
    handoff_path.write_bytes(changed)

    result = verify_campaign_plan_handoff(bundle, packet)

    assert result.valid is False
    assert "handoff-file-changed" in _issue_codes(result)


def test_verify_detects_source_and_embedded_approval_changes(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    _, _, plan_path, packet_path = _export_packet(tmp_path, campaign_data)
    revised = dict(campaign_data)
    revised["body"] = "Changed after packet creation"
    _write_plan(tmp_path, revised)
    current = build_campaign_plan(load_campaign_plan(plan_path))

    result = verify_campaign_plan_handoff(current, load_campaign_plan_handoff(packet_path))

    assert result.valid is False
    assert {
        "approval-source-changed",
        "approval-plan-id-changed",
        "plan-id-changed",
        "source-changed",
        "handoff-hash-changed",
    } <= _issue_codes(result)


def test_handoff_parser_rejects_invalid_shape(tmp_path: Path) -> None:
    invalid = {
        "schemaVersion": False,
        "artifactType": "other",
        "handoffId": "bad",
        "handoffHash": "bad",
        "planId": "bad",
        "sourceHash": "bad",
        "approval": "elsewhere.json",
        "generatedAt": "yesterday",
        "producer": {"name": "other", "version": "latest", "extra": True},
        "artifacts": {},
        "extra": True,
    }

    with pytest.raises(ConfigError) as caught:
        CampaignPlanHandoff.from_dict(invalid)

    message = str(caught.value)
    assert "unknown handoff field" in message
    assert "schemaVersion must be 1" in message
    assert "artifactType must be plan-handoff" in message
    assert "handoffId must be" in message
    assert "producer has unknown field" in message
    assert "artifacts must contain between 5 and 9 files" in message


def test_handoff_parser_rejects_invalid_artifact_descriptors(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    bundle, approval, _ = _approved_bundle(tmp_path, campaign_data)
    valid = build_campaign_plan_handoff(bundle, approval, generated_at=GENERATED_AT).to_dict()
    variants: list[tuple[dict[str, Any], str]] = []

    artifacts_not_object = deepcopy(valid)
    artifacts_not_object["artifacts"] = []
    variants.append((artifacts_not_object, "artifacts must be an object"))

    unsupported = deepcopy(valid)
    unsupported["artifacts"]["csv/other.csv"] = {
        "bytes": 1,
        "sha256": "0" * 64,
    }
    variants.append((unsupported, "unsupported path"))

    descriptor_not_object = deepcopy(valid)
    descriptor_not_object["artifacts"]["adapter.json"] = []
    variants.append((descriptor_not_object, "adapter.json must be an object"))

    unknown_descriptor_field = deepcopy(valid)
    unknown_descriptor_field["artifacts"]["adapter.json"]["extra"] = True
    variants.append((unknown_descriptor_field, "unknown field"))

    invalid_size = deepcopy(valid)
    invalid_size["artifacts"]["adapter.json"]["bytes"] = False
    variants.append((invalid_size, "bytes must be between"))

    invalid_digest = deepcopy(valid)
    invalid_digest["artifacts"]["adapter.json"]["sha256"] = "A" * 64
    variants.append((invalid_digest, "sha256 must be a lowercase"))

    missing_base = deepcopy(valid)
    del missing_base["artifacts"]["manifest.json"]
    variants.append((missing_base, "missing required path"))

    for raw, expected in variants:
        with pytest.raises(ConfigError, match=expected):
            CampaignPlanHandoff.from_dict(raw)


def test_verify_detects_changed_artifact_declarations_and_generation_order(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    bundle, _, _, packet_path = _export_packet(tmp_path, campaign_data)
    handoff_path = packet_path / "handoff.json"
    handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
    del handoff["artifacts"]["csv/x.csv"]
    handoff["artifacts"]["csv/bluesky.csv"] = {
        "bytes": 1,
        "sha256": "0" * 64,
    }
    handoff["generatedAt"] = "2026-08-03T14:14:00Z"
    handoff_path.write_text(json.dumps(handoff), encoding="utf-8")

    result = verify_campaign_plan_handoff(bundle, load_campaign_plan_handoff(packet_path))

    assert {
        "handoff-before-approval",
        "artifact-declaration-missing",
        "artifact-declaration-unexpected",
    } <= _issue_codes(result)


def test_handoff_load_and_verify_reject_missing_or_invalid_file_types(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    bundle, _, _, packet_path = _export_packet(tmp_path, campaign_data)
    packet = load_campaign_plan_handoff(packet_path)
    adapter = packet_path / "adapter.json"
    adapter.unlink()
    adapter.mkdir()
    csv_root = packet_path / "csv"
    for artifact in csv_root.iterdir():
        artifact.unlink()
    csv_root.rmdir()
    csv_root.write_text("not a directory", encoding="utf-8")

    result = verify_campaign_plan_handoff(bundle, packet)

    assert "artifact-type-invalid" in _issue_codes(result)

    (packet_path / "handoff.json").unlink()
    with pytest.raises(ConfigError, match="handoff handoff.json must be a regular file"):
        load_campaign_plan_handoff(packet_path)


def test_handoff_rejects_file_output_root_and_symbolic_link_packet(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    bundle, approval, _ = _approved_bundle(tmp_path, campaign_data)
    output_file = tmp_path / "not-a-directory"
    output_file.write_text("keep", encoding="utf-8")
    with pytest.raises(OSError, match="not a directory"):
        export_campaign_plan_handoff(
            bundle,
            approval,
            output_file,
            generated_at=GENERATED_AT,
        )

    actual = tmp_path / "actual"
    actual.mkdir()
    linked = tmp_path / "linked"
    try:
        linked.symlink_to(actual, target_is_directory=True)
    except OSError:
        pytest.skip("symbolic links are not available in this environment")
    with pytest.raises(ConfigError, match="non-symbolic-link"):
        load_campaign_plan_handoff(linked)

    with pytest.raises(OSError, match="symbolic-link"):
        export_campaign_plan_handoff(
            bundle,
            approval,
            linked,
            generated_at=GENERATED_AT,
        )


def test_verify_rejects_symbolic_link_artifact(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    bundle, _, _, packet_path = _export_packet(tmp_path, campaign_data)
    calendar = packet_path / "calendar.ics"
    replacement = tmp_path / "replacement.ics"
    replacement.write_bytes(calendar.read_bytes())
    calendar.unlink()
    try:
        calendar.symlink_to(replacement)
    except OSError:
        pytest.skip("symbolic links are not available in this environment")

    result = verify_campaign_plan_handoff(bundle, load_campaign_plan_handoff(packet_path))

    assert result.valid is False
    assert any(
        issue.code == "artifact-missing" and issue.path == "calendar.ics" for issue in result.issues
    )
