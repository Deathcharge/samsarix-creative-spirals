# Copyright (c) 2026 Samsarix LLC
# SPDX-License-Identifier: MPL-2.0

"""Bounded multi-campaign planning, quality checks, and portable exports."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import re
import unicodedata
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import CampaignBundle, CampaignConfig, ConfigError, SUPPORTED_PLATFORMS
from .policy import ContentPolicy, ContentPolicyBinding
from .quality import check_campaign
from .workflow import _load_json_object, _slugify, build_campaign, load_campaign

MAX_PLAN_ITEMS = 100
_PLAN_KEYS = {"schemaVersion", "name", "requiredPlatforms", "items"}
_PLAN_ITEM_KEYS = {"campaign", "intendedAt"}
_RFC3339_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$")
_MISSING = object()
_CSV_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r", "\n", "＝", "＋", "－", "＠")
_CSV_FIELDS = (
    "plan_id",
    "sequence",
    "campaign_id",
    "source_hash",
    "name",
    "intended_at_utc",
    "content",
    "character_count",
    "character_limit",
    "truncated",
    "warnings",
)


def _normalize_single_line(value: str) -> str:
    return unicodedata.normalize("NFC", value).strip()


def _format_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_intended_at(value: Any, *, field: str, issues: list[str]) -> datetime | None:
    if value is _MISSING:
        return None
    if not isinstance(value, str) or not _RFC3339_RE.fullmatch(value):
        issues.append(f"{field} must be an RFC 3339 date-time with an explicit offset or Z")
        return None
    normalized = re.sub(
        r"\.(\d+)(?=Z|[+-]\d{2}:\d{2}$)",
        lambda match: "." + (match.group(1) + "000000")[:6],
        value,
    )
    try:
        parsed = datetime.fromisoformat(normalized.replace("Z", "+00:00"))
    except ValueError:
        issues.append(f"{field} must be a valid date and time")
        return None
    if value.endswith("-00:00"):
        issues.append(f"{field} must use a known UTC offset instead of -00:00")
        return None
    return parsed.astimezone(timezone.utc)


def _parse_platforms(value: Any, *, field: str, issues: list[str]) -> tuple[str, ...]:
    if not isinstance(value, list):
        issues.append(f"{field} must be an array of supported platforms")
        return ()
    if len(value) > len(SUPPORTED_PLATFORMS):
        issues.append(f"{field} must contain at most {len(SUPPORTED_PLATFORMS)} items")
    result: list[str] = []
    seen: set[str] = set()
    for index, candidate in enumerate(value):
        if not isinstance(candidate, str):
            issues.append(f"{field}[{index}] must be a string")
            continue
        platform = candidate.strip().lower()
        if platform not in SUPPORTED_PLATFORMS:
            issues.append(f"{field}[{index}] must be one of: {', '.join(SUPPORTED_PLATFORMS)}")
        elif platform in seen:
            issues.append(f"{field}[{index}] duplicates {platform}")
        else:
            seen.add(platform)
            result.append(platform)
    return tuple(result)


def _resolve_campaign_path(
    value: Any,
    *,
    field: str,
    base_dir: Path,
    issues: list[str],
) -> tuple[str, Path] | None:
    if not isinstance(value, str):
        issues.append(f"{field} must be a relative JSON file path")
        return None
    source = unicodedata.normalize("NFC", value).strip()
    segments = source.split("/")
    if (
        not source
        or len(source) > 500
        or "\\" in source
        or ":" in source
        or any(character in '<>"|?*' for character in source)
        or any(unicodedata.category(character) in {"Cc", "Cs"} for character in source)
        or source.startswith("/")
        or any(segment in {"", ".", ".."} for segment in segments)
        or not source.endswith(".json")
    ):
        issues.append(
            f"{field} must be a portable relative .json path without empty, dot, or parent segments"
        )
        return None
    root = base_dir.resolve()
    resolved = (root / Path(*segments)).resolve()
    if not resolved.is_relative_to(root):
        issues.append(f"{field} resolves outside the plan directory")
        return None
    return source, resolved


@dataclass(frozen=True, slots=True)
class CampaignPlanItem:
    """One referenced campaign and its optional intended publication time."""

    source: str
    campaign: CampaignConfig
    intended_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"campaign": self.source}
        if self.intended_at is not None:
            result["intendedAt"] = _format_utc(self.intended_at)
        return result


@dataclass(frozen=True, slots=True)
class CampaignPlan:
    """A validated, bounded sequence of campaign references."""

    schema_version: int
    name: str
    required_platforms: tuple[str, ...]
    items: tuple[CampaignPlanItem, ...]

    @classmethod
    def from_dict(cls, raw: dict[str, Any], *, base_dir: str | Path) -> CampaignPlan:
        """Validate a plan mapping and load its confined campaign references."""
        issues: list[str] = []
        unknown = sorted(str(key) for key in raw if key not in _PLAN_KEYS)
        if unknown:
            issues.append(f"unknown plan field(s): {', '.join(unknown)}")

        schema_version = raw.get("schemaVersion")
        if isinstance(schema_version, bool) or schema_version != 1:
            issues.append("schemaVersion must be 1")

        name_value = raw.get("name")
        if not isinstance(name_value, str):
            issues.append("name must be a string")
            name = ""
        else:
            name = _normalize_single_line(name_value)
            if not name:
                issues.append("name must not be empty")
            elif len(name) > 120:
                issues.append("name must be at most 120 characters")
            if any(unicodedata.category(char) in {"Cc", "Cs"} for char in name):
                issues.append("name must be a single line without control characters")

        required_platforms = _parse_platforms(
            raw.get("requiredPlatforms", []), field="requiredPlatforms", issues=issues
        )

        items_value = raw.get("items")
        items: list[CampaignPlanItem] = []
        campaign_cache: dict[Path, CampaignConfig] = {}
        if not isinstance(items_value, list):
            issues.append("items must be a non-empty array")
        else:
            if not items_value:
                issues.append("items must contain at least one campaign")
            if len(items_value) > MAX_PLAN_ITEMS:
                issues.append(f"items must contain at most {MAX_PLAN_ITEMS} campaigns")
            for index, item_value in enumerate(items_value[:MAX_PLAN_ITEMS]):
                field = f"items[{index}]"
                if not isinstance(item_value, dict):
                    issues.append(f"{field} must be an object")
                    continue
                item_unknown = sorted(str(key) for key in item_value if key not in _PLAN_ITEM_KEYS)
                if item_unknown:
                    issues.append(f"{field} has unknown field(s): {', '.join(item_unknown)}")
                campaign_path = _resolve_campaign_path(
                    item_value.get("campaign"),
                    field=f"{field}.campaign",
                    base_dir=Path(base_dir),
                    issues=issues,
                )
                intended_at = _parse_intended_at(
                    item_value.get("intendedAt", _MISSING),
                    field=f"{field}.intendedAt",
                    issues=issues,
                )
                if campaign_path is None:
                    continue
                source, resolved = campaign_path
                try:
                    campaign = campaign_cache.get(resolved)
                    if campaign is None:
                        campaign = load_campaign(resolved)
                        campaign_cache[resolved] = campaign
                except ConfigError as error:
                    issues.extend(f"{field}.campaign: {issue}" for issue in error.issues)
                    continue
                items.append(
                    CampaignPlanItem(
                        source=source,
                        campaign=campaign,
                        intended_at=intended_at,
                    )
                )

        if issues:
            raise ConfigError(issues)
        return cls(
            schema_version=1,
            name=name,
            required_platforms=required_platforms,
            items=tuple(items),
        )

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "schemaVersion": self.schema_version,
            "name": self.name,
            "items": [item.to_dict() for item in self.items],
        }
        if self.required_platforms:
            result["requiredPlatforms"] = list(self.required_platforms)
        return result


@dataclass(frozen=True, slots=True)
class PlannedCampaign:
    """One built campaign in plan order."""

    sequence: int
    source: str
    intended_at: datetime | None
    bundle: CampaignBundle

    def to_dict(self) -> dict[str, Any]:
        return {
            "sequence": self.sequence,
            "source": self.source,
            "intendedAt": _format_utc(self.intended_at) if self.intended_at else None,
            "campaign": self.bundle.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class CampaignPlanBundle:
    """Deterministic built representation of a complete campaign plan."""

    plan_id: str
    source_hash: str
    name: str
    required_platforms: tuple[str, ...]
    items: tuple[PlannedCampaign, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": 1,
            "planId": self.plan_id,
            "sourceHash": self.source_hash,
            "name": self.name,
            "requiredPlatforms": list(self.required_platforms),
            "items": [item.to_dict() for item in self.items],
        }


@dataclass(frozen=True, slots=True)
class PlanIssue:
    """One stable, machine-readable plan or campaign finding."""

    code: str
    severity: str
    item: int
    message: str
    campaign_id: str | None = None
    platform: str | None = None
    rule_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "code": self.code,
            "severity": self.severity,
            "item": self.item,
            "campaignId": self.campaign_id,
            "platform": self.platform,
            "message": self.message,
        }
        if self.rule_id is not None:
            result["ruleId"] = self.rule_id
        return result


@dataclass(frozen=True, slots=True)
class CampaignPlanCheck:
    """Aggregate quality result for a complete plan."""

    plan_id: str
    publishable: bool
    issues: tuple[PlanIssue, ...]
    content_policy: ContentPolicyBinding | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "schemaVersion": 1,
            "planId": self.plan_id,
            "publishable": self.publishable,
            "issues": [issue.to_dict() for issue in self.issues],
        }
        if self.content_policy is not None:
            result["contentPolicy"] = self.content_policy.to_dict()
        return result


def load_campaign_plan(path: str | Path) -> CampaignPlan:
    """Load a bounded plan and campaign references confined beneath its directory."""
    plan_path = Path(path)
    raw = _load_json_object(plan_path, kind="plan")
    return CampaignPlan.from_dict(raw, base_dir=plan_path.resolve().parent)


def _canonical_plan(plan: CampaignPlan) -> bytes:
    payload: dict[str, Any] = {
        "schemaVersion": plan.schema_version,
        "name": plan.name,
        "requiredPlatforms": list(plan.required_platforms),
        "items": [
            {
                **item.to_dict(),
                "campaignConfig": item.campaign.to_dict(),
            }
            for item in plan.items
        ],
    }
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def build_campaign_plan(plan: CampaignPlan) -> CampaignPlanBundle:
    """Build every campaign and a deterministic identity for the complete plan."""
    source_hash = hashlib.sha256(_canonical_plan(plan)).hexdigest()
    items = tuple(
        PlannedCampaign(
            sequence=index,
            source=item.source,
            intended_at=item.intended_at,
            bundle=build_campaign(item.campaign),
        )
        for index, item in enumerate(plan.items, start=1)
    )
    return CampaignPlanBundle(
        plan_id=f"scp_{source_hash[:12]}",
        source_hash=source_hash,
        name=plan.name,
        required_platforms=plan.required_platforms,
        items=items,
    )


def check_campaign_plan(
    bundle: CampaignPlanBundle,
    *,
    warnings_as_errors: bool = False,
    content_policy: ContentPolicy | None = None,
) -> CampaignPlanCheck:
    """Aggregate item quality with sequence- and coverage-level plan checks."""
    issues: list[PlanIssue] = []
    warning_severity = "error" if warnings_as_errors else "warning"
    seen_times: dict[datetime, int] = {}
    previous_time: datetime | None = None

    for item in bundle.items:
        item_platforms = {draft.platform for draft in item.bundle.drafts}
        for platform in bundle.required_platforms:
            if platform not in item_platforms:
                issues.append(
                    PlanIssue(
                        code="missing-platform",
                        severity="error",
                        item=item.sequence,
                        campaign_id=item.bundle.campaign_id,
                        platform=platform,
                        message=f"Campaign does not include required platform {platform}.",
                    )
                )

        campaign_check = check_campaign(
            item.bundle,
            warnings_as_errors=warnings_as_errors,
            content_policy=content_policy,
        )
        for campaign_issue in campaign_check.issues:
            issues.append(
                PlanIssue(
                    code=f"campaign-{campaign_issue.code}",
                    severity=campaign_issue.severity,
                    item=item.sequence,
                    campaign_id=item.bundle.campaign_id,
                    platform=campaign_issue.platform,
                    message=campaign_issue.message,
                    rule_id=campaign_issue.rule_id,
                )
            )

        if item.intended_at is None:
            continue
        earlier_item = seen_times.get(item.intended_at)
        if earlier_item is not None:
            issues.append(
                PlanIssue(
                    code="duplicate-time",
                    severity=warning_severity,
                    item=item.sequence,
                    campaign_id=item.bundle.campaign_id,
                    message=f"Intended time duplicates item {earlier_item}.",
                )
            )
        else:
            seen_times[item.intended_at] = item.sequence
        if previous_time is not None and item.intended_at < previous_time:
            issues.append(
                PlanIssue(
                    code="out-of-order",
                    severity=warning_severity,
                    item=item.sequence,
                    campaign_id=item.bundle.campaign_id,
                    message="Intended time is earlier than the preceding scheduled item.",
                )
            )
        previous_time = item.intended_at

    return CampaignPlanCheck(
        plan_id=bundle.plan_id,
        publishable=not any(issue.severity == "error" for issue in issues),
        issues=tuple(issues),
        content_policy=content_policy.binding if content_policy is not None else None,
    )


def _ical_escape(value: str) -> str:
    normalized = value.replace("\r\n", "\n").replace("\r", "\n")
    return (
        normalized.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def _fold_ical_line(line: str) -> list[str]:
    folded: list[str] = []
    current = ""
    byte_limit = 75
    for character in line:
        if current and len((current + character).encode("utf-8")) > byte_limit:
            folded.append(current if not folded else f" {current}")
            current = character
            byte_limit = 74
        else:
            current += character
    folded.append(current if not folded else f" {current}")
    return folded


def render_plan_calendar(
    bundle: CampaignPlanBundle,
    *,
    generated_at: datetime,
) -> str:
    """Render RFC 5545 VEVENT/VTODO components with CRLF and UTF-8-safe folding."""
    if generated_at.utcoffset() is None:
        raise ConfigError("generated_at must include timezone information")
    stamp = generated_at.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Samsarix LLC//Creative Spirals//EN",
        "CALSCALE:GREGORIAN",
        f"X-WR-CALNAME:{_ical_escape(bundle.name)}",
    ]
    for item in bundle.items:
        component = "VEVENT" if item.intended_at is not None else "VTODO"
        platforms = ", ".join(draft.platform for draft in item.bundle.drafts)
        description = f"Campaign ID: {item.bundle.campaign_id}\nPlatforms: {platforms}"
        lines.extend(
            [
                f"BEGIN:{component}",
                f"UID:{bundle.plan_id}-{item.sequence}-{item.bundle.campaign_id}@samsarix.com",
                f"DTSTAMP:{stamp}",
            ]
        )
        if item.intended_at is not None:
            lines.append(
                f"DTSTART:{item.intended_at.astimezone(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
            )
        lines.extend(
            [
                f"SUMMARY:{_ical_escape(item.bundle.name)}",
                f"DESCRIPTION:{_ical_escape(description)}",
                "TRANSP:TRANSPARENT" if component == "VEVENT" else "STATUS:NEEDS-ACTION",
                f"END:{component}",
            ]
        )
    lines.append("END:VCALENDAR")
    return "\r\n".join(part for line in lines for part in _fold_ical_line(line)) + "\r\n"


def _csv_payload(bundle: CampaignPlanBundle, platform: str) -> str:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=_CSV_FIELDS, lineterminator="\n")
    writer.writeheader()
    for item in bundle.items:
        draft = next((draft for draft in item.bundle.drafts if draft.platform == platform), None)
        if draft is None:
            continue
        writer.writerow(
            {
                "plan_id": bundle.plan_id,
                "sequence": item.sequence,
                "campaign_id": item.bundle.campaign_id,
                "source_hash": item.bundle.source_hash,
                "name": _csv_safe_text(item.bundle.name),
                "intended_at_utc": _format_utc(item.intended_at) if item.intended_at else "",
                "content": _csv_safe_text(draft.content),
                "character_count": draft.character_count,
                "character_limit": draft.character_limit,
                "truncated": str(draft.truncated).lower(),
                "warnings": _csv_safe_text(" | ".join(draft.warnings)),
            }
        )
    return stream.getvalue()


def _csv_safe_text(value: str) -> str:
    """Keep spreadsheet applications from interpreting exported text as a formula."""
    return f"'{value}" if value.startswith(_CSV_FORMULA_PREFIXES) else value


def _used_platforms(bundle: CampaignPlanBundle) -> list[str]:
    used = {draft.platform for item in bundle.items for draft in item.bundle.drafts}
    return [platform for platform in SUPPORTED_PLATFORMS if platform in used]


def _plan_manifest(bundle: CampaignPlanBundle, generated_at: datetime) -> dict[str, Any]:
    platforms = _used_platforms(bundle)
    return {
        "schemaVersion": 1,
        "planId": bundle.plan_id,
        "sourceHash": bundle.source_hash,
        "name": bundle.name,
        "generatedAt": _format_utc(generated_at),
        "adapter": "adapter.json",
        "calendar": "calendar.ics",
        "platformCsv": {platform: f"csv/{platform}.csv" for platform in platforms},
        "items": [
            {
                "sequence": item.sequence,
                "source": item.source,
                "campaignId": item.bundle.campaign_id,
                "sourceHash": item.bundle.source_hash,
                "intendedAt": _format_utc(item.intended_at) if item.intended_at else None,
                "platforms": [draft.platform for draft in item.bundle.drafts],
                "media": [reference.to_dict() for reference in item.bundle.media],
            }
            for item in bundle.items
        ],
    }


def render_plan_adapter(bundle: CampaignPlanBundle) -> str:
    """Render the deterministic v2 publisher-adapter interchange payload."""
    payload = {
        "schemaVersion": 2,
        "contract": "samsarix.plan-drafts",
        "planId": bundle.plan_id,
        "sourceHash": bundle.source_hash,
        "name": bundle.name,
        "items": [
            {
                "sequence": item.sequence,
                "source": item.source,
                "campaignId": item.bundle.campaign_id,
                "sourceHash": item.bundle.source_hash,
                "intendedAt": _format_utc(item.intended_at) if item.intended_at else None,
                "media": [reference.to_dict() for reference in item.bundle.media],
                "drafts": [draft.to_dict() for draft in item.bundle.drafts],
            }
            for item in bundle.items
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def _plan_artifact_payloads(
    bundle: CampaignPlanBundle,
    generated_at: datetime,
) -> dict[str, bytes]:
    """Render the exact portable files shared by plan exports and approved handoffs."""
    artifacts = {
        f"csv/{platform}.csv": _csv_payload(bundle, platform).encode("utf-8")
        for platform in _used_platforms(bundle)
    }
    artifacts.update(
        {
            "calendar.ics": render_plan_calendar(bundle, generated_at=generated_at).encode("utf-8"),
            "adapter.json": render_plan_adapter(bundle).encode("utf-8"),
            "manifest.json": (
                json.dumps(
                    _plan_manifest(bundle, generated_at),
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n"
            ).encode("utf-8"),
        }
    )
    return artifacts


def _write_plan_artifacts(root: Path, artifacts: dict[str, bytes]) -> None:
    """Write internally generated portable artifact names beneath a prepared directory."""
    for portable_path, payload in artifacts.items():
        destination = root.joinpath(*portable_path.split("/"))
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(payload)


def _clear_plan_temp(path: Path) -> None:
    if not path.exists():
        return
    for child in path.iterdir():
        if child.name == "csv" and child.is_dir() and not child.is_symlink():
            for csv_file in child.iterdir():
                if not csv_file.is_file() or csv_file.is_symlink():
                    raise OSError(f"refusing to clean unexpected temporary entry: {csv_file}")
                csv_file.unlink()
            child.rmdir()
        elif child.is_file() and not child.is_symlink():
            child.unlink()
        else:
            raise OSError(f"refusing to clean unexpected temporary entry: {child}")
    path.rmdir()


def _validate_existing_plan_target(target: Path) -> None:
    allowed = {"adapter.json", "calendar.ics", "manifest.json", "csv"}
    unexpected = [entry for entry in target.iterdir() if entry.name not in allowed]
    if unexpected:
        raise OSError(f"refusing to overwrite bundle with unexpected entry: {unexpected[0]}")
    for filename in ("adapter.json", "calendar.ics", "manifest.json"):
        artifact = target / filename
        if (artifact.exists() or artifact.is_symlink()) and (
            artifact.is_symlink() or not artifact.is_file()
        ):
            raise OSError(f"refusing to overwrite invalid plan artifact: {artifact}")
    csv_dir = target / "csv"
    if csv_dir.exists():
        if csv_dir.is_symlink() or not csv_dir.is_dir():
            raise OSError(f"refusing to overwrite invalid CSV directory: {csv_dir}")
        for csv_file in csv_dir.iterdir():
            if csv_file.is_symlink() or not csv_file.is_file() or csv_file.suffix != ".csv":
                raise OSError(f"refusing to overwrite unexpected CSV entry: {csv_file}")


def export_campaign_plan(
    bundle: CampaignPlanBundle,
    output_root: str | Path = "plan-outbox",
    *,
    overwrite: bool = False,
    generated_at: datetime | None = None,
) -> Path:
    """Export a plan manifest, RFC 5545 calendar, and one CSV per used platform."""
    root = Path(os.path.abspath(output_root))
    if root.exists():
        if root.is_symlink():
            raise OSError(f"refusing to export through a symbolic-link directory: {root}")
        if not root.is_dir():
            raise OSError(f"output root is not a directory: {root}")
    else:
        root.mkdir(parents=True)

    bundle_name = f"{_slugify(bundle.name)}-{bundle.plan_id}"
    target = root / bundle_name
    if target.exists() or target.is_symlink():
        if target.is_symlink() or not target.is_dir():
            raise OSError(f"refusing to overwrite non-directory bundle path: {target}")
        if not overwrite:
            raise FileExistsError(
                f"bundle already exists: {target}; pass --overwrite to replace it"
            )
        _validate_existing_plan_target(target)

    stamp = generated_at or datetime.now(timezone.utc)
    if stamp.utcoffset() is None:
        raise ConfigError("generated_at must include timezone information")
    temporary = root / f".{bundle_name}.{uuid.uuid4().hex}.tmp"
    temporary.mkdir(mode=0o700)
    try:
        _write_plan_artifacts(temporary, _plan_artifact_payloads(bundle, stamp))
        csv_dir = temporary / "csv"

        if not target.exists():
            temporary.replace(target)
        else:
            target_csv = target / "csv"
            target_csv.mkdir(exist_ok=True)
            written = {source.name for source in csv_dir.iterdir()}
            for source in sorted(csv_dir.iterdir()):
                os.replace(source, target_csv / source.name)
            for stale in sorted(target_csv.iterdir()):
                if stale.name not in written:
                    stale.unlink()
            csv_dir.rmdir()
            os.replace(temporary / "calendar.ics", target / "calendar.ics")
            os.replace(temporary / "adapter.json", target / "adapter.json")
            os.replace(temporary / "manifest.json", target / "manifest.json")
            temporary.rmdir()
    finally:
        _clear_plan_temp(temporary)
    return target
