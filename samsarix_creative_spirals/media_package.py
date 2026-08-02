# Copyright (c) 2026 Samsarix LLC
# SPDX-License-Identifier: MPL-2.0

"""Approval-bound, bounded image payloads for offline campaign handoffs."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import struct
import unicodedata
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import (
    ConfigError,
    SUPPORTED_PLATFORMS,
    _portable_media_path,
)
from .plans import CampaignPlanBundle
from .workflow import MAX_CONFIG_BYTES, _load_json_object

MAX_PACKAGED_MEDIA_ASSETS = 400
MAX_PACKAGED_MEDIA_FILE_BYTES = 2_000_000
MAX_PACKAGED_MEDIA_TOTAL_BYTES = 100_000_000
MAX_PACKAGED_MEDIA_PIXELS = 36_152_319

_MEDIA_BINDING_KEYS = {"mediaId", "mediaHash", "assetCount", "totalBytes"}
_MEDIA_INDEX_KEYS = {
    "schemaVersion",
    "contract",
    "mediaId",
    "mediaHash",
    "planId",
    "sourceHash",
    "totalBytes",
    "assets",
}
_MEDIA_ASSET_KEYS = {
    "sequence",
    "source",
    "reference",
    "packetPath",
    "contentType",
    "width",
    "height",
    "bytes",
    "sha256",
    "altText",
    "platforms",
}
_MEDIA_ID_RE = re.compile(r"^scm_[0-9a-f]{12}$")
_PLAN_ID_RE = re.compile(r"^scp_[0-9a-f]{12}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_PACKET_PATH_RE = re.compile(r"^media/([0-9a-f]{64})\.(jpg|png)$")
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_JPEG_SOF_MARKERS = {
    0xC0,
    0xC1,
    0xC2,
    0xC3,
    0xC5,
    0xC6,
    0xC7,
    0xC9,
    0xCA,
    0xCB,
    0xCD,
    0xCE,
    0xCF,
}


@dataclass(frozen=True, slots=True)
class CampaignPlanMediaBinding:
    """Compact approval binding for one exact campaign-plan media snapshot."""

    media_id: str
    media_hash: str
    asset_count: int
    total_bytes: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "mediaId": self.media_id,
            "mediaHash": self.media_hash,
            "assetCount": self.asset_count,
            "totalBytes": self.total_bytes,
        }

    @classmethod
    def from_dict(
        cls,
        value: object,
        *,
        field: str,
        issues: list[str],
    ) -> CampaignPlanMediaBinding | None:
        if not isinstance(value, dict):
            issues.append(f"{field} must be an object")
            return None
        unknown = sorted(str(key) for key in value if key not in _MEDIA_BINDING_KEYS)
        if unknown:
            issues.append(f"{field} has unknown field(s): {', '.join(unknown)}")
        media_id_value = value.get("mediaId")
        media_id = media_id_value if isinstance(media_id_value, str) else ""
        if not _MEDIA_ID_RE.fullmatch(media_id):
            issues.append(f"{field}.mediaId must be a Samsarix media ID")
        media_hash_value = value.get("mediaHash")
        media_hash = media_hash_value if isinstance(media_hash_value, str) else ""
        if not _SHA256_RE.fullmatch(media_hash):
            issues.append(f"{field}.mediaHash must be a lowercase SHA-256 hash")
        asset_count = _bounded_integer(
            value.get("assetCount"),
            field=f"{field}.assetCount",
            minimum=1,
            maximum=MAX_PACKAGED_MEDIA_ASSETS,
            issues=issues,
        )
        total_bytes = _bounded_integer(
            value.get("totalBytes"),
            field=f"{field}.totalBytes",
            minimum=1,
            maximum=MAX_PACKAGED_MEDIA_TOTAL_BYTES,
            issues=issues,
        )
        return cls(media_id, media_hash, asset_count, total_bytes)


@dataclass(frozen=True, slots=True)
class CampaignPlanMediaAsset:
    """One campaign media reference bound to one exact packet image."""

    sequence: int
    source: str
    reference: str
    packet_path: str
    content_type: str
    width: int
    height: int
    size: int
    sha256: str
    alt_text: str
    platforms: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "sequence": self.sequence,
            "source": self.source,
            "reference": self.reference,
            "packetPath": self.packet_path,
            "contentType": self.content_type,
            "width": self.width,
            "height": self.height,
            "bytes": self.size,
            "sha256": self.sha256,
            "altText": self.alt_text,
            "platforms": list(self.platforms),
        }


@dataclass(frozen=True, slots=True)
class CampaignPlanMedia:
    """Normalized index for exact static images attached to one campaign plan."""

    media_id: str
    media_hash: str
    plan_id: str
    source_hash: str
    total_bytes: int
    assets: tuple[CampaignPlanMediaAsset, ...]

    @property
    def binding(self) -> CampaignPlanMediaBinding:
        return CampaignPlanMediaBinding(
            media_id=self.media_id,
            media_hash=self.media_hash,
            asset_count=len(self.assets),
            total_bytes=self.total_bytes,
        )

    def _core_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": 1,
            "contract": "samsarix.handoff-media",
            "planId": self.plan_id,
            "sourceHash": self.source_hash,
            "totalBytes": self.total_bytes,
            "assets": [asset.to_dict() for asset in self.assets],
        }

    def to_dict(self) -> dict[str, Any]:
        core = self._core_dict()
        return {
            "schemaVersion": 1,
            "contract": "samsarix.handoff-media",
            "mediaId": self.media_id,
            "mediaHash": self.media_hash,
            "planId": core["planId"],
            "sourceHash": core["sourceHash"],
            "totalBytes": core["totalBytes"],
            "assets": core["assets"],
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> CampaignPlanMedia:
        issues: list[str] = []
        unknown = sorted(str(key) for key in raw if key not in _MEDIA_INDEX_KEYS)
        if unknown:
            issues.append(f"unknown media index field(s): {', '.join(unknown)}")
        if raw.get("schemaVersion") != 1 or isinstance(raw.get("schemaVersion"), bool):
            issues.append("schemaVersion must be 1")
        if raw.get("contract") != "samsarix.handoff-media":
            issues.append("contract must be samsarix.handoff-media")

        media_id_value = raw.get("mediaId")
        media_id = media_id_value if isinstance(media_id_value, str) else ""
        if not _MEDIA_ID_RE.fullmatch(media_id):
            issues.append("mediaId must be a Samsarix media ID")
        media_hash_value = raw.get("mediaHash")
        media_hash = media_hash_value if isinstance(media_hash_value, str) else ""
        if not _SHA256_RE.fullmatch(media_hash):
            issues.append("mediaHash must be a lowercase SHA-256 hash")
        plan_id_value = raw.get("planId")
        plan_id = plan_id_value if isinstance(plan_id_value, str) else ""
        if not _PLAN_ID_RE.fullmatch(plan_id):
            issues.append("planId must be a Samsarix campaign plan ID")
        source_hash_value = raw.get("sourceHash")
        source_hash = source_hash_value if isinstance(source_hash_value, str) else ""
        if not _SHA256_RE.fullmatch(source_hash):
            issues.append("sourceHash must be a lowercase SHA-256 hash")
        total_bytes = _bounded_integer(
            raw.get("totalBytes"),
            field="totalBytes",
            minimum=1,
            maximum=MAX_PACKAGED_MEDIA_TOTAL_BYTES,
            issues=issues,
        )

        assets_value = raw.get("assets")
        assets: list[CampaignPlanMediaAsset] = []
        if not isinstance(assets_value, list):
            issues.append("assets must be a non-empty array")
        else:
            if not 1 <= len(assets_value) <= MAX_PACKAGED_MEDIA_ASSETS:
                issues.append(
                    f"assets must contain between 1 and {MAX_PACKAGED_MEDIA_ASSETS} items"
                )
            for index, value in enumerate(assets_value[:MAX_PACKAGED_MEDIA_ASSETS]):
                asset = _parse_media_asset(value, field=f"assets[{index}]", issues=issues)
                if asset is not None:
                    assets.append(asset)

        _validate_asset_set(assets, total_bytes=total_bytes, issues=issues)
        candidate = cls(media_id, media_hash, plan_id, source_hash, total_bytes, tuple(assets))
        expected_hash = hashlib.sha256(_canonical_media_core(candidate._core_dict())).hexdigest()
        if media_hash and media_hash != expected_hash:
            issues.append("mediaHash does not match canonical media index content")
        if media_id and media_id != f"scm_{expected_hash[:12]}":
            issues.append("mediaId does not match mediaHash")
        if issues:
            raise ConfigError(issues)
        return candidate


@dataclass(frozen=True, slots=True)
class CollectedCampaignPlanMedia:
    """One normalized media index plus immutable captured file payloads."""

    index: CampaignPlanMedia
    files: tuple[tuple[str, bytes], ...]

    def payloads(self) -> dict[str, bytes]:
        return dict(self.files)


def _bounded_integer(
    value: object,
    *,
    field: str,
    minimum: int,
    maximum: int,
    issues: list[str],
) -> int:
    parsed = value if isinstance(value, int) and not isinstance(value, bool) else 0
    if not minimum <= parsed <= maximum:
        issues.append(f"{field} must be between {minimum} and {maximum}")
    return parsed


def _portable_index_path(value: object, *, field: str, suffix: str, issues: list[str]) -> str:
    if not isinstance(value, str):
        issues.append(f"{field} must be a portable relative {suffix} path")
        return ""
    normalized = unicodedata.normalize("NFC", value)
    path = normalized.strip()
    segments = path.split("/")
    if (
        not path
        or normalized != path
        or len(path) > 500
        or "\\" in path
        or ":" in path
        or any(character in '<>"|?*' for character in path)
        or any(unicodedata.category(character) in {"Cc", "Cs"} for character in path)
        or path.startswith("/")
        or any(
            segment in {"", ".", ".."}
            or segment != segment.strip()
            or segment.endswith(".")
            or len(segment) > 100
            for segment in segments
        )
        or not path.endswith(suffix)
    ):
        issues.append(f"{field} must be a portable relative {suffix} path")
    return path


def _parse_media_asset(
    value: object,
    *,
    field: str,
    issues: list[str],
) -> CampaignPlanMediaAsset | None:
    if not isinstance(value, dict):
        issues.append(f"{field} must be an object")
        return None
    unknown = sorted(str(key) for key in value if key not in _MEDIA_ASSET_KEYS)
    if unknown:
        issues.append(f"{field} has unknown field(s): {', '.join(unknown)}")
    sequence = _bounded_integer(
        value.get("sequence"), field=f"{field}.sequence", minimum=1, maximum=100, issues=issues
    )
    source = _portable_index_path(
        value.get("source"), field=f"{field}.source", suffix=".json", issues=issues
    )
    reference = (
        _portable_media_path(value.get("reference"), field=f"{field}.reference", issues=issues)
        or ""
    )

    packet_path_value = value.get("packetPath")
    packet_path = packet_path_value if isinstance(packet_path_value, str) else ""
    packet_match = _PACKET_PATH_RE.fullmatch(packet_path)
    if packet_match is None:
        issues.append(f"{field}.packetPath must be a content-addressed media path")
    content_type_value = value.get("contentType")
    content_type = content_type_value if isinstance(content_type_value, str) else ""
    if content_type not in {"image/jpeg", "image/png"}:
        issues.append(f"{field}.contentType must be image/jpeg or image/png")
    width = _bounded_integer(
        value.get("width"), field=f"{field}.width", minimum=1, maximum=100_000, issues=issues
    )
    height = _bounded_integer(
        value.get("height"), field=f"{field}.height", minimum=1, maximum=100_000, issues=issues
    )
    if width * height > MAX_PACKAGED_MEDIA_PIXELS:
        issues.append(f"{field} dimensions must contain at most {MAX_PACKAGED_MEDIA_PIXELS} pixels")
    size = _bounded_integer(
        value.get("bytes"),
        field=f"{field}.bytes",
        minimum=1,
        maximum=MAX_PACKAGED_MEDIA_FILE_BYTES,
        issues=issues,
    )
    digest_value = value.get("sha256")
    digest = digest_value if isinstance(digest_value, str) else ""
    if not _SHA256_RE.fullmatch(digest):
        issues.append(f"{field}.sha256 must be a lowercase SHA-256 hash")
    if packet_match is not None:
        if packet_match.group(1) != digest:
            issues.append(f"{field}.packetPath digest must match sha256")
        expected_suffix = "jpg" if content_type == "image/jpeg" else "png"
        if packet_match.group(2) != expected_suffix:
            issues.append(f"{field}.packetPath suffix must match contentType")
    alt_text_value = value.get("altText")
    alt_text = alt_text_value if isinstance(alt_text_value, str) else ""
    if not 1 <= len(alt_text) <= 1_000 or any(char in "\r\n" for char in alt_text):
        issues.append(f"{field}.altText must contain 1 to 1000 single-line characters")
    platforms_value = value.get("platforms")
    platforms: list[str] = []
    if not isinstance(platforms_value, list) or not platforms_value:
        issues.append(f"{field}.platforms must be a non-empty array")
    else:
        for platform in platforms_value:
            if not isinstance(platform, str) or platform not in SUPPORTED_PLATFORMS:
                issues.append(f"{field}.platforms must contain only supported platforms")
            elif platform in platforms:
                issues.append(f"{field}.platforms must not contain duplicates")
            else:
                platforms.append(platform)
    return CampaignPlanMediaAsset(
        sequence,
        source,
        reference,
        packet_path,
        content_type,
        width,
        height,
        size,
        digest,
        alt_text,
        tuple(platforms),
    )


def _validate_asset_set(
    assets: list[CampaignPlanMediaAsset],
    *,
    total_bytes: int,
    issues: list[str],
) -> None:
    references: set[tuple[int, str]] = set()
    packets: dict[str, tuple[int, str, int, int, str]] = {}
    for asset in assets:
        key = (asset.sequence, asset.reference.casefold())
        if key in references:
            issues.append("assets must not repeat a reference within one plan item")
        references.add(key)
        descriptor = (asset.size, asset.content_type, asset.width, asset.height, asset.sha256)
        previous = packets.get(asset.packet_path)
        if previous is not None and previous != descriptor:
            issues.append("assets sharing packetPath must declare identical file metadata")
        packets[asset.packet_path] = descriptor
    expected_total = sum(descriptor[0] for descriptor in packets.values())
    if total_bytes != expected_total:
        issues.append("totalBytes must equal the sum of unique packaged media files")


def _canonical_media_core(core: dict[str, Any]) -> bytes:
    return json.dumps(core, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )


def _png_dimensions(payload: bytes) -> tuple[int, int]:
    if not payload.startswith(_PNG_SIGNATURE):
        raise ConfigError("file content does not match its PNG suffix")
    position = len(_PNG_SIGNATURE)
    width = height = 0
    saw_idat = False
    saw_iend = False
    chunk_index = 0
    while position < len(payload):
        if position + 12 > len(payload):
            raise ConfigError("PNG contains a truncated chunk")
        length = struct.unpack(">I", payload[position : position + 4])[0]
        chunk_type = payload[position + 4 : position + 8]
        end = position + 12 + length
        if end > len(payload):
            raise ConfigError("PNG contains a truncated chunk payload")
        data = payload[position + 8 : position + 8 + length]
        declared_crc = struct.unpack(">I", payload[position + 8 + length : end])[0]
        if zlib.crc32(chunk_type + data) & 0xFFFFFFFF != declared_crc:
            raise ConfigError("PNG contains an invalid chunk checksum")
        if chunk_index == 0:
            if chunk_type != b"IHDR" or length != 13:
                raise ConfigError("PNG must begin with one 13-byte IHDR chunk")
            width, height = struct.unpack(">II", data[:8])
        elif chunk_type == b"IHDR":
            raise ConfigError("PNG contains more than one IHDR chunk")
        if chunk_type == b"acTL":
            raise ConfigError("animated PNG is outside the static-image contract")
        if chunk_type == b"IDAT":
            saw_idat = True
        if chunk_type == b"IEND":
            if length != 0 or end != len(payload):
                raise ConfigError("PNG IEND must be empty and terminate the file")
            saw_iend = True
            break
        position = end
        chunk_index += 1
    if not width or not height or not saw_idat or not saw_iend:
        raise ConfigError("PNG must contain dimensions, image data, and a terminal IEND chunk")
    return width, height


def _jpeg_dimensions(payload: bytes) -> tuple[int, int]:
    if len(payload) < 4 or not payload.startswith(b"\xff\xd8"):
        raise ConfigError("file content does not match its JPEG suffix")
    if not payload.endswith(b"\xff\xd9"):
        raise ConfigError("JPEG must end at its EOI marker")
    position = 2
    dimensions: tuple[int, int] | None = None
    while position < len(payload) - 2:
        if payload[position] != 0xFF:
            raise ConfigError("JPEG marker stream is malformed before image data")
        while position < len(payload) and payload[position] == 0xFF:
            position += 1
        if position >= len(payload):
            break
        marker = payload[position]
        position += 1
        if marker == 0xD9:
            break
        if marker == 0xDA:
            if dimensions is None:
                raise ConfigError("JPEG does not declare dimensions before image data")
            if position + 2 > len(payload):
                raise ConfigError("JPEG contains a truncated scan header")
            length = struct.unpack(">H", payload[position : position + 2])[0]
            if length < 2 or position + length > len(payload) - 2:
                raise ConfigError("JPEG contains an invalid scan header")
            return dimensions
        if marker == 0x00 or marker == 0xD8 or marker == 0x01 or 0xD0 <= marker <= 0xD7:
            continue
        if position + 2 > len(payload):
            raise ConfigError("JPEG contains a truncated marker length")
        length = struct.unpack(">H", payload[position : position + 2])[0]
        if length < 2 or position + length > len(payload):
            raise ConfigError("JPEG contains an invalid marker length")
        if marker in _JPEG_SOF_MARKERS:
            if length < 8:
                raise ConfigError("JPEG frame header is too short")
            height, width = struct.unpack(">HH", payload[position + 3 : position + 7])
            if not width or not height:
                raise ConfigError("JPEG dimensions must be positive")
            dimensions = (width, height)
        position += length
    raise ConfigError("JPEG does not contain a supported frame and scan header")


def inspect_static_image(payload: bytes, *, suffix: str) -> tuple[str, int, int, str]:
    """Validate one bounded static JPEG/PNG payload and return normalized metadata."""
    normalized = suffix.casefold()
    if normalized == ".png":
        content_type = "image/png"
        width, height = _png_dimensions(payload)
        packet_suffix = "png"
    elif normalized in {".jpg", ".jpeg"}:
        content_type = "image/jpeg"
        width, height = _jpeg_dimensions(payload)
        packet_suffix = "jpg"
    else:
        raise ConfigError("packaged media must use a .jpg, .jpeg, or .png suffix")
    if width * height > MAX_PACKAGED_MEDIA_PIXELS:
        raise ConfigError(
            f"image contains {width * height} pixels; maximum is {MAX_PACKAGED_MEDIA_PIXELS}"
        )
    return content_type, width, height, packet_suffix


def _ensure_no_symlink_components(root: Path, segments: tuple[str, ...], *, field: str) -> Path:
    candidate = root
    for segment in segments:
        candidate = candidate / segment
        if candidate.is_symlink():
            raise ConfigError(f"{field} traverses a symbolic link: {candidate}")
    return candidate


def _read_stable_media_file(path: Path, *, field: str) -> bytes:
    try:
        named_before = os.stat(path, follow_symlinks=False)
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(path, flags)
        try:
            opened_before = os.fstat(descriptor)
            if not stat.S_ISREG(opened_before.st_mode):
                raise ConfigError(f"{field} must resolve to a regular file")
            named_identity = (named_before.st_dev, named_before.st_ino)
            opened_identity = (opened_before.st_dev, opened_before.st_ino)
            if named_identity != opened_identity:
                raise ConfigError(f"{field} changed while it was being opened")
            if not 1 <= opened_before.st_size <= MAX_PACKAGED_MEDIA_FILE_BYTES:
                raise ConfigError(
                    f"{field} must contain between 1 and {MAX_PACKAGED_MEDIA_FILE_BYTES} bytes"
                )
            with os.fdopen(descriptor, "rb", closefd=False) as handle:
                payload = handle.read(MAX_PACKAGED_MEDIA_FILE_BYTES + 1)
            opened_after = os.fstat(descriptor)
        finally:
            os.close(descriptor)
        named_after = os.stat(path, follow_symlinks=False)
    except ConfigError:
        raise
    except OSError as error:
        raise ConfigError(f"cannot read {field}: {error}") from error
    before_identity = (
        opened_before.st_dev,
        opened_before.st_ino,
        opened_before.st_size,
        opened_before.st_mtime_ns,
    )
    after_identity = (
        opened_after.st_dev,
        opened_after.st_ino,
        opened_after.st_size,
        opened_after.st_mtime_ns,
    )
    named_after_identity = (named_after.st_dev, named_after.st_ino)
    if before_identity != after_identity or named_identity != named_after_identity:
        raise ConfigError(f"{field} changed while it was being read")
    if len(payload) != opened_before.st_size:
        raise ConfigError(f"{field} size changed while it was being read")
    return payload


def collect_campaign_plan_media(
    bundle: CampaignPlanBundle,
    plan_root: str | Path,
) -> CollectedCampaignPlanMedia:
    """Capture exact, bounded campaign-relative images beneath one trusted plan root."""
    root_input = Path(os.path.abspath(plan_root))
    if root_input.is_symlink() or not root_input.is_dir():
        raise ConfigError("plan_root must be a non-symbolic-link directory")
    root = root_input.resolve()
    assets: list[CampaignPlanMediaAsset] = []
    files: dict[str, bytes] = {}
    total_bytes = 0
    for item in bundle.items:
        source_segments = tuple(item.source.split("/"))
        campaign_path = _ensure_no_symlink_components(
            root, source_segments, field=f"item {item.sequence} campaign source"
        )
        campaign_root = campaign_path.parent.resolve()
        if not campaign_root.is_relative_to(root):
            raise ConfigError(f"item {item.sequence} campaign directory escapes plan_root")
        for index, reference in enumerate(item.bundle.media):
            field = f"item {item.sequence} media[{index}]"
            reference_segments = tuple(reference.path.split("/"))
            media_path = _ensure_no_symlink_components(
                campaign_root, reference_segments, field=field
            )
            resolved = media_path.resolve(strict=False)
            if not resolved.is_relative_to(campaign_root):
                raise ConfigError(f"{field} resolves outside its campaign directory")
            payload = _read_stable_media_file(media_path, field=field)
            content_type, width, height, packet_suffix = inspect_static_image(
                payload, suffix=media_path.suffix
            )
            digest = hashlib.sha256(payload).hexdigest()
            packet_path = f"media/{digest}.{packet_suffix}"
            existing = files.get(packet_path)
            if existing is not None and existing != payload:
                raise ConfigError(f"{field} collides with a different packaged payload")
            if existing is None:
                total_bytes += len(payload)
                if total_bytes > MAX_PACKAGED_MEDIA_TOTAL_BYTES:
                    raise ConfigError(
                        "packaged media exceeds the "
                        f"{MAX_PACKAGED_MEDIA_TOTAL_BYTES}-byte total limit"
                    )
            files[packet_path] = payload
            assets.append(
                CampaignPlanMediaAsset(
                    sequence=item.sequence,
                    source=item.source,
                    reference=reference.path,
                    packet_path=packet_path,
                    content_type=content_type,
                    width=width,
                    height=height,
                    size=len(payload),
                    sha256=digest,
                    alt_text=reference.alt_text,
                    platforms=reference.platforms,
                )
            )
            if len(assets) > MAX_PACKAGED_MEDIA_ASSETS:
                raise ConfigError(
                    f"plan media must contain at most {MAX_PACKAGED_MEDIA_ASSETS} references"
                )
    if not assets:
        raise ConfigError("plan has no media references to package")
    provisional = CampaignPlanMedia(
        media_id="scm_000000000000",
        media_hash="0" * 64,
        plan_id=bundle.plan_id,
        source_hash=bundle.source_hash,
        total_bytes=total_bytes,
        assets=tuple(assets),
    )
    media_hash = hashlib.sha256(_canonical_media_core(provisional._core_dict())).hexdigest()
    media_index = CampaignPlanMedia(
        media_id=f"scm_{media_hash[:12]}",
        media_hash=media_hash,
        plan_id=bundle.plan_id,
        source_hash=bundle.source_hash,
        total_bytes=total_bytes,
        assets=tuple(assets),
    )
    payload_size = len(media_index_payload(media_index))
    if payload_size > MAX_CONFIG_BYTES:
        raise ConfigError(f"media index exceeds the {MAX_CONFIG_BYTES}-byte JSON limit")
    return CollectedCampaignPlanMedia(index=media_index, files=tuple(sorted(files.items())))


def media_index_payload(index: CampaignPlanMedia) -> bytes:
    """Render one normalized media index for embedding in a handoff packet."""
    return (json.dumps(index.to_dict(), ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def validate_collected_campaign_plan_media(media: CollectedCampaignPlanMedia) -> None:
    """Reject a forged or internally inconsistent in-memory media collection."""
    try:
        parsed_index = CampaignPlanMedia.from_dict(media.index.to_dict())
    except ConfigError as error:
        raise ConfigError(f"collected media index is invalid: {error}") from error
    if parsed_index != media.index:
        raise ConfigError("collected media index does not match its normalized representation")
    expected_paths = {asset.packet_path for asset in media.index.assets}
    files = media.payloads()
    issues: list[str] = []
    if len(files) != len(media.files):
        issues.append("collected media files must not repeat packet paths")
    if set(files) != expected_paths:
        issues.append("collected media files must exactly cover media index packet paths")
    for packet_path, payload in files.items():
        matching = next(
            (asset for asset in media.index.assets if asset.packet_path == packet_path), None
        )
        if matching is None:
            continue
        if len(payload) != matching.size or hashlib.sha256(payload).hexdigest() != matching.sha256:
            issues.append(f"collected media payload does not match index: {packet_path}")
            continue
        try:
            content_type, width, height, suffix = inspect_static_image(
                payload, suffix=Path(packet_path).suffix
            )
        except ConfigError as error:
            issues.append(f"collected media payload is invalid at {packet_path}: {error}")
            continue
        if (
            content_type != matching.content_type
            or width != matching.width
            or height != matching.height
            or not packet_path.endswith(f".{suffix}")
        ):
            issues.append(f"collected media image metadata does not match index: {packet_path}")
    if sum(len(payload) for payload in files.values()) != media.index.total_bytes:
        issues.append("collected media payload total does not match media index")
    if issues:
        raise ConfigError(issues)


def load_campaign_plan_media(path: str | Path) -> CampaignPlanMedia:
    """Load and validate one bounded handoff-media index."""
    return CampaignPlanMedia.from_dict(_load_json_object(path, kind="media index"))


def campaign_plan_media_binding_issues(
    expected: CampaignPlanMediaBinding | None,
    actual: CampaignPlanMedia | None,
) -> tuple[tuple[str, str], ...]:
    """Return stable approval findings for an optional exact media snapshot."""
    if expected is None and actual is None:
        return ()
    if expected is None:
        return (("media-introduced", "Exact media was supplied but is not bound by the approval."),)
    if actual is None:
        return (("media-missing", "Approval requires its exact media snapshot."),)
    if expected != actual.binding:
        return (("media-changed", "Current media does not match the approval's exact snapshot."),)
    return ()


def campaign_plan_media_identity_issues(
    bundle: CampaignPlanBundle,
    media: CampaignPlanMedia | None,
) -> tuple[tuple[str, str], ...]:
    """Return structural and source-binding findings for one optional media index."""
    if media is None:
        return ()
    try:
        parsed = CampaignPlanMedia.from_dict(media.to_dict())
    except ConfigError:
        return (("media-invalid", "Media index is internally inconsistent or malformed."),)
    issues: list[tuple[str, str]] = []
    if parsed.plan_id != bundle.plan_id:
        issues.append(("media-plan-id-changed", "Media index belongs to a different plan ID."))
    if parsed.source_hash != bundle.source_hash:
        issues.append(("media-source-changed", "Media index belongs to different plan source."))
    return tuple(issues)
