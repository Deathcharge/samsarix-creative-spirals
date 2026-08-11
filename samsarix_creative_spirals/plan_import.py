# Copyright (c) 2026 Samsarix LLC
# SPDX-License-Identifier: MPL-2.0

"""Bounded, atomic CSV import into canonical campaign and plan sources."""

from __future__ import annotations

import csv
import io
import json
import os
import re
import unicodedata
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .filesystem import directory_identity, is_link_like, require_directory_identity
from .models import CampaignConfig, ConfigError, SUPPORTED_PLATFORMS
from .plans import CampaignPlan, load_campaign_plan
from .workflow import _slugify

MAX_PLAN_IMPORT_BYTES = 1_000_000
MAX_PLAN_IMPORT_ISSUES = 2_500
MAX_PLAN_IMPORT_ROWS = 100
PLAN_IMPORT_FIELDS = (
    "name",
    "title",
    "body",
    "link",
    "hashtags",
    "platforms",
    "intended_at",
    "media_path",
    "media_alt_text",
    "media_platforms",
)

_RFC3339_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$")
_ISSUE_FIELD_RE = re.compile(r"^([A-Za-z][A-Za-z0-9]*(?:\[[0-9]+\])?(?:\.[A-Za-z0-9]+)*)")
_ISSUE_CODE_RE = re.compile(r"^[a-z][a-z0-9-]{0,63}$")
_SOURCE_RE = re.compile(r"^campaigns/[0-9]{3}-[a-z0-9]+(?:-[a-z0-9]+)*\.json$")


def _format_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class PlanImportIssue:
    """One stable file-, header-, or logical-row import diagnostic."""

    code: str
    message: str
    row: int | None = None
    field: str | None = None

    def __post_init__(self) -> None:
        issues: list[str] = []
        if not isinstance(self.code, str) or not _ISSUE_CODE_RE.fullmatch(self.code):
            issues.append("code must be a lowercase hyphenated diagnostic identifier")
        if (
            not isinstance(self.message, str)
            or not self.message.strip()
            or len(self.message) > 1000
        ):
            issues.append("message must contain between 1 and 1000 characters")
        elif any(unicodedata.category(character) in {"Cc", "Cs"} for character in self.message):
            issues.append("message must be a single line without control characters")
        if self.row is not None and (
            isinstance(self.row, bool) or not isinstance(self.row, int) or self.row < 1
        ):
            issues.append("row must be a positive integer when supplied")
        if self.field is not None and (
            not isinstance(self.field, str) or not self.field or len(self.field) > 120
        ):
            issues.append("field must contain between 1 and 120 characters when supplied")
        if issues:
            raise ConfigError(issues)

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.row is not None:
            result["row"] = self.row
        if self.field is not None:
            result["field"] = self.field
        return result


@dataclass(frozen=True, slots=True)
class ImportedCampaign:
    """One validated campaign source and its intended plan time."""

    sequence: int
    source: str
    campaign: CampaignConfig
    intended_at: datetime | None = None

    def __post_init__(self) -> None:
        issues: list[str] = []
        if (
            isinstance(self.sequence, bool)
            or not isinstance(self.sequence, int)
            or not 1 <= self.sequence <= MAX_PLAN_IMPORT_ROWS
        ):
            issues.append(f"sequence must be between 1 and {MAX_PLAN_IMPORT_ROWS}")
        if not isinstance(self.source, str) or not _SOURCE_RE.fullmatch(self.source):
            issues.append("source must be a generated portable campaign JSON path")
        campaign_value: object = self.campaign
        if not isinstance(campaign_value, CampaignConfig):
            issues.append("campaign must be a CampaignConfig value")
        if self.intended_at is not None and (
            not isinstance(self.intended_at, datetime) or self.intended_at.utcoffset() is None
        ):
            issues.append("intended_at must include timezone information when supplied")
        if issues:
            raise ConfigError(issues)
        if self.intended_at is not None:
            object.__setattr__(self, "intended_at", self.intended_at.astimezone(timezone.utc))


