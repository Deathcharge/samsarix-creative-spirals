from __future__ import annotations

import json
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

import pytest
from jsonschema import Draft202012Validator, FormatChecker

from samsarix_creative_spirals import (
    CampaignPlanPublication,
    ConfigError,
    build_campaign_plan,
    create_campaign_plan_approval,
    export_campaign_plan_handoff,
    export_campaign_plan_publication,
    initialize_campaign_plan_publication,
    load_campaign_plan,
    load_campaign_plan_handoff,
    load_campaign_plan_publication,
    load_publication_schema,
    record_campaign_plan_publication,
    verify_campaign_plan_publication,
)

APPROVED_AT = datetime(2026, 8, 3, 14, tzinfo=timezone.utc)
HANDOFF_AT = datetime(2026, 8, 4, 9, tzinfo=timezone.utc)
CREATED_AT = datetime(2026, 8, 4, 10, tzinfo=timezone.utc)
ASSESSED_AT = datetime(2026, 8, 5, 12, tzinfo=timezone.utc)


def _record(
    bundle: Any, packet: Any, publication: CampaignPlanPublication, **changes: Any
) -> CampaignPlanPublication:
    arguments: dict[str, Any] = {
        "sequence": 1,
        "platform": "x",
        "status": "published",
        "recorded_by": "Release operator",
        "occurred_at": datetime(2026, 8, 4, 11, tzinfo=timezone.utc),
        "url": "https://social.example/samsarix/123",
        "assessed_at": ASSESSED_AT,
    }
    arguments.update(changes)
    return record_campaign_plan_publication(bundle, packet, publication, **arguments)


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _workflow(root: Path, campaign_data: dict[str, Any]) -> tuple[Any, Any, Path]:
    campaign = dict(campaign_data)
    campaign["platforms"] = ["x", "linkedin"]
    _write_json(root / "campaign.json", campaign)
    plan_path = root / "plan.json"
    _write_json(
        plan_path,
        {
            "schemaVersion": 1,
            "name": "Publication workflow",
            "requiredPlatforms": ["x", "linkedin"],
            "items": [
                {
                    "campaign": "campaign.json",
                    "intendedAt": "2026-08-04T11:00:00Z",
                }
            ],
        },
    )
    bundle = build_campaign_plan(load_campaign_plan(plan_path))
    approval = create_campaign_plan_approval(
        bundle, approved_by="Release reviewer", approved_at=APPROVED_AT
    )
    packet_path = export_campaign_plan_handoff(
        bundle, approval, root / "handoffs", generated_at=HANDOFF_AT
    )
    return bundle, load_campaign_plan_handoff(packet_path), plan_path


