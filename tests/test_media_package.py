from __future__ import annotations

import copy
import hashlib
import json
import struct
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from media_helpers import png_chunk as _png_chunk
from media_helpers import png_image as _png
from samsarix_creative_spirals import (
    ApprovalPolicy,
    CampaignPlanApprovalAssignment,
    CampaignPlanMedia,
    CampaignPlanMediaBinding,
    CollectedCampaignPlanMedia,
    ConfigError,
    build_campaign_plan,
    build_campaign_plan_readiness,
    collect_campaign_plan_media,
    create_campaign_plan_approval,
    create_campaign_plan_approval_set,
    export_campaign_plan_handoff,
    load_campaign_plan,
    load_campaign_plan_handoff,
    load_campaign_plan_media,
    load_media_package_schema,
    load_plan_approval_schema,
    load_readiness_schema,
    verify_campaign_plan_approval,
    verify_campaign_plan_handoff,
)
from samsarix_creative_spirals.media_package import inspect_static_image
from samsarix_creative_spirals.media_package import (
    campaign_plan_media_binding_issues,
    campaign_plan_media_identity_issues,
    validate_collected_campaign_plan_media,
)

APPROVED_AT = datetime(2026, 8, 3, 14, 15, tzinfo=timezone.utc)
GENERATED_AT = datetime(2026, 8, 4, 9, 30, tzinfo=timezone.utc)


def _jpeg(*, width: int = 3, height: int = 2) -> bytes:
    frame = bytes((8,)) + struct.pack(">HH", height, width) + bytes((1, 1, 0x11, 0))
    scan = bytes((1, 1, 0, 0, 63, 0))
    return (
        b"\xff\xd8"
        + b"\xff\xe0\x00\x02"
        + b"\xff\xc0"
        + struct.pack(">H", len(frame) + 2)
        + frame
        + b"\xff\xda"
        + struct.pack(">H", len(scan) + 2)
        + scan
        + b"\x00\xff\xd9"
    )


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _media_plan(
    root: Path,
    campaign_data: dict[str, Any],
    *,
    media_payload: bytes | None = None,
    items: int = 1,
) -> tuple[Any, Path, Path]:
    campaign = dict(campaign_data)
    campaign["media"] = [
        {
            "path": "media/launch.png",
            "altText": "Launch dashboard with approval status",
            "platforms": ["x", "linkedin"],
        }
    ]
    campaign_path = root / "campaigns" / "release.json"
    _write_json(campaign_path, campaign)
    media_path = campaign_path.parent / "media" / "launch.png"
    media_path.parent.mkdir()
    media_path.write_bytes(media_payload if media_payload is not None else _png())
    plan_path = root / "plan.json"
    _write_json(
        plan_path,
        {
            "schemaVersion": 1,
            "name": "Verified media release",
            "requiredPlatforms": ["x", "linkedin"],
            "items": [
                {
                    "campaign": "campaigns/release.json",
                    "intendedAt": f"2026-08-{10 + index:02d}T13:00:00Z",
                }
                for index in range(items)
            ],
        },
    )
    return build_campaign_plan(load_campaign_plan(plan_path)), plan_path, media_path