@dataclass(frozen=True, slots=True)
class CampaignPlanImport:
    """A validated in-memory source package ready for exclusive export."""

    name: str
    required_platforms: tuple[str, ...]
    items: tuple[ImportedCampaign, ...]

    def __post_init__(self) -> None:
        issues: list[str] = []
        normalized_name = _single_line_name_value(self.name, issues=issues)
        try:
            required_platforms = tuple(self.required_platforms)
        except TypeError:
            issues.append("required_platforms must contain canonical platform names")
            required_platforms = ()
        expected_required = tuple(
            platform for platform in SUPPORTED_PLATFORMS if platform in required_platforms
        )
        if required_platforms != expected_required:
            issues.append("required_platforms must be unique and in canonical platform order")
        try:
            items = tuple(self.items)
        except TypeError:
            issues.append("items must contain ImportedCampaign values")
            items = ()
        if not 1 <= len(items) <= MAX_PLAN_IMPORT_ROWS:
            issues.append(f"items must contain between 1 and {MAX_PLAN_IMPORT_ROWS} campaigns")
        if any(not isinstance(item, ImportedCampaign) for item in items):
            issues.append("items must contain ImportedCampaign values")
        else:
            if tuple(item.sequence for item in items) != tuple(range(1, len(items) + 1)):
                issues.append("item sequences must be contiguous and ordered from 1")
            if len({item.source.casefold() for item in items}) != len(items):
                issues.append("item sources must be unique")
            for index, item in enumerate(items, start=1):
                for platform in required_platforms:
                    if platform not in item.campaign.platforms:
                        issues.append(f"item {index} does not request required platform {platform}")
        if issues:
            raise ConfigError(issues)
        object.__setattr__(self, "name", normalized_name)
        object.__setattr__(self, "required_platforms", required_platforms)
        object.__setattr__(self, "items", items)

    def plan_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "schemaVersion": 1,
            "name": self.name,
            "items": [
                {
                    "campaign": item.source,
                    **(
                        {"intendedAt": _format_utc(item.intended_at)}
                        if item.intended_at is not None
                        else {}
                    ),
                }
                for item in self.items
            ],
        }
        if self.required_platforms:
            result["requiredPlatforms"] = list(self.required_platforms)
        return result


@dataclass(frozen=True, slots=True)
class CampaignPlanImportCheck:
    """Machine-readable validation result with no filesystem side effects."""

    row_count: int
    issues: tuple[PlanImportIssue, ...]
    imported: CampaignPlanImport | None = None

    def __post_init__(self) -> None:
        validation: list[str] = []
        if (
            isinstance(self.row_count, bool)
            or not isinstance(self.row_count, int)
            or self.row_count < 0
        ):
            validation.append("row_count must be a non-negative integer")
        try:
            issues = tuple(self.issues)
        except TypeError:
            validation.append("issues must contain PlanImportIssue values")
            issues = ()
        if any(not isinstance(issue, PlanImportIssue) for issue in issues):
            validation.append("issues must contain PlanImportIssue values")
        if len(issues) > MAX_PLAN_IMPORT_ISSUES:
            validation.append(f"issues must contain at most {MAX_PLAN_IMPORT_ISSUES} diagnostics")
        imported_value: object = self.imported
        if imported_value is not None and not isinstance(imported_value, CampaignPlanImport):
            validation.append("imported must be a CampaignPlanImport value when supplied")
        if issues and self.imported is not None:
            validation.append("an invalid check cannot include an imported package")
        if not issues and self.imported is None:
            validation.append("a valid check must include an imported package")
        if validation:
            raise ConfigError(validation)
        object.__setattr__(self, "issues", issues)

    @property
    def valid(self) -> bool:
        return not self.issues and self.imported is not None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": 1,
            "artifactType": "plan-import-check",
            "valid": self.valid,
            "rowCount": self.row_count,
            "issues": [issue.to_dict() for issue in self.issues],
        }


def _single_line_name_value(value: object, *, issues: list[str]) -> str:
    if not isinstance(value, str):
        issues.append("name must be a string")
        return ""
    normalized = unicodedata.normalize("NFC", value).strip()
    if not normalized:
        issues.append("name must not be empty")
    elif len(normalized) > 120:
        issues.append("name must be at most 120 characters")
    if any(unicodedata.category(character) in {"Cc", "Cs"} for character in normalized):
        issues.append("name must be a single line without control characters")
    return normalized


