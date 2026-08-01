# Copyright (c) 2026 Samsarix LLC
# SPDX-License-Identifier: MPL-2.0

"""Campaign loading, deterministic preview, and safe local export."""

from __future__ import annotations

import hashlib
import json
import os
import unicodedata
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .formatters import format_platform
from .models import CampaignBundle, CampaignConfig, ConfigError

MAX_CONFIG_BYTES = 1_000_000
MAX_JSON_NESTING = 100


def _reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ConfigError(f"duplicate JSON field: {key}")
        result[key] = value
    return result


def _ensure_bounded_json_nesting(text: str) -> None:
    """Reject deeply nested containers before parser behavior can vary by Python version."""
    depth = 0
    in_string = False
    escaped = False
    for character in text:
        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
            continue
        if character == '"':
            in_string = True
        elif character in "[{":
            depth += 1
            if depth > MAX_JSON_NESTING:
                raise ConfigError("campaign JSON nesting is too deep")
        elif character in "]}":
            depth -= 1


def load_campaign(path: str | Path) -> CampaignConfig:
    """Load a UTF-8 JSON campaign file with bounded input size."""
    config_path = Path(path)
    try:
        size = config_path.stat().st_size
    except OSError as error:
        raise ConfigError(f"cannot read campaign file: {error}") from error
    if size > MAX_CONFIG_BYTES:
        raise ConfigError(f"campaign file exceeds the {MAX_CONFIG_BYTES}-byte limit")
    if not config_path.is_file():
        raise ConfigError("campaign path must be a file")

    try:
        text = config_path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError) as error:
        raise ConfigError(f"cannot read campaign file as UTF-8: {error}") from error
    _ensure_bounded_json_nesting(text)
    try:
        raw = json.loads(text, object_pairs_hook=_reject_duplicate_json_keys)
    except json.JSONDecodeError as error:
        raise ConfigError(
            f"invalid JSON at line {error.lineno}, column {error.colno}: {error.msg}"
        ) from error
    except RecursionError as error:
        raise ConfigError("campaign JSON nesting is too deep") from error
    if not isinstance(raw, dict):
        raise ConfigError("campaign configuration must be a JSON object")
    return CampaignConfig.from_dict(raw)


def _canonical_source(config: CampaignConfig) -> bytes:
    return json.dumps(
        config.to_dict(),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def build_campaign(config: CampaignConfig | dict[str, Any]) -> CampaignBundle:
    """Build deterministic, copy-ready drafts without network or file side effects."""
    normalized = config if isinstance(config, CampaignConfig) else CampaignConfig.from_dict(config)
    source_hash = hashlib.sha256(_canonical_source(normalized)).hexdigest()
    drafts = tuple(format_platform(normalized, platform) for platform in normalized.platforms)
    return CampaignBundle(
        campaign_id=f"scs_{source_hash[:12]}",
        source_hash=source_hash,
        name=normalized.name,
        drafts=drafts,
    )


def _slugify(value: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    cleaned = "".join(char.lower() if char.isalnum() else "-" for char in ascii_value)
    slug = "-".join(part for part in cleaned.split("-") if part)[:60].strip("-")
    return slug or "campaign"


def _manifest(bundle: CampaignBundle, exported_at: datetime) -> dict[str, Any]:
    drafts: list[dict[str, Any]] = []
    for draft in bundle.drafts:
        drafts.append(
            {
                "platform": draft.platform,
                "file": f"{draft.platform}.md",
                "characterCount": draft.character_count,
                "originalCharacterCount": draft.original_character_count,
                "characterLimit": draft.character_limit,
                "truncated": draft.truncated,
                "warnings": list(draft.warnings),
            }
        )
    return {
        "schemaVersion": 1,
        "campaignId": bundle.campaign_id,
        "sourceHash": bundle.source_hash,
        "name": bundle.name,
        "exportedAt": exported_at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "drafts": drafts,
    }


def _clear_temp_directory(path: Path) -> None:
    if not path.exists():
        return
    for child in path.iterdir():
        if child.is_file() and not child.is_symlink():
            child.unlink()
        else:
            raise OSError(f"refusing to clean unexpected temporary entry: {child}")
    path.rmdir()


def export_campaign(
    bundle: CampaignBundle,
    output_root: str | Path = "outbox",
    *,
    overwrite: bool = False,
    exported_at: datetime | None = None,
) -> Path:
    """Persist a bundle beneath a generated safe path and return that path."""
    root = Path(output_root).resolve()
    if root.exists() and root.is_symlink():
        raise OSError(f"refusing to export through a symbolic-link directory: {root}")
    root.mkdir(parents=True, exist_ok=True)
    if not root.is_dir():
        raise OSError(f"output root is not a directory: {root}")

    bundle_name = f"{_slugify(bundle.name)}-{bundle.campaign_id}"
    target = root / bundle_name
    if target.exists() or target.is_symlink():
        if target.is_symlink() or not target.is_dir():
            raise OSError(f"refusing to overwrite non-directory bundle path: {target}")
        if not overwrite:
            raise FileExistsError(
                f"bundle already exists: {target}; pass --overwrite to replace it"
            )

    temporary = root / f".{bundle_name}.{uuid.uuid4().hex}.tmp"
    temporary.mkdir(mode=0o700)
    try:
        for draft in bundle.drafts:
            (temporary / f"{draft.platform}.md").write_text(
                f"{draft.content}\n",
                encoding="utf-8",
                newline="\n",
            )
        manifest = _manifest(bundle, exported_at or datetime.now(timezone.utc))
        (temporary / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )

        if not target.exists():
            temporary.replace(target)
        else:
            draft_files = sorted(
                path for path in temporary.iterdir() if path.name != "manifest.json"
            )
            for source in draft_files:
                os.replace(source, target / source.name)
            os.replace(temporary / "manifest.json", target / "manifest.json")
            temporary.rmdir()
    finally:
        _clear_temp_directory(temporary)
    return target