def test_collect_media_is_deterministic_content_addressed_and_schema_valid(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    bundle, plan_path, _ = _media_plan(tmp_path, campaign_data, items=2)

    first = collect_campaign_plan_media(bundle, plan_path.parent)
    second = collect_campaign_plan_media(bundle, plan_path.parent)
    raw = first.index.to_dict()

    assert first == second
    assert first.index.media_id == f"scm_{first.index.media_hash[:12]}"
    assert first.index.binding.asset_count == 2
    assert len(first.files) == 1
    assert first.index.total_bytes == len(_png())
    assert [asset.sequence for asset in first.index.assets] == [1, 2]
    asset = first.index.assets[0]
    assert asset.packet_path == f"media/{asset.sha256}.png"
    assert (asset.content_type, asset.width, asset.height) == ("image/png", 1, 1)
    assert CampaignPlanMedia.from_dict(raw) == first.index
    schema = load_media_package_schema()
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(raw)


def test_media_binding_makes_approval_sensitive_to_exact_image_bytes(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    bundle, plan_path, media_path = _media_plan(tmp_path, campaign_data)
    collected = collect_campaign_plan_media(bundle, plan_path.parent)
    approval = create_campaign_plan_approval(
        bundle,
        approved_by="Visual reviewer",
        approved_at=APPROVED_AT,
        media=collected.index,
    )

    assert verify_campaign_plan_approval(bundle, approval, media=collected.index).valid
    Draft202012Validator(load_plan_approval_schema()).validate(approval.to_dict())
    readiness = build_campaign_plan_readiness(
        bundle,
        approval=approval,
        media=collected.index,
        assessed_at=datetime(2026, 8, 5, 12, tzinfo=timezone.utc),
    )
    assert readiness.stage == "approved"
    Draft202012Validator(load_readiness_schema()).validate(readiness.to_dict())
    assert [issue.code for issue in verify_campaign_plan_approval(bundle, approval).issues] == [
        "media-missing"
    ]

    media_path.write_bytes(_png(red=99))
    changed = collect_campaign_plan_media(bundle, plan_path.parent)
    result = verify_campaign_plan_approval(bundle, approval, media=changed.index)

    assert result.valid is False
    assert [issue.code for issue in result.issues] == ["media-changed"]
    assert changed.index.media_hash != collected.index.media_hash


def test_export_and_verify_approval_bound_media_packet(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    bundle, plan_path, _ = _media_plan(tmp_path, campaign_data)
    media = collect_campaign_plan_media(bundle, plan_path.parent)
    approval = create_campaign_plan_approval(
        bundle,
        approved_by="Visual reviewer",
        approved_at=APPROVED_AT,
        media=media.index,
    )
    packet_path = export_campaign_plan_handoff(
        bundle,
        approval,
        tmp_path / "handoffs",
        generated_at=GENERATED_AT,
        media=media,
    )

    packet = load_campaign_plan_handoff(packet_path)
    result = verify_campaign_plan_handoff(bundle, packet)
    asset = media.index.assets[0]

    assert result.valid
    assert packet.media == media.index
    assert "media-index.json" in {artifact.path for artifact in packet.handoff.artifacts}
    assert (packet_path / asset.packet_path).read_bytes() == _png()
    assert packet.approval.media == media.index.binding

    packaged = packet_path / asset.packet_path
    changed = bytearray(packaged.read_bytes())
    changed[-10] ^= 1
    packaged.write_bytes(changed)
    invalid = verify_campaign_plan_handoff(bundle, load_campaign_plan_handoff(packet_path))
    assert invalid.valid is False
    assert any(
        issue.code == "media-checksum-mismatch" and issue.path == asset.packet_path
        for issue in invalid.issues
    )


def test_approval_quorum_preserves_exact_media_through_handoff(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    bundle, plan_path, _ = _media_plan(tmp_path, campaign_data)
    media = collect_campaign_plan_media(bundle, plan_path.parent)
    first = create_campaign_plan_approval(
        bundle,
        approved_by="Brand visual reviewer",
        approved_at=APPROVED_AT,
        media=media.index,
    )
    second = create_campaign_plan_approval(
        bundle,
        approved_by="Release visual reviewer",
        approved_at=APPROVED_AT.replace(minute=APPROVED_AT.minute + 5),
        media=media.index,
    )
    policy = ApprovalPolicy.from_dict(
        {
            "schemaVersion": 1,
            "name": "Visual release quorum",
            "minimumTotal": 2,
            "distinctReviewers": True,
            "requirements": [
                {"role": "brand", "minimum": 1},
                {"role": "release-owner", "minimum": 1},
            ],
        }
    )
    approval_set = create_campaign_plan_approval_set(
        bundle,
        policy,
        (
            CampaignPlanApprovalAssignment("brand", first),
            CampaignPlanApprovalAssignment("release-owner", second),
        ),
        media=media.index,
    )

    packet_path = export_campaign_plan_handoff(
        bundle,
        approval_set,
        tmp_path / "quorum-handoffs",
        generated_at=GENERATED_AT,
        media=media,
    )
    packet = load_campaign_plan_handoff(packet_path)
    result = verify_campaign_plan_handoff(bundle, packet)

    assert result.valid
    assert packet.approval == approval_set
    assert packet.media == media.index
    assert (packet_path / media.index.assets[0].packet_path).read_bytes() == _png()


def test_handoff_verifier_refuses_symbolic_link_media_directory(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    bundle, plan_path, _ = _media_plan(tmp_path, campaign_data)
    media = collect_campaign_plan_media(bundle, plan_path.parent)
    approval = create_campaign_plan_approval(
        bundle,
        approved_by="Visual reviewer",
        approved_at=APPROVED_AT,
        media=media.index,
    )
    packet_path = export_campaign_plan_handoff(
        bundle,
        approval,
        tmp_path / "handoffs",
        generated_at=GENERATED_AT,
        media=media,
    )
    media_root = packet_path / "media"
    external = tmp_path / "external"
    external.mkdir()
    for file_path in media_root.iterdir():
        (external / file_path.name).write_bytes(file_path.read_bytes())
        file_path.unlink()
    media_root.rmdir()
    try:
        media_root.symlink_to(external, target_is_directory=True)
    except OSError:
        pytest.skip("symbolic links are not available in this environment")

    result = verify_campaign_plan_handoff(bundle, load_campaign_plan_handoff(packet_path))

    assert result.valid is False
    assert any(
        issue.code == "artifact-type-invalid" and issue.path == media.index.assets[0].packet_path
        for issue in result.issues
    )


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        (b"not a png", "does not match its PNG suffix"),
        (_png(animated=True), "animated PNG"),
        (_png(width=7000, height=6000), "maximum is 36152319"),
    ],
)
def test_collect_rejects_invalid_or_out_of_contract_images(
    tmp_path: Path,
    campaign_data: dict[str, Any],
    payload: bytes,
    expected: str,
) -> None:
    bundle, plan_path, _ = _media_plan(tmp_path, campaign_data, media_payload=payload)

    with pytest.raises(ConfigError, match=expected):
        collect_campaign_plan_media(bundle, plan_path.parent)


def test_collect_rejects_missing_oversized_and_symbolic_link_media(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    bundle, plan_path, media_path = _media_plan(tmp_path, campaign_data)
    media_path.unlink()
    with pytest.raises(ConfigError, match="cannot read item 1 media"):
        collect_campaign_plan_media(bundle, plan_path.parent)

    media_path.write_bytes(b"0" * 2_000_001)
    with pytest.raises(ConfigError, match="between 1 and 2000000 bytes"):
        collect_campaign_plan_media(bundle, plan_path.parent)

    target = tmp_path / "target.png"
    target.write_bytes(_png())
    media_path.unlink()
    try:
        media_path.symlink_to(target)
    except OSError:
        pytest.skip("symbolic links are not available in this environment")
    with pytest.raises(ConfigError, match="traverses a symbolic link"):
        collect_campaign_plan_media(bundle, plan_path.parent)


def test_media_index_parser_and_in_memory_collection_reject_tampering(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    bundle, plan_path, _ = _media_plan(tmp_path, campaign_data)
    media = collect_campaign_plan_media(bundle, plan_path.parent)
    raw = media.index.to_dict()
    raw["assets"][0]["sha256"] = "f" * 64

    with pytest.raises(ConfigError, match="packetPath digest must match sha256"):
        CampaignPlanMedia.from_dict(raw)

    forged = replace(media, files=((media.files[0][0], b"changed"),))
    approval = create_campaign_plan_approval(
        bundle,
        approved_by="Reviewer",
        approved_at=APPROVED_AT,
        media=media.index,
    )
    with pytest.raises(ConfigError, match="does not match index"):
        export_campaign_plan_handoff(
            bundle,
            approval,
            tmp_path / "handoffs",
            generated_at=GENERATED_AT,
            media=forged,
        )

    duplicate = CollectedCampaignPlanMedia(
        index=media.index,
        files=(media.files[0], media.files[0]),
    )
    with pytest.raises(ConfigError, match="must not repeat"):
        export_campaign_plan_handoff(
            bundle,
            approval,
            tmp_path / "handoffs",
            generated_at=GENERATED_AT,
            media=duplicate,
        )


def test_media_hash_is_not_a_signature(tmp_path: Path, campaign_data: dict[str, Any]) -> None:
    bundle, plan_path, _ = _media_plan(tmp_path, campaign_data)
    media = collect_campaign_plan_media(bundle, plan_path.parent)

    assert hashlib.sha256(media.files[0][1]).hexdigest() == media.index.assets[0].sha256
    assert media.index.media_hash != media.index.assets[0].sha256


def test_static_jpeg_inspection_normalizes_suffix_and_dimensions() -> None:
    assert inspect_static_image(_jpeg(), suffix=".jpeg") == ("image/jpeg", 3, 2, "jpg")


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        (b"not-jpeg", "does not match"),
        (b"\xff\xd8\xff\xd9", "frame and scan"),
        (b"\xff\xd8\xff\xda\x00\x02\xff\xd9", "before image data"),
        (b"\xff\xd8x\xff\xd9", "marker stream"),
        (b"\xff\xd8\xff\xc0\x00\x01\xff\xd9", "marker length"),
        (_jpeg()[:-2], "EOI"),
    ],
)
def test_static_jpeg_inspection_rejects_malformed_payloads(payload: bytes, expected: str) -> None:
    with pytest.raises(ConfigError, match=expected):
        inspect_static_image(payload, suffix=".jpg")


def test_static_image_inspection_rejects_unknown_suffix() -> None:
    with pytest.raises(ConfigError, match="must use"):
        inspect_static_image(_png(), suffix=".gif")


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        (b"\x89PNG\r\n\x1a\n\x00", "truncated chunk"),
        (
            b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 100) + b"IHDR" + b"x" * 4,
            "truncated chunk payload",
        ),
        (
            b"\x89PNG\r\n\x1a\n" + _png_chunk(b"IDAT", b"x") + _png_chunk(b"IEND", b""),
            "must begin",
        ),
        (
            _png()[:-12]
            + _png_chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0))
            + _png_chunk(b"IEND", b""),
            "more than one IHDR",
        ),
        (_png() + b"trailing", "IEND must be empty"),
        (_png()[:-5] + b"bad!!", "chunk checksum"),
        (
            b"\x89PNG\r\n\x1a\n"
            + _png_chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0))
            + _png_chunk(b"IEND", b""),
            "must contain dimensions",
        ),
    ],
)
def test_static_png_inspection_rejects_malformed_structure(payload: bytes, expected: str) -> None:
    with pytest.raises(ConfigError, match=expected):
        inspect_static_image(payload, suffix=".png")