def _single_line_name(value: object, *, issues: list[PlanImportIssue]) -> str:
    validation: list[str] = []
    normalized = _single_line_name_value(value, issues=validation)
    issues.extend(
        PlanImportIssue("invalid-plan-name", message, field="name") for message in validation
    )
    return normalized


def _required_platform_values(
    values: Sequence[str], *, issues: list[PlanImportIssue]
) -> tuple[str, ...]:
    normalized: set[str] = set()
    values_object: object = values
    candidates: tuple[object, ...]
    if isinstance(values_object, (str, bytes)) or not isinstance(values_object, Sequence):
        issues.append(
            PlanImportIssue(
                "invalid-required-platform",
                "required platforms must contain canonical platform names",
                field="requiredPlatforms",
            )
        )
        candidates = ()
    else:
        candidates = tuple(values_object)
    if len(candidates) > len(SUPPORTED_PLATFORMS):
        issues.append(
            PlanImportIssue(
                "too-many-required-platforms",
                f"required platforms must contain at most {len(SUPPORTED_PLATFORMS)} values",
                field="requiredPlatforms",
            )
        )
        candidates = candidates[: len(SUPPORTED_PLATFORMS)]
    for value in candidates:
        if not isinstance(value, str):
            issues.append(
                PlanImportIssue(
                    "invalid-required-platform",
                    "required platform must be a string",
                    field="requiredPlatforms",
                )
            )
            continue
        platform = value.strip().lower()
        if platform not in SUPPORTED_PLATFORMS:
            issues.append(
                PlanImportIssue(
                    "invalid-required-platform",
                    f"required platform must be one of: {', '.join(SUPPORTED_PLATFORMS)}",
                    field="requiredPlatforms",
                )
            )
        elif platform in normalized:
            issues.append(
                PlanImportIssue(
                    "duplicate-required-platform",
                    f"required platform duplicates {platform}",
                    field="requiredPlatforms",
                )
            )
        else:
            normalized.add(platform)
    return tuple(platform for platform in SUPPORTED_PLATFORMS if platform in normalized)


def _tokens(
    value: str,
    *,
    row: int,
    field: str,
    required: bool,
    maximum: int,
    issues: list[PlanImportIssue],
) -> list[str]:
    if not value.strip():
        if required:
            issues.append(
                PlanImportIssue("missing-field", f"{field} must not be empty", row=row, field=field)
            )
        return []
    raw_tokens = value.split("|", maximum)
    if len(raw_tokens) > maximum:
        issues.append(
            PlanImportIssue(
                "too-many-values",
                f"{field} must contain at most {maximum} values",
                row=row,
                field=field,
            )
        )
    tokens = [token.strip() for token in raw_tokens[:maximum]]
    if any(not token for token in tokens):
        issues.append(
            PlanImportIssue(
                "invalid-list",
                f"{field} must use non-empty values separated by |",
                row=row,
                field=field,
            )
        )
    return [token for token in tokens if token]


