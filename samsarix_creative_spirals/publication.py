# Copyright (c) 2026 Samsarix LLC
# SPDX-License-Identifier: MPL-2.0

"""Handoff-bound, operator-attested publication ledgers for campaign plans."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, cast
from urllib.parse import urlsplit

from .handoff import CampaignPlanHandoffPacket, verify_campaign_plan_handoff
from .models import ConfigError, SUPPORTED_PLATFORMS
from .plans import CampaignPlanBundle
from .policy import ContentPolicy
from .review import _format_utc, _normalized_text, _parse_timestamp
from .workflow import _load_json_object

PublicationRecordStatus = Literal["pending", "published", "failed", "skipped"]

MAX_PUBLICATION_RECORDS = 500
MAX_PUBLICATION_URL_LENGTH = 2_000
_PUBLICATION_KEYS = {
    "schemaVersion",
    "artifactType",
    "planId",
    "sourceHash",
    "handoffId",
    "handoffHash",
    "createdAt",
    "records",
}
_RECORD_KEYS = {
    "sequence",
    "campaignId",
    "platform",
    "status",
    "recordedBy",
    "occurredAt",
    "url",
    "note",
}
_TERMINAL_STATUSES = {"published", "failed", "skipped"}
_PLAN_ID_RE = re.compile(r"^scp_[0-9a-f]{12}$")
_CAMPAIGN_ID_RE = re.compile(r"^scs_[0-9a-f]{12}$")
_HANDOFF_ID_RE = re.compile(r"^sch_[0-9a-f]{12}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _publication_url(value: Any, *, field: str, issues: list[str]) -> str:
    if not isinstance(value, str):
        issues.append(f"{field} must be a string")
        return ""
    result = value.strip()
    if not result:
        issues.append(f"{field} must not be empty")
        return result
    if len(result) > MAX_PUBLICATION_URL_LENGTH:
        issues.append(f"{field} must be at most {MAX_PUBLICATION_URL_LENGTH} characters")
    if any(
        character.isspace() or ord(character) < 32 or ord(character) == 127 for character in result
    ):
        issues.append(f"{field} must not contain whitespace or control characters")
    try:
        parsed = urlsplit(result)
        port = parsed.port
    except ValueError:
        parsed = None
        port = None
        issues.append(f"{field} must be a valid absolute HTTP(S) URL")
    if parsed is not None:
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            issues.append(f"{field} must be a valid absolute HTTP(S) URL")
        if parsed.username is not None or parsed.password is not None:
            issues.append(f"{field} must not contain credentials")
        _ = port
    return result


@dataclass(frozen=True, slots=True)
class PublicationRecord:
    """One operator-recorded outcome for an exact generated platform draft."""

    sequence: int
    campaign_id: str
    platform: str
    status: PublicationRecordStatus
    recorded_by: str | None = None
    occurred_at: datetime | None = None
    url: str | None = None
    note: str | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "sequence": self.sequence,
            "campaignId": self.campaign_id,
            "platform": self.platform,
            "status": self.status,
        }
        if self.recorded_by is not None:
            result["recordedBy"] = self.recorded_by
        if self.occurred_at is not None:
            result["occurredAt"] = _format_utc(self.occurred_at)
        if self.url is not None:
            result["url"] = self.url
        if self.note is not None:
            result["note"] = self.note
        return result

    @classmethod
    def from_dict(cls, raw: dict[str, Any], *, index: int) -> PublicationRecord:
        issues: list[str] = []
        field = f"records[{index}]"
        unknown = sorted(str(key) for key in raw if key not in _RECORD_KEYS)
        if unknown:
            issues.append(f"{field} has unknown field(s): {', '.join(unknown)}")

        sequence_value = raw.get("sequence")
        sequence = (
            sequence_value
            if isinstance(sequence_value, int) and not isinstance(sequence_value, bool)
            else 0
        )
        if not 1 <= sequence <= 100:
            issues.append(f"{field}.sequence must be between 1 and 100")

        campaign_value = raw.get("campaignId")
        campaign_id = campaign_value if isinstance(campaign_value, str) else ""
        if not _CAMPAIGN_ID_RE.fullmatch(campaign_id):
            issues.append(f"{field}.campaignId must be a Samsarix campaign ID")

        platform_value = raw.get("platform")
        platform = platform_value if isinstance(platform_value, str) else ""
        if platform not in SUPPORTED_PLATFORMS:
            issues.append(f"{field}.platform must be one of: {', '.join(SUPPORTED_PLATFORMS)}")

        status_value = raw.get("status")
        status: PublicationRecordStatus = (
            cast(PublicationRecordStatus, status_value)
            if isinstance(status_value, str)
            and status_value in {"pending", "published", "failed", "skipped"}
            else "pending"
        )
        if not isinstance(status_value, str) or status_value not in {
            "pending",
            "published",
            "failed",
            "skipped",
        }:
            issues.append(f"{field}.status must be pending, published, failed, or skipped")

        recorded_by = None
        if "recordedBy" in raw:
            recorded_by = _normalized_text(
                raw["recordedBy"],
                field=f"{field}.recordedBy",
                maximum=120,
                multiline=False,
                issues=issues,
            )
        occurred_at = None
        if "occurredAt" in raw:
            occurred_at = _parse_timestamp(
                raw["occurredAt"], field=f"{field}.occurredAt", issues=issues
            )
        url = None
        if "url" in raw:
            url = _publication_url(raw["url"], field=f"{field}.url", issues=issues)
        note = None
        if "note" in raw:
            note = _normalized_text(
                raw["note"],
                field=f"{field}.note",
                maximum=500,
                multiline=True,
                issues=issues,
            )

        present_outcome_fields = {
            key for key in ("recordedBy", "occurredAt", "url", "note") if key in raw
        }
        if status == "pending" and present_outcome_fields:
            issues.append(f"{field} pending records must not contain outcome fields")
        elif status in _TERMINAL_STATUSES:
            if recorded_by is None:
                issues.append(f"{field}.recordedBy is required for {status} records")
            if occurred_at is None:
                issues.append(f"{field}.occurredAt is required for {status} records")
            if status == "published":
                if url is None:
                    issues.append(f"{field}.url is required for published records")
            elif note is None:
                issues.append(f"{field}.note is required for {status} records")
            if status != "published" and url is not None:
                issues.append(f"{field}.url is only allowed for published records")

        if issues:
            raise ConfigError(issues)
        return cls(sequence, campaign_id, platform, status, recorded_by, occurred_at, url, note)


@dataclass(frozen=True, slots=True)
class CampaignPlanPublication:
    """Unsigned sidecar ledger bound to an exact plan and approved handoff."""

    plan_id: str
    source_hash: str
    handoff_id: str
    handoff_hash: str
    created_at: datetime
    records: tuple[PublicationRecord, ...]

    @property
    def publication_hash(self) -> str:
        payload = json.dumps(
            self.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    @property
    def publication_id(self) -> str:
        return f"scpub_{self.publication_hash[:12]}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": 1,
            "artifactType": "plan-publication",
            "planId": self.plan_id,
            "sourceHash": self.source_hash,
            "handoffId": self.handoff_id,
            "handoffHash": self.handoff_hash,
            "createdAt": _format_utc(self.created_at),
            "records": [record.to_dict() for record in self.records],
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> CampaignPlanPublication:
        issues: list[str] = []
        unknown = sorted(str(key) for key in raw if key not in _PUBLICATION_KEYS)
        if unknown:
            issues.append(f"unknown publication field(s): {', '.join(unknown)}")
        if raw.get("schemaVersion") != 1 or isinstance(raw.get("schemaVersion"), bool):
            issues.append("schemaVersion must be 1")
        if raw.get("artifactType") != "plan-publication":
            issues.append("artifactType must be plan-publication")

        plan_value = raw.get("planId")
        plan_id = plan_value if isinstance(plan_value, str) else ""
        if not _PLAN_ID_RE.fullmatch(plan_id):
            issues.append("planId must be a Samsarix campaign plan ID")
        source_value = raw.get("sourceHash")
        source_hash = source_value if isinstance(source_value, str) else ""
        if not _SHA256_RE.fullmatch(source_hash):
            issues.append("sourceHash must be a lowercase SHA-256 hash")
        handoff_value = raw.get("handoffId")
        handoff_id = handoff_value if isinstance(handoff_value, str) else ""
        if not _HANDOFF_ID_RE.fullmatch(handoff_id):
            issues.append("handoffId must be a Samsarix handoff ID")
        handoff_hash_value = raw.get("handoffHash")
        handoff_hash = handoff_hash_value if isinstance(handoff_hash_value, str) else ""
        if not _SHA256_RE.fullmatch(handoff_hash):
            issues.append("handoffHash must be a lowercase SHA-256 hash")
        created_at = _parse_timestamp(raw.get("createdAt"), field="createdAt", issues=issues)

        records_value = raw.get("records")
        records: list[PublicationRecord] = []
        if not isinstance(records_value, list):
            issues.append("records must be an array")
        else:
            if not 1 <= len(records_value) <= MAX_PUBLICATION_RECORDS:
                issues.append(
                    f"records must contain between 1 and {MAX_PUBLICATION_RECORDS} entries"
                )
            seen: set[tuple[int, str]] = set()
            for index, record_value in enumerate(records_value):
                if not isinstance(record_value, dict):
                    issues.append(f"records[{index}] must be an object")
                    continue
                try:
                    record = PublicationRecord.from_dict(record_value, index=index)
                except ConfigError as error:
                    issues.extend(error.issues)
                    continue
                key = (record.sequence, record.platform)
                if key in seen:
                    issues.append(
                        f"records[{index}] duplicates item {record.sequence} {record.platform}"
                    )
                else:
                    seen.add(key)
                    records.append(record)

        if issues:
            raise ConfigError(issues)
        assert created_at is not None
        return cls(plan_id, source_hash, handoff_id, handoff_hash, created_at, tuple(records))


@dataclass(frozen=True, slots=True)
class PublicationIssue:
    """One stable integrity or workflow finding for a publication ledger."""

    code: str
    severity: Literal["warning", "error"]
    message: str
    item: int | None = None
    platform: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "item": self.item,
            "platform": self.platform,
            "message": self.message,
        }


@dataclass(frozen=True, slots=True)
class PublicationCheck:
    """Offline verification result for one current-plan publication ledger."""

    publication_id: str
    plan_id: str
    current: bool
    complete: bool
    counts: tuple[tuple[str, int], ...]
    issues: tuple[PublicationIssue, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": 1,
            "current": self.current,
            "complete": self.complete,
            "publicationId": self.publication_id,
            "planId": self.plan_id,
            "counts": dict(self.counts),
            "issues": [issue.to_dict() for issue in self.issues],
        }


def initialize_campaign_plan_publication(
    bundle: CampaignPlanBundle,
    packet: CampaignPlanHandoffPacket,
    *,
    created_at: datetime | None = None,
    content_policy: ContentPolicy | None = None,
) -> CampaignPlanPublication:
    """Create a pending ledger only after its exact handoff verifies offline."""
    issues: list[str] = []
    timestamp = created_at or datetime.now(timezone.utc)
    if timestamp.utcoffset() is None:
        issues.append("created_at must include timezone information")
    handoff_check = verify_campaign_plan_handoff(bundle, packet, content_policy=content_policy)
    if not handoff_check.valid:
        detail = ", ".join(issue.message for issue in handoff_check.issues)
        issues.append(f"cannot initialize publication ledger from an invalid handoff: {detail}")
    if timestamp.utcoffset() is not None and timestamp < packet.handoff.generated_at:
        issues.append("created_at must not be earlier than the handoff generation time")
    if issues:
        raise ConfigError(issues)
    records = tuple(
        PublicationRecord(
            sequence=item.sequence,
            campaign_id=item.bundle.campaign_id,
            platform=draft.platform,
            status="pending",
        )
        for item in bundle.items
        for draft in item.bundle.drafts
    )
    return CampaignPlanPublication(
        plan_id=bundle.plan_id,
        source_hash=bundle.source_hash,
        handoff_id=packet.handoff.handoff_id,
        handoff_hash=packet.handoff.handoff_hash,
        created_at=timestamp.astimezone(timezone.utc),
        records=records,
    )


def load_campaign_plan_publication(path: str | Path) -> CampaignPlanPublication:
    """Load and structurally validate one bounded publication-ledger JSON file."""
    return CampaignPlanPublication.from_dict(_load_json_object(path, kind="publication ledger"))


def _validated_publication_object(
    publication: CampaignPlanPublication,
) -> CampaignPlanPublication:
    """Apply the serialized contract to a directly constructed public value."""
    if not isinstance(publication, CampaignPlanPublication):
        raise ConfigError("publication must be a CampaignPlanPublication value")
    try:
        CampaignPlanPublication.from_dict(publication.to_dict())
    except ConfigError:
        raise
    except (AttributeError, TypeError, ValueError) as error:
        raise ConfigError(f"publication object is structurally invalid: {error}") from error
    return publication


def export_campaign_plan_publication(
    publication: CampaignPlanPublication, path: str | Path
) -> Path:
    """Write a new ledger without replacing existing operator evidence."""
    publication = _validated_publication_object(publication)
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(publication.to_dict(), ensure_ascii=False, indent=2) + "\n"
    try:
        with destination.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
    except FileExistsError:
        raise ConfigError(
            f"refusing to overwrite existing publication ledger: {destination}"
        ) from None
    return destination


def _expected_records(bundle: CampaignPlanBundle) -> tuple[tuple[int, str, str], ...]:
    return tuple(
        (item.sequence, item.bundle.campaign_id, draft.platform)
        for item in bundle.items
        for draft in item.bundle.drafts
    )


def record_campaign_plan_publication(
    bundle: CampaignPlanBundle,
    packet: CampaignPlanHandoffPacket,
    publication: CampaignPlanPublication,
    *,
    sequence: int,
    platform: str,
    status: Literal["published", "failed", "skipped"],
    recorded_by: str,
    occurred_at: datetime,
    url: str | None = None,
    note: str | None = None,
    replace_outcome: bool = False,
    assessed_at: datetime | None = None,
    content_policy: ContentPolicy | None = None,
) -> CampaignPlanPublication:
    """Return a new verified ledger snapshot recording one operator-attested outcome.

    No files are changed and no provider is contacted. Failed attempts may be retried;
    changing a published/skipped outcome requires explicit replacement. Exact repeats
    are idempotent. Use the exclusive exporter to retain the previous snapshot.
    """
    timestamp = assessed_at if assessed_at is not None else datetime.now(timezone.utc)
    if not isinstance(timestamp, datetime) or timestamp.utcoffset() is None:
        raise ConfigError("assessed_at must be a datetime with timezone information")
    if not isinstance(occurred_at, datetime) or occurred_at.utcoffset() is None:
        raise ConfigError("occurred_at must be a datetime with timezone information")
    if not isinstance(sequence, int) or isinstance(sequence, bool) or not 1 <= sequence <= 100:
        raise ConfigError("sequence must be an integer between 1 and 100")
    if not isinstance(platform, str) or platform not in SUPPORTED_PLATFORMS:
        raise ConfigError(f"platform must be one of: {', '.join(SUPPORTED_PLATFORMS)}")
    if not isinstance(status, str) or status not in {"published", "failed", "skipped"}:
        raise ConfigError("status must be published, failed, or skipped")
    if not isinstance(replace_outcome, bool):
        raise ConfigError("replace_outcome must be a boolean")

    before = verify_campaign_plan_publication(
        bundle, packet, publication, assessed_at=timestamp, content_policy=content_policy
    )
    if not before.current:
        detail = ", ".join(issue.code for issue in before.issues if issue.severity == "error")
        raise ConfigError(f"cannot record an outcome on a non-current publication ledger: {detail}")
    index = next(
        (
            index
            for index, record in enumerate(publication.records)
            if record.sequence == sequence and record.platform == platform
        ),
        None,
    )
    if index is None:
        raise ConfigError("no publication record matches the requested sequence and platform")
    previous = PublicationRecord.from_dict(publication.records[index].to_dict(), index=index)
    raw: dict[str, Any] = {
        "sequence": sequence,
        "campaignId": previous.campaign_id,
        "platform": platform,
        "status": status,
        "recordedBy": recorded_by,
        "occurredAt": _format_utc(occurred_at),
    }
    if url is not None:
        raw["url"] = url
    if note is not None:
        raw["note"] = note
    outcome = PublicationRecord.from_dict(raw, index=index)
    if outcome == previous:
        return publication
    if previous.status in {"published", "skipped"} and not replace_outcome:
        raise ConfigError("changing a published or skipped record requires replace_outcome=True")
    if previous.occurred_at is not None and occurred_at < previous.occurred_at:
        raise ConfigError("occurred_at must not be earlier than the previous recorded outcome")
    records = list(publication.records)
    records[index] = outcome
    result = replace(publication, records=tuple(records))
    after = verify_campaign_plan_publication(
        bundle, packet, result, assessed_at=timestamp, content_policy=content_policy
    )
    if not after.current:
        detail = ", ".join(issue.code for issue in after.issues if issue.severity == "error")
        raise ConfigError(f"recorded outcome would invalidate the publication ledger: {detail}")
    return result


def verify_campaign_plan_publication(
    bundle: CampaignPlanBundle,
    packet: CampaignPlanHandoffPacket,
    publication: CampaignPlanPublication,
    *,
    assessed_at: datetime | None = None,
    content_policy: ContentPolicy | None = None,
) -> PublicationCheck:
    """Verify ledger bindings, record coverage, chronology, and workflow completion offline."""
    timestamp = assessed_at or datetime.now(timezone.utc)
    if timestamp.utcoffset() is None:
        raise ConfigError("assessed_at must include timezone information")
    timestamp = timestamp.astimezone(timezone.utc)
    issues: list[PublicationIssue] = []
    current = True

    def integrity(
        code: str, message: str, *, item: int | None = None, platform: str | None = None
    ) -> None:
        nonlocal current
        current = False
        issues.append(PublicationIssue(code, "error", message, item, platform))

    handoff_check = verify_campaign_plan_handoff(bundle, packet, content_policy=content_policy)
    for issue in handoff_check.issues:
        integrity(f"handoff-{issue.code}", issue.message)
    try:
        publication = _validated_publication_object(publication)
    except ConfigError as error:
        integrity("publication-invalid", f"Ledger structure is invalid: {error}")
        return PublicationCheck(
            publication_id="scpub_invalid",
            plan_id=bundle.plan_id,
            current=False,
            complete=False,
            counts=(
                ("records", 0),
                ("pending", 0),
                ("published", 0),
                ("failed", 0),
                ("skipped", 0),
            ),
            issues=tuple(issues),
        )
    if publication.plan_id != bundle.plan_id:
        integrity("plan-id-changed", "Ledger plan ID does not match current source.")
    if publication.source_hash != bundle.source_hash:
        integrity("source-changed", "Ledger source hash does not match current source.")
    if publication.handoff_id != packet.handoff.handoff_id:
        integrity("handoff-id-changed", "Ledger handoff ID does not match the supplied packet.")
    if publication.handoff_hash != packet.handoff.handoff_hash:
        integrity("handoff-hash-changed", "Ledger handoff hash does not match the supplied packet.")
    if publication.created_at.utcoffset() is None:
        integrity("created-timezone-missing", "Ledger creation time must include a UTC offset.")
    else:
        if publication.created_at < packet.handoff.generated_at:
            integrity("created-before-handoff", "Ledger creation time is earlier than its handoff.")
        if publication.created_at > timestamp:
            integrity(
                "created-in-future", "Ledger creation time is later than the assessment time."
            )

    expected = _expected_records(bundle)
    actual = tuple(
        (record.sequence, record.campaign_id, record.platform) for record in publication.records
    )
    if actual != expected:
        expected_set = set(expected)
        actual_set = set(actual)
        for sequence, campaign_id, platform in expected:
            if (sequence, campaign_id, platform) not in actual_set:
                integrity(
                    "record-missing",
                    f"Ledger is missing the expected {campaign_id} draft.",
                    item=sequence,
                    platform=platform,
                )
        for sequence, campaign_id, platform in actual:
            if (sequence, campaign_id, platform) not in expected_set:
                integrity(
                    "record-unexpected",
                    f"Ledger contains an unexpected {campaign_id} draft.",
                    item=sequence,
                    platform=platform,
                )
        if actual_set == expected_set:
            integrity("record-order-changed", "Ledger records are not in canonical plan order.")

    for record in publication.records:
        if record.occurred_at is not None:
            if record.occurred_at.utcoffset() is None:
                integrity(
                    "outcome-timezone-missing",
                    "Recorded outcome time must include a UTC offset.",
                    item=record.sequence,
                    platform=record.platform,
                )
            else:
                if record.occurred_at < packet.handoff.generated_at:
                    integrity(
                        "outcome-before-handoff",
                        "Recorded outcome is earlier than the approved handoff.",
                        item=record.sequence,
                        platform=record.platform,
                    )
                if record.occurred_at > timestamp:
                    integrity(
                        "outcome-in-future",
                        "Recorded outcome is later than the assessment time.",
                        item=record.sequence,
                        platform=record.platform,
                    )
        if record.status == "pending":
            issues.append(
                PublicationIssue(
                    "publication-pending",
                    "warning",
                    "Publication outcome has not been recorded.",
                    record.sequence,
                    record.platform,
                )
            )
        elif record.status == "failed":
            issues.append(
                PublicationIssue(
                    "publication-failed",
                    "error",
                    "Operator recorded a failed publication attempt.",
                    record.sequence,
                    record.platform,
                )
            )

    counts_by_status = {
        status: sum(record.status == status for record in publication.records)
        for status in ("pending", "published", "failed", "skipped")
    }
    complete = current and counts_by_status["pending"] == 0 and counts_by_status["failed"] == 0
    counts = (
        ("records", len(publication.records)),
        ("pending", counts_by_status["pending"]),
        ("published", counts_by_status["published"]),
        ("failed", counts_by_status["failed"]),
        ("skipped", counts_by_status["skipped"]),
    )
    return PublicationCheck(
        publication_id=publication.publication_id,
        plan_id=bundle.plan_id,
        current=current,
        complete=complete,
        counts=counts,
        issues=tuple(issues),
    )