def test_media_index_parser_reports_root_and_asset_contract_failures(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    bundle, plan_path, _ = _media_plan(tmp_path, campaign_data)
    valid = collect_campaign_plan_media(bundle, plan_path.parent).index.to_dict()
    invalid_root = {
        "schemaVersion": False,
        "contract": "other",
        "mediaId": "bad",
        "mediaHash": "bad",
        "planId": "bad",
        "sourceHash": "bad",
        "totalBytes": False,
        "assets": "bad",
        "extra": True,
    }
    with pytest.raises(ConfigError) as caught:
        CampaignPlanMedia.from_dict(invalid_root)
    message = str(caught.value)
    assert "unknown media index field" in message
    assert "schemaVersion must be 1" in message
    assert "assets must be a non-empty array" in message

    invalid_asset = copy.deepcopy(valid)
    invalid_asset["assets"] = [
        {
            "sequence": False,
            "source": "../bad",
            "reference": "/bad.gif",
            "packetPath": "elsewhere",
            "contentType": "image/gif",
            "width": 100_000,
            "height": 100_000,
            "bytes": 0,
            "sha256": "BAD",
            "altText": "bad\ntext",
            "platforms": ["x", "x", "other"],
            "extra": True,
        }
    ]
    with pytest.raises(ConfigError) as caught:
        CampaignPlanMedia.from_dict(invalid_asset)
    message = str(caught.value)
    assert "unknown field" in message
    assert "portable relative path" in message
    assert "supported platforms" in message
    assert "totalBytes must equal" in message

    non_object_asset = copy.deepcopy(valid)
    non_object_asset["assets"] = [False]
    with pytest.raises(ConfigError, match=r"assets\[0\] must be an object"):
        CampaignPlanMedia.from_dict(non_object_asset)

    mismatched_suffix = copy.deepcopy(valid)
    mismatched_suffix["assets"][0]["contentType"] = "image/jpeg"
    mismatched_suffix["assets"][0]["platforms"] = []
    with pytest.raises(ConfigError) as caught:
        CampaignPlanMedia.from_dict(mismatched_suffix)
    assert "suffix must match" in str(caught.value)
    assert "platforms must be a non-empty array" in str(caught.value)


def test_media_index_rejects_duplicate_and_conflicting_asset_declarations(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    bundle, plan_path, _ = _media_plan(tmp_path, campaign_data)
    valid = collect_campaign_plan_media(bundle, plan_path.parent).index.to_dict()
    duplicate = copy.deepcopy(valid)
    duplicate["assets"].append(copy.deepcopy(duplicate["assets"][0]))
    duplicate["assets"][1]["bytes"] += 1

    with pytest.raises(ConfigError) as caught:
        CampaignPlanMedia.from_dict(duplicate)

    message = str(caught.value)
    assert "must not repeat a reference" in message
    assert "sharing packetPath" in message


def test_load_media_index_and_collection_edge_errors(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    bundle, plan_path, _ = _media_plan(tmp_path, campaign_data)
    media = collect_campaign_plan_media(bundle, plan_path.parent)
    index_path = tmp_path / "index.json"
    _write_json(index_path, media.index.to_dict())
    assert load_campaign_plan_media(index_path) == media.index

    with pytest.raises(ConfigError, match="plan_root"):
        collect_campaign_plan_media(bundle, tmp_path / "missing")

    without_media_data = dict(campaign_data)
    no_media_root = tmp_path / "no-media"
    _write_json(no_media_root / "campaign.json", without_media_data)
    _write_json(
        no_media_root / "plan.json",
        {
            "schemaVersion": 1,
            "name": "No media",
            "items": [{"campaign": "campaign.json"}],
        },
    )
    no_media = build_campaign_plan(load_campaign_plan(no_media_root / "plan.json"))
    with pytest.raises(ConfigError, match="no media references"):
        collect_campaign_plan_media(no_media, no_media_root)


def test_media_binding_parser_and_binding_issue_states() -> None:
    issues: list[str] = []
    assert CampaignPlanMediaBinding.from_dict(None, field="media", issues=issues) is None
    assert issues == ["media must be an object"]

    issues = []
    binding = CampaignPlanMediaBinding.from_dict(
        {
            "mediaId": "bad",
            "mediaHash": "bad",
            "assetCount": False,
            "totalBytes": 0,
            "extra": True,
        },
        field="media",
        issues=issues,
    )
    assert binding is not None
    assert len(issues) == 5
    assert campaign_plan_media_binding_issues(None, None) == ()
    introduced: Any = object()
    assert campaign_plan_media_binding_issues(None, introduced) == (
        ("media-introduced", "Exact media was supplied but is not bound by the approval."),
    )


def test_embedded_media_binding_schemas_stay_synchronized() -> None:
    assert (
        load_plan_approval_schema()["$defs"]["mediaBinding"]
        == load_readiness_schema()["$defs"]["mediaBinding"]
    )


def test_collected_media_validator_rejects_missing_extra_and_invalid_index(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    bundle, plan_path, _ = _media_plan(tmp_path, campaign_data)
    media = collect_campaign_plan_media(bundle, plan_path.parent)

    with pytest.raises(ConfigError, match="exactly cover"):
        validate_collected_campaign_plan_media(replace(media, files=()))
    with pytest.raises(ConfigError, match="exactly cover"):
        validate_collected_campaign_plan_media(
            replace(media, files=media.files + (("media/extra.png", _png()),))
        )
    forged_index = replace(media.index, media_hash="0" * 64)
    with pytest.raises(ConfigError, match="index is invalid"):
        validate_collected_campaign_plan_media(replace(media, index=forged_index))
    assert campaign_plan_media_identity_issues(bundle, forged_index)[0][0] == "media-invalid"


def test_approval_rejects_media_snapshot_from_another_plan(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    first, first_path, _ = _media_plan(tmp_path / "first", campaign_data)
    revised = dict(campaign_data)
    revised["body"] = "A different approved release."
    second, _, _ = _media_plan(tmp_path / "second", revised)
    foreign = collect_campaign_plan_media(first, first_path.parent).index

    with pytest.raises(ConfigError, match="different plan ID"):
        create_campaign_plan_approval(
            second,
            approved_by="Reviewer",
            approved_at=APPROVED_AT,
            media=foreign,
        )