def test_record_outcomes_preserves_sources_and_completes_the_journey(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    bundle, packet, _ = _workflow(tmp_path, campaign_data)
    original = initialize_campaign_plan_publication(bundle, packet, created_at=CREATED_AT)
    before = original.to_dict()
    first = _record(bundle, packet, original)
    assert original.to_dict() == before
    assert first.publication_id != original.publication_id
    assert first.records[1] == original.records[1]
    assert first.source_hash == original.source_hash
    assert first.handoff_hash == original.handoff_hash
    assert first.created_at == original.created_at
    assert _record(bundle, packet, first) == first
    complete = _record(
        bundle, packet, first, platform="linkedin", status="skipped", url=None, note="Not needed."
    )
    assert verify_campaign_plan_publication(
        bundle, packet, complete, assessed_at=ASSESSED_AT
    ).complete
    Draft202012Validator(load_publication_schema(), format_checker=FormatChecker()).validate(
        complete.to_dict()
    )
    path = export_campaign_plan_publication(complete, tmp_path / "complete.json")
    assert load_campaign_plan_publication(path) == complete
    with pytest.raises(ConfigError, match="overwrite"):
        export_campaign_plan_publication(first, path)
    assert load_campaign_plan_publication(path) == complete


def test_failed_attempt_can_be_retried_without_inheriting_old_metadata(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    bundle, packet, _ = _workflow(tmp_path, campaign_data)
    original = initialize_campaign_plan_publication(bundle, packet, created_at=CREATED_AT)
    failed = _record(
        bundle, packet, original, status="failed", url=None, note="Service rejected it."
    )
    check = verify_campaign_plan_publication(bundle, packet, failed, assessed_at=ASSESSED_AT)
    assert check.current and not check.complete
    retried = _record(bundle, packet, failed)
    assert failed.records[0].status == "failed"
    assert retried.records[0].status == "published"
    assert retried.records[0].note is None


def test_record_preserves_unselected_direct_values_and_normalizes_only_the_target(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    bundle, packet, _ = _workflow(tmp_path, campaign_data)
    original = _completed(
        initialize_campaign_plan_publication(bundle, packet, created_at=CREATED_AT)
    )
    original = replace(
        original,
        records=(original.records[0], replace(original.records[1], note="  Kept as given  ")),
    )
    changed = _record(bundle, packet, original, replace_outcome=True, recorded_by=" New operator ")
    assert changed.records[0].recorded_by == "New operator"
    assert changed.records[1] is original.records[1]
    assert _record(bundle, packet, changed, recorded_by=" New operator ") is changed


@pytest.mark.parametrize("status", ["published", "skipped"])
def test_terminal_correction_requires_explicit_replacement(
    tmp_path: Path, campaign_data: dict[str, Any], status: str
) -> None:
    bundle, packet, _ = _workflow(tmp_path, campaign_data)
    original = initialize_campaign_plan_publication(bundle, packet, created_at=CREATED_AT)
    first = _record(
        bundle,
        packet,
        original,
        status=status,
        url="https://example.com/post" if status == "published" else None,
        note="Intentional omission" if status == "skipped" else None,
    )
    with pytest.raises(ConfigError, match="replace_outcome"):
        _record(bundle, packet, first, status="failed", url=None, note="Correcting the outcome.")
    corrected = _record(
        bundle,
        packet,
        first,
        status="failed",
        url=None,
        note="Correcting the outcome.",
        replace_outcome=True,
    )
    assert corrected.records[0].url is None
    assert corrected.records[0].status == "failed"


@pytest.mark.parametrize(
    "changes, message",
    [
        ({"sequence": True}, "sequence"),
        ({"sequence": 0}, "sequence"),
        ({"sequence": 101}, "sequence"),
        ({"sequence": 2}, "no publication record"),
        ({"platform": "discord"}, "no publication record"),
        ({"platform": []}, "platform"),
        ({"status": "pending"}, "status"),
        ({"status": []}, "status"),
        ({"replace_outcome": "yes"}, "boolean"),
        ({"recorded_by": ""}, "recordedBy"),
        ({"recorded_by": "bad\x1blabel"}, "recordedBy"),
        ({"url": None}, "url"),
        ({"url": "https://name:secret@example.com/post"}, "credentials"),
        ({"status": "failed", "url": None}, "note"),
        ({"status": "skipped", "note": "Skip it"}, "url"),
        ({"note": "n" * 501}, "note"),
        ({"occurred_at": datetime(2026, 8, 4)}, "timezone"),
        ({"occurred_at": "2026-08-04T11:00:00Z"}, "datetime"),
        ({"assessed_at": datetime(2026, 8, 5)}, "timezone"),
        ({"assessed_at": "2026-08-05T12:00:00Z"}, "datetime"),
        ({"occurred_at": APPROVED_AT}, "outcome-before-handoff"),
        ({"occurred_at": datetime(2027, 1, 1, tzinfo=timezone.utc)}, "outcome-in-future"),
    ],
)
def test_record_rejects_invalid_input_without_mutating_ledger(
    tmp_path: Path, campaign_data: dict[str, Any], changes: dict[str, Any], message: str
) -> None:
    bundle, packet, _ = _workflow(tmp_path, campaign_data)
    original = initialize_campaign_plan_publication(bundle, packet, created_at=CREATED_AT)
    before = original.to_dict()
    with pytest.raises(ConfigError, match=message):
        _record(bundle, packet, original, **changes)
    assert original.to_dict() == before


def test_record_rejects_backdated_retry_and_stale_or_malformed_evidence(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    bundle, packet, _ = _workflow(tmp_path, campaign_data)
    original = initialize_campaign_plan_publication(bundle, packet, created_at=CREATED_AT)
    failed = _record(bundle, packet, original, status="failed", url=None, note="Unavailable")
    with pytest.raises(ConfigError, match="previous recorded outcome"):
        _record(bundle, packet, failed, occurred_at=CREATED_AT)
    for invalid in (
        replace(original, source_hash="a" * 64),
        replace(original, records=original.records[:1]),
        replace(original, records=(replace(original.records[0], status="published"),)),
    ):
        with pytest.raises(ConfigError, match="non-current publication ledger"):
            _record(bundle, packet, invalid)
    (packet.root / "calendar.ics").write_text("tampered", encoding="utf-8")
    with pytest.raises(ConfigError, match="non-current publication ledger"):
        _record(bundle, packet, original)


def test_cli_record_creates_new_snapshot_and_rejects_overwrite_or_stale_evidence(
    tmp_path: Path, campaign_data: dict[str, Any], capsys: Any
) -> None:
    from samsarix_creative_spirals.cli import main

    bundle, packet, plan_path = _workflow(tmp_path, campaign_data)
    original = initialize_campaign_plan_publication(bundle, packet, created_at=CREATED_AT)
    path = export_campaign_plan_publication(original, tmp_path / "pending.json")
    output = tmp_path / "published.json"
    arguments = [
        "plan",
        "publication",
        "record",
        str(plan_path),
        str(packet.root),
        str(path),
        "--item",
        "1",
        "--platform",
        "x",
        "--status",
        "published",
        "--by",
        "Operator",
        "--at",
        "2026-08-04T11:00:00Z",
        "--url",
        "https://social.example/post/1",
        "--assessed-at",
        "2026-08-05T12:00:00Z",
        "--output",
        str(output),
    ]
    assert main(arguments + ["--json"]) == 0
    response = json.loads(capsys.readouterr().out)
    assert response["previousPublicationId"] == original.publication_id
    assert response["publication"]["records"][0]["status"] == "published"
    assert response["publication"]["records"][1]["status"] == "pending"
    assert load_campaign_plan_publication(path) == original
    written = output.read_bytes()
    assert main(arguments) == 1
    assert "overwrite" in capsys.readouterr().err
    assert output.read_bytes() == written
    arguments[-1] = str(tmp_path / "second.json")
    assert main(arguments) == 0
    assert "not platform-verified proof" in capsys.readouterr().out
    arguments[-1] = str(tmp_path / "should-not-exist.json")
    arguments[arguments.index("--item") + 1] = "2"
    assert main(arguments) == 1
    assert not Path(arguments[-1]).exists()
    assert "no publication record" in capsys.readouterr().err
    arguments[arguments.index("--item") + 1] = "1"
    arguments[arguments.index("--at") + 1] = "not-a-date"
    assert main(arguments) == 1
    assert "--at" in capsys.readouterr().err
    assert not Path(arguments[-1]).exists()
    arguments[arguments.index("--at") + 1] = "2026-08-04T11:00:00Z"
    arguments[arguments.index("--assessed-at") + 1] = "2026-08-05"
    assert main(arguments) == 1
    assert "--assessed-at" in capsys.readouterr().err
    assert not Path(arguments[-1]).exists()
    arguments[arguments.index("--assessed-at") + 1] = "2026-08-05T12:00:00Z"
    (packet.root / "calendar.ics").write_text("tampered", encoding="utf-8")
    assert main(arguments) == 1
    assert not Path(arguments[-1]).exists()
    assert "non-current" in capsys.readouterr().err


def _completed(publication: CampaignPlanPublication) -> CampaignPlanPublication:
    return replace(
        publication,
        records=(
            replace(
                publication.records[0],
                status="published",
                recorded_by="Publisher A",
                occurred_at=datetime(2026, 8, 4, 11, tzinfo=timezone.utc),
                url="https://social.example/@samsarix/123",
            ),
            replace(
                publication.records[1],
                status="skipped",
                recorded_by="Publisher A",
                occurred_at=datetime(2026, 8, 4, 11, 5, tzinfo=timezone.utc),
                note="Channel intentionally omitted for this release.",
            ),
        ),
    )


def test_initialize_publication_is_deterministic_schema_valid_and_pending(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    bundle, packet, _ = _workflow(tmp_path, campaign_data)

    first = initialize_campaign_plan_publication(bundle, packet, created_at=CREATED_AT)
    second = initialize_campaign_plan_publication(bundle, packet, created_at=CREATED_AT)
    check = verify_campaign_plan_publication(bundle, packet, first, assessed_at=ASSESSED_AT)

    assert first == second
    assert first.publication_id == f"scpub_{first.publication_hash[:12]}"
    assert [(record.sequence, record.platform) for record in first.records] == [
        (1, "x"),
        (1, "linkedin"),
    ]
    assert check.current is True and check.complete is False
    assert dict(check.counts) == {
        "records": 2,
        "pending": 2,
        "published": 0,
        "failed": 0,
        "skipped": 0,
    }
    assert {issue.code for issue in check.issues} == {"publication-pending"}
    Draft202012Validator(load_publication_schema(), format_checker=FormatChecker()).validate(
        first.to_dict()
    )
    assert CampaignPlanPublication.from_dict(first.to_dict()) == first


def test_completed_publication_accepts_published_and_skipped_outcomes(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    bundle, packet, _ = _workflow(tmp_path, campaign_data)
    publication = _completed(
        initialize_campaign_plan_publication(bundle, packet, created_at=CREATED_AT)
    )

    check = verify_campaign_plan_publication(bundle, packet, publication, assessed_at=ASSESSED_AT)

    assert check.current is True and check.complete is True
    assert check.issues == ()
    assert dict(check.counts)["published"] == 1
    assert dict(check.counts)["skipped"] == 1
    Draft202012Validator(load_publication_schema(), format_checker=FormatChecker()).validate(
        publication.to_dict()
    )


def test_export_and_load_are_bounded_and_exclusive(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    bundle, packet, _ = _workflow(tmp_path, campaign_data)
    publication = initialize_campaign_plan_publication(bundle, packet, created_at=CREATED_AT)
    output = tmp_path / "records" / "publication.json"

    assert export_campaign_plan_publication(publication, output) == output
    assert load_campaign_plan_publication(output) == publication
    with pytest.raises(ConfigError, match="refusing to overwrite"):
        export_campaign_plan_publication(publication, output)


def test_publication_parser_rejects_invalid_outcome_contracts(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    bundle, packet, _ = _workflow(tmp_path, campaign_data)
    raw = initialize_campaign_plan_publication(bundle, packet, created_at=CREATED_AT).to_dict()
    raw["records"][0].update(
        {
            "status": "published",
            "recordedBy": "Publisher",
            "occurredAt": "2026-08-04T11:00:00Z",
            "url": "https://person:secret@example.com/post",
        }
    )
    raw["records"][1].update(
        {
            "status": "failed",
            "recordedBy": "Publisher",
            "occurredAt": "2026-08-04T11:00:00Z",
        }
    )

    with pytest.raises(ConfigError) as caught:
        CampaignPlanPublication.from_dict(raw)

    assert "must not contain credentials" in str(caught.value)
    assert "note is required for failed" in str(caught.value)


def test_publication_parser_rejects_duplicate_records_and_pending_outcomes(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    bundle, packet, _ = _workflow(tmp_path, campaign_data)
    raw = initialize_campaign_plan_publication(bundle, packet, created_at=CREATED_AT).to_dict()
    raw["records"][0]["note"] = "Not allowed yet"
    raw["records"][1] = dict(raw["records"][0])

    with pytest.raises(ConfigError) as caught:
        CampaignPlanPublication.from_dict(raw)

    assert "pending records must not contain outcome fields" in str(caught.value)

    duplicate = initialize_campaign_plan_publication(
        bundle, packet, created_at=CREATED_AT
    ).to_dict()
    duplicate["records"][1] = dict(duplicate["records"][0])
    duplicate["extra"] = True
    with pytest.raises(ConfigError) as duplicate_error:
        CampaignPlanPublication.from_dict(duplicate)
    assert "unknown publication field" in str(duplicate_error.value)
    assert "duplicates item 1 x" in str(duplicate_error.value)


def test_publication_parser_rejects_non_string_status_without_crashing(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    bundle, packet, _ = _workflow(tmp_path, campaign_data)
    raw = initialize_campaign_plan_publication(bundle, packet, created_at=CREATED_AT).to_dict()
    raw["records"][0]["status"] = {"unexpected": True}

    with pytest.raises(ConfigError, match="status must be"):
        CampaignPlanPublication.from_dict(raw)


def test_publication_parser_rejects_bounded_urls_and_invalid_record_containers(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    bundle, packet, _ = _workflow(tmp_path, campaign_data)

    skipped_url = initialize_campaign_plan_publication(
        bundle, packet, created_at=CREATED_AT
    ).to_dict()
    skipped_url["records"][0].update(
        {
            "status": "skipped",
            "recordedBy": "Publisher",
            "occurredAt": "2026-08-04T11:00:00Z",
            "note": "Deferred.",
            "url": "https://social.example/posts/1",
        }
    )
    with pytest.raises(ConfigError, match="url is only allowed for published records"):
        CampaignPlanPublication.from_dict(skipped_url)

    overlong_url = initialize_campaign_plan_publication(
        bundle, packet, created_at=CREATED_AT
    ).to_dict()
    overlong_url["records"][0].update(
        {
            "status": "published",
            "recordedBy": "Publisher",
            "occurredAt": "2026-08-04T11:00:00Z",
            "url": "https://social.example/" + "a" * 2_000,
        }
    )
    with pytest.raises(ConfigError, match="at most 2000 characters"):
        CampaignPlanPublication.from_dict(overlong_url)

    whitespace_url = initialize_campaign_plan_publication(
        bundle, packet, created_at=CREATED_AT
    ).to_dict()
    whitespace_url["records"][0].update(
        {
            "status": "published",
            "recordedBy": "Publisher",
            "occurredAt": "2026-08-04T11:00:00Z",
            "url": "https://social.example/posts/has space",
        }
    )
    with pytest.raises(ConfigError, match="whitespace or control characters"):
        CampaignPlanPublication.from_dict(whitespace_url)

    control_url = initialize_campaign_plan_publication(
        bundle, packet, created_at=CREATED_AT
    ).to_dict()
    control_url["records"][0].update(
        {
            "status": "published",
            "recordedBy": "Publisher",
            "occurredAt": "2026-08-04T11:00:00Z",
            "url": "https://social.example/posts/has\u0007control",
        }
    )
    with pytest.raises(ConfigError, match="whitespace or control characters"):
        CampaignPlanPublication.from_dict(control_url)

    not_an_array = initialize_campaign_plan_publication(
        bundle, packet, created_at=CREATED_AT
    ).to_dict()
    not_an_array["records"] = {"unexpected": True}
    with pytest.raises(ConfigError, match="records must be an array"):
        CampaignPlanPublication.from_dict(not_an_array)

    non_object = initialize_campaign_plan_publication(
        bundle, packet, created_at=CREATED_AT
    ).to_dict()
    non_object["records"] = ["not-an-object"]
    with pytest.raises(ConfigError, match=r"records\[0\] must be an object"):
        CampaignPlanPublication.from_dict(non_object)


def test_verify_detects_stale_bindings_matrix_order_and_chronology(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    bundle, packet, _ = _workflow(tmp_path, campaign_data)
    original = _completed(
        initialize_campaign_plan_publication(bundle, packet, created_at=CREATED_AT)
    )
    changed = replace(
        original,
        source_hash="0" * 64,
        handoff_hash="f" * 64,
        created_at=datetime(2026, 8, 6, tzinfo=timezone.utc),
        records=(
            replace(
                original.records[1],
                occurred_at=datetime(2026, 8, 3, tzinfo=timezone.utc),
            ),
            original.records[0],
        ),
    )

    check = verify_campaign_plan_publication(bundle, packet, changed, assessed_at=ASSESSED_AT)
    codes = {issue.code for issue in check.issues}

    assert check.current is False and check.complete is False
    assert {
        "source-changed",
        "handoff-hash-changed",
        "created-in-future",
        "record-order-changed",
        "outcome-before-handoff",
    } <= codes


def test_verify_detects_missing_unexpected_and_future_outcomes(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    bundle, packet, _ = _workflow(tmp_path, campaign_data)
    original = _completed(
        initialize_campaign_plan_publication(bundle, packet, created_at=CREATED_AT)
    )
    changed = replace(
        original,
        records=(
            replace(
                original.records[0],
                campaign_id="scs_000000000000",
                occurred_at=datetime(2026, 8, 6, tzinfo=timezone.utc),
            ),
        ),
    )

    check = verify_campaign_plan_publication(bundle, packet, changed, assessed_at=ASSESSED_AT)
    codes = {issue.code for issue in check.issues}

    assert check.current is False
    assert {"record-missing", "record-unexpected", "outcome-in-future"} <= codes


def test_failed_outcome_is_current_but_incomplete(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    bundle, packet, _ = _workflow(tmp_path, campaign_data)
    publication = initialize_campaign_plan_publication(bundle, packet, created_at=CREATED_AT)
    failed = replace(
        publication,
        records=(
            replace(
                publication.records[0],
                status="failed",
                recorded_by="Publisher",
                occurred_at=datetime(2026, 8, 4, 11, tzinfo=timezone.utc),
                note="Platform rejected the upload.",
            ),
            publication.records[1],
        ),
    )

    check = verify_campaign_plan_publication(bundle, packet, failed, assessed_at=ASSESSED_AT)

    assert check.current is True and check.complete is False
    assert {issue.code for issue in check.issues} == {
        "publication-failed",
        "publication-pending",
    }


def test_initialize_rejects_naive_or_pre_handoff_creation_time(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    bundle, packet, _ = _workflow(tmp_path, campaign_data)

    with pytest.raises(ConfigError, match="timezone"):
        initialize_campaign_plan_publication(bundle, packet, created_at=datetime(2026, 8, 4, 10))
    with pytest.raises(ConfigError, match="earlier than the handoff"):
        initialize_campaign_plan_publication(
            bundle,
            packet,
            created_at=datetime(2026, 8, 4, 8, tzinfo=timezone.utc),
        )

    adapter = packet.root / "adapter.json"
    adapter.write_bytes(adapter.read_bytes() + b"\n")
    with pytest.raises(ConfigError, match="invalid handoff"):
        initialize_campaign_plan_publication(bundle, packet, created_at=CREATED_AT)


def test_verify_reports_naive_direct_dataclass_timestamps(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    bundle, packet, _ = _workflow(tmp_path, campaign_data)
    publication = _completed(
        initialize_campaign_plan_publication(bundle, packet, created_at=CREATED_AT)
    )
    publication = replace(
        publication,
        created_at=datetime(2026, 8, 4, 10),
        records=(
            replace(publication.records[0], occurred_at=datetime(2026, 8, 4, 11)),
            publication.records[1],
        ),
    )

    check = verify_campaign_plan_publication(bundle, packet, publication, assessed_at=ASSESSED_AT)

    assert check.current is False
    assert {issue.code for issue in check.issues} >= {
        "created-timezone-missing",
        "outcome-timezone-missing",
    }
    with pytest.raises(ConfigError, match="timezone"):
        verify_campaign_plan_publication(
            bundle,
            packet,
            publication,
            assessed_at=datetime(2026, 8, 5, 12),
        )


def test_direct_publication_objects_cannot_bypass_status_validation(
    tmp_path: Path, campaign_data: dict[str, Any]
) -> None:
    bundle, packet, _ = _workflow(tmp_path, campaign_data)
    publication = _completed(
        initialize_campaign_plan_publication(bundle, packet, created_at=CREATED_AT)
    )
    forged = replace(
        publication,
        records=(
            replace(publication.records[0], status=cast(Any, "forged")),
            *publication.records[1:],
        ),
    )

    check = verify_campaign_plan_publication(bundle, packet, forged, assessed_at=ASSESSED_AT)

    assert check.current is False
    assert check.complete is False
    assert {issue.code for issue in check.issues} >= {"publication-invalid"}
    with pytest.raises(ConfigError, match="status"):
        export_campaign_plan_publication(forged, tmp_path / "forged.json")