def _intended_at(value: str, *, row: int, issues: list[PlanImportIssue]) -> datetime | None:
    if not value.strip():
        return None
    candidate = value.strip()
    if candidate != value:
        issues.append(
            PlanImportIssue(
                "invalid-timestamp",
                "intended_at must not contain surrounding whitespace",
                row=row,
                field="intended_at",
            )
        )
        return None
    if not _RFC3339_RE.fullmatch(candidate):
        issues.append(
            PlanImportIssue(
                "invalid-timestamp",
                "intended_at must be an RFC 3339 date-time with an explicit offset or Z",
                row=row,
                field="intended_at",
            )
        )
        return None
    if candidate.endswith("-00:00"):
        issues.append(
            PlanImportIssue(
                "unknown-offset",
                "intended_at must use a known UTC offset instead of -00:00",
                row=row,
                field="intended_at",
            )
        )
        return None
    normalized = re.sub(
        r"\.(\d+)(?=Z|[+-]\d{2}:\d{2}$)",
        lambda match: "." + (match.group(1) + "000000")[:6],
        candidate,
    )
    try:
        return datetime.fromisoformat(normalized.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        issues.append(
            PlanImportIssue(
                "invalid-timestamp",
                "intended_at must be a valid date and time",
                row=row,
                field="intended_at",
            )
        )
        return None


def _campaign_issue_field(message: str) -> str | None:
    match = _ISSUE_FIELD_RE.match(message)
    if match is None:
        return None
    field = match.group(1)
    return field if len(field) <= 120 else None


def _bounded_issue_message(message: object) -> str:
    text = str(message)
    without_controls = "".join(
        " " if unicodedata.category(character) in {"Cc", "Cs"} else character for character in text
    )
    collapsed = " ".join(without_controls.split())
    return collapsed[:1000] if collapsed else "campaign validation failed"


def _campaign_from_row(
    values: dict[str, str],
    *,
    row: int,
    required_platforms: tuple[str, ...],
    issues: list[PlanImportIssue],
) -> tuple[CampaignConfig | None, datetime | None]:
    platforms = _tokens(
        values["platforms"],
        row=row,
        field="platforms",
        required=True,
        maximum=len(SUPPORTED_PLATFORMS),
        issues=issues,
    )
    hashtags = _tokens(
        values["hashtags"], row=row, field="hashtags", required=False, maximum=10, issues=issues
    )
    intended_at = _intended_at(values["intended_at"], row=row, issues=issues)
    campaign: dict[str, Any] = {
        "schemaVersion": 1,
        "name": values["name"],
        "body": values["body"],
        "hashtags": hashtags,
        "platforms": platforms,
    }
    for source_field in ("title", "link"):
        if values[source_field].strip():
            campaign[source_field] = values[source_field]

    media_path_value = values["media_path"]
    media_path = media_path_value.strip()
    media_alt_text = values["media_alt_text"].strip()
    media_platforms_value = values["media_platforms"]
    if media_path or media_alt_text or media_platforms_value.strip():
        if not media_path:
            issues.append(
                PlanImportIssue(
                    "incomplete-media",
                    "media_path is required when any media field is supplied",
                    row=row,
                    field="media_path",
                )
            )
        if not media_alt_text:
            issues.append(
                PlanImportIssue(
                    "incomplete-media",
                    "media_alt_text is required when media_path is supplied",
                    row=row,
                    field="media_alt_text",
                )
            )
        media: dict[str, Any] = {"path": media_path_value, "altText": media_alt_text}
        if media_platforms_value.strip():
            media["platforms"] = _tokens(
                media_platforms_value,
                row=row,
                field="media_platforms",
                required=False,
                maximum=len(SUPPORTED_PLATFORMS),
                issues=issues,
            )
        campaign["media"] = [media]

    try:
        normalized = CampaignConfig.from_dict(campaign)
    except ConfigError as error:
        issues.extend(
            PlanImportIssue(
                "invalid-campaign",
                _bounded_issue_message(message),
                row=row,
                field=_campaign_issue_field(message),
            )
            for message in error.issues
        )
        return None, intended_at

    for platform in required_platforms:
        if platform not in normalized.platforms:
            issues.append(
                PlanImportIssue(
                    "missing-required-platform",
                    f"campaign does not request required platform {platform}",
                    row=row,
                    field="platforms",
                )
            )
    return normalized, intended_at


def inspect_campaign_plan_csv(
    path: str | Path,
    *,
    name: str,
    required_platforms: Sequence[str] = (),
) -> CampaignPlanImportCheck:
    """Validate a bounded UTF-8 CSV completely without writing any output files."""
    source = Path(path)
    with source.open("rb") as handle:
        payload = handle.read(MAX_PLAN_IMPORT_BYTES + 1)
    if len(payload) > MAX_PLAN_IMPORT_BYTES:
        issue = PlanImportIssue(
            "file-too-large", f"CSV must be at most {MAX_PLAN_IMPORT_BYTES} bytes"
        )
        return CampaignPlanImportCheck(row_count=0, issues=(issue,))
    try:
        text = payload.decode("utf-8-sig")
    except UnicodeDecodeError:
        issue = PlanImportIssue("invalid-encoding", "CSV must be valid UTF-8")
        return CampaignPlanImportCheck(row_count=0, issues=(issue,))
    if not text:
        issue = PlanImportIssue("empty-file", "CSV must contain a header and at least one row")
        return CampaignPlanImportCheck(row_count=0, issues=(issue,))

    records: list[list[str]] = []
    try:
        reader = csv.reader(io.StringIO(text, newline=""), strict=True)
        for record in reader:
            records.append(record)
            if len(records) > MAX_PLAN_IMPORT_ROWS + 1:
                break
    except csv.Error as error:
        issue = PlanImportIssue("invalid-csv", f"CSV syntax is invalid: {error}")
        return CampaignPlanImportCheck(row_count=0, issues=(issue,))
    row_count = min(MAX_PLAN_IMPORT_ROWS + 1, max(0, len(records) - 1))
    issues: list[PlanImportIssue] = []
    normalized_name = _single_line_name(name, issues=issues)
    normalized_required = _required_platform_values(required_platforms, issues=issues)
    if tuple(records[0]) != PLAN_IMPORT_FIELDS:
        issues.append(
            PlanImportIssue(
                "invalid-header",
                "CSV header must exactly match: " + ",".join(PLAN_IMPORT_FIELDS),
                row=1,
            )
        )
        return CampaignPlanImportCheck(row_count=row_count, issues=tuple(issues))
    if row_count == 0:
        issues.append(PlanImportIssue("missing-rows", "CSV must contain at least one data row"))
    if row_count > MAX_PLAN_IMPORT_ROWS:
        issues.append(
            PlanImportIssue(
                "too-many-rows", f"CSV must contain at most {MAX_PLAN_IMPORT_ROWS} data rows"
            )
        )

    imported_items: list[ImportedCampaign] = []
    for record_index, record in enumerate(records[1 : MAX_PLAN_IMPORT_ROWS + 1], start=2):
        if not record or all(not value.strip() for value in record):
            issues.append(
                PlanImportIssue("blank-row", "blank rows are not allowed", row=record_index)
            )
            continue
        if len(record) != len(PLAN_IMPORT_FIELDS):
            issues.append(
                PlanImportIssue(
                    "invalid-row-shape",
                    f"row must contain exactly {len(PLAN_IMPORT_FIELDS)} fields",
                    row=record_index,
                )
            )
            continue
        values = dict(zip(PLAN_IMPORT_FIELDS, record, strict=True))
        campaign, intended_at = _campaign_from_row(
            values,
            row=record_index,
            required_platforms=normalized_required,
            issues=issues,
        )
        if campaign is not None:
            slug = _slugify(campaign.name)
            source_name = f"campaigns/{record_index - 1:03d}-{slug}.json"
            if not _SOURCE_RE.fullmatch(source_name):
                issues.append(
                    PlanImportIssue(
                        "invalid-campaign-source",
                        "campaign name cannot produce a portable source filename",
                        row=record_index,
                        field="name",
                    )
                )
                continue
            imported_items.append(
                ImportedCampaign(
                    sequence=record_index - 1,
                    source=source_name,
                    campaign=campaign,
                    intended_at=intended_at,
                )
            )

    if len(issues) > MAX_PLAN_IMPORT_ISSUES:
        issues = issues[: MAX_PLAN_IMPORT_ISSUES - 1]
        issues.append(
            PlanImportIssue(
                "issue-limit",
                f"additional diagnostics omitted after {MAX_PLAN_IMPORT_ISSUES - 1} issues",
            )
        )
    if issues:
        return CampaignPlanImportCheck(row_count=row_count, issues=tuple(issues))
    imported = CampaignPlanImport(
        name=normalized_name,
        required_platforms=normalized_required,
        items=tuple(imported_items),
    )
    return CampaignPlanImportCheck(row_count=row_count, issues=(), imported=imported)


def _clear_temporary_import(path: Path, identity: tuple[int, int, int, int]) -> None:
    if not path.exists():
        return
    require_directory_identity(path, identity, label="import directory")
    expected = {"campaigns", "plan.json"}
    for child in path.iterdir():
        if child.name not in expected:
            raise OSError(f"refusing to clean unexpected import entry: {child}")
    campaigns = path / "campaigns"
    if campaigns.exists():
        if is_link_like(campaigns) or not campaigns.is_dir():
            raise OSError(f"refusing to clean invalid campaign directory: {campaigns}")
        campaigns_identity = directory_identity(campaigns, label="import campaign directory")
        for campaign in campaigns.iterdir():
            require_directory_identity(path, identity, label="import directory")
            require_directory_identity(
                campaigns, campaigns_identity, label="import campaign directory"
            )
            if is_link_like(campaign) or not campaign.is_file() or campaign.suffix != ".json":
                raise OSError(f"refusing to clean unexpected campaign entry: {campaign}")
            campaign.unlink()
        campaigns.rmdir()
    plan = path / "plan.json"
    if plan.exists():
        require_directory_identity(path, identity, label="import directory")
        if is_link_like(plan) or not plan.is_file():
            raise OSError(f"refusing to clean invalid plan entry: {plan}")
        plan.unlink()
    path.rmdir()


def _publish_import_stage(
    stage: Path, target: Path, target_identity: tuple[int, int, int, int]
) -> None:
    """Publish a validated stage into an exclusively reserved destination."""
    campaign_target = target / "campaigns"
    require_directory_identity(target, target_identity, label="import output")
    campaign_target.mkdir(mode=0o700)
    campaign_identity = directory_identity(campaign_target, label="import campaign output")
    for source in sorted((stage / "campaigns").iterdir(), key=lambda path: path.name):
        require_directory_identity(target, target_identity, label="import output")
        require_directory_identity(
            campaign_target, campaign_identity, label="import campaign output"
        )
        destination = campaign_target / source.name
        with source.open("rb") as source_handle, destination.open("xb") as target_handle:
            target_handle.write(source_handle.read())
    require_directory_identity(target, target_identity, label="import output")
    with (
        (stage / "plan.json").open("rb") as source_handle,
        (target / "plan.json").open("xb") as target_handle,
    ):
        target_handle.write(source_handle.read())


def export_campaign_plan_import(imported: CampaignPlanImport, output: str | Path) -> Path:
    """Write a complete source package exclusively and return its plan path."""
    imported_value: object = imported
    if not isinstance(imported_value, CampaignPlanImport):
        raise ConfigError("imported must be a CampaignPlanImport value")
    target = Path(os.path.abspath(output))
    parent = target.parent
    parent.mkdir(parents=True, exist_ok=True)
    if is_link_like(parent):
        raise OSError(f"import output parent is link-like: {parent}")
    parent_identity = directory_identity(parent, label="import output parent")

    temporary = parent / f".{target.name}.{uuid.uuid4().hex}.tmp"
    require_directory_identity(parent, parent_identity, label="import output parent")
    temporary.mkdir(mode=0o700)
    temporary_identity = directory_identity(temporary, label="import staging directory")
    try:
        campaign_directory = temporary / "campaigns"
        campaign_directory.mkdir(mode=0o700)
        for item in imported.items:
            destination = temporary / Path(*item.source.split("/"))
            destination.write_text(
                json.dumps(item.campaign.to_dict(), ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
                newline="\n",
            )
        plan_path = temporary / "plan.json"
        plan_path.write_text(
            json.dumps(imported.plan_dict(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        validated: CampaignPlan = load_campaign_plan(plan_path)
        if len(validated.items) != len(imported.items):
            raise OSError("import validation produced an unexpected item count")
        try:
            require_directory_identity(parent, parent_identity, label="import output parent")
            target.mkdir(mode=0o700)
        except FileExistsError as error:
            raise FileExistsError(
                f"refusing to overwrite existing import output: {target}"
            ) from error
        target_identity = directory_identity(target, label="import output")
        try:
            _publish_import_stage(temporary, target, target_identity)
        except Exception:
            _clear_temporary_import(target, target_identity)
            raise
        _clear_temporary_import(temporary, temporary_identity)
    except Exception:
        if temporary.exists():
            _clear_temporary_import(temporary, temporary_identity)
        raise
    return target / "plan.json"
