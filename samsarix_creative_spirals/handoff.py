# Copyright (c) 2026 Samsarix LLC
# SPDX-License-Identifier: MPL-2.0

"""Approved plan handoff packets with offline source and artifact verification."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ._version import __version__
from .approval_policy import (
    CampaignPlanApprovalEvidence,
    load_campaign_plan_approval_evidence,
    verify_campaign_plan_approval_evidence,
)
from .filesystem import directory_identity, is_link_like, require_directory_identity
from .media_package import (
    CampaignPlanMedia,
    CollectedCampaignPlanMedia,
    load_campaign_plan_media,
    media_index_payload,
    validate_collected_campaign_plan_media,
)
from .models import ConfigError
from .policy import ContentPolicy, load_content_policy
from .plans import (
    CampaignPlanBundle,
    _clear_plan_temp,
    _plan_artifact_payloads,
    _write_plan_artifacts,
)
from .review import _format_utc, _parse_timestamp
from .workflow import _load_json_object, _slugify

MAX_HANDOFF_ARTIFACT_BYTES = 1_000_000_000
_HANDOFF_KEYS = {
    "schemaVersion",
    "artifactType",
    "handoffId",
    "handoffHash",
    "planId",
    "sourceHash",
    "approval",
    "generatedAt",
    "producer",
    "artifacts",
}
_PRODUCER_KEYS = {"name", "version"}
_ARTIFACT_KEYS = {"bytes", "sha256"}
_REQUIRED_ARTIFACT_PATHS = (
    "adapter.json",
    "approval.json",
    "calendar.ics",
    "manifest.json",
)
_OPTIONAL_ARTIFACT_PATHS = ("content-policy.json", "media-index.json")
_CSV_ARTIFACT_PATHS = (
    "csv/x.csv",
    "csv/linkedin.csv",
    "csv/bluesky.csv",
    "csv/mastodon.csv",
    "csv/discord.csv",
)
_ARTIFACT_PATHS = _REQUIRED_ARTIFACT_PATHS + _OPTIONAL_ARTIFACT_PATHS + _CSV_ARTIFACT_PATHS
_HANDOFF_ID_RE = re.compile(r"^sch_[0-9a-f]{12}$")
_PLAN_ID_RE = re.compile(r"^scp_[0-9a-f]{12}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_VERSION_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+(?:[A-Za-z0-9.+-]*)?$")


@dataclass(frozen=True, slots=True)
class HandoffArtifact:
    """Expected size and SHA-256 checksum for one fixed packet-relative artifact."""

    path: str
    size: int
    sha256: str

    def to_dict(self) -> dict[str, Any]:
        return {"bytes": self.size, "sha256": self.sha256}


def _parse_producer(raw: dict[str, Any], issues: list[str]) -> str:
    producer_value = raw.get("producer")
    producer_version = ""
    if not isinstance(producer_value, dict):
        issues.append("producer must be an object")
        return producer_version

    producer_unknown = sorted(str(key) for key in producer_value if key not in _PRODUCER_KEYS)
    if producer_unknown:
        issues.append(f"producer has unknown field(s): {', '.join(producer_unknown)}")
    if producer_value.get("name") != "samsarix-creative-spirals":
        issues.append("producer.name must be samsarix-creative-spirals")
    version_value = producer_value.get("version")
    producer_version = version_value if isinstance(version_value, str) else ""
    if len(producer_version) > 50 or not _VERSION_RE.fullmatch(producer_version):
        issues.append("producer.version must be a supported package version")
    return producer_version


def _parse_artifacts(
    raw: dict[str, Any],
    issues: list[str],
) -> dict[str, HandoffArtifact]:
    artifacts_value = raw.get("artifacts")
    artifacts_by_path: dict[str, HandoffArtifact] = {}
    if not isinstance(artifacts_value, dict):
        issues.append("artifacts must be an object")
        return artifacts_by_path

    minimum_artifacts = len(_REQUIRED_ARTIFACT_PATHS) + 1
    maximum_artifacts = len(_ARTIFACT_PATHS)
    if not minimum_artifacts <= len(artifacts_value) <= maximum_artifacts:
        issues.append(
            f"artifacts must contain between {minimum_artifacts} and {maximum_artifacts} files"
        )
    for path, artifact_value in artifacts_value.items():
        if path not in _ARTIFACT_PATHS:
            issues.append(f"artifacts has unsupported path: {path}")
            continue
        if not isinstance(artifact_value, dict):
            issues.append(f"artifacts.{path} must be an object")
            continue
        artifact_unknown = sorted(str(key) for key in artifact_value if key not in _ARTIFACT_KEYS)
        if artifact_unknown:
            issues.append(f"artifacts.{path} has unknown field(s): {', '.join(artifact_unknown)}")
        size_value = artifact_value.get("bytes")
        size = size_value if isinstance(size_value, int) and not isinstance(size_value, bool) else 0
        if not 1 <= size <= MAX_HANDOFF_ARTIFACT_BYTES:
            issues.append(
                f"artifacts.{path}.bytes must be between 1 and {MAX_HANDOFF_ARTIFACT_BYTES}"
            )
        digest_value = artifact_value.get("sha256")
        digest = digest_value if isinstance(digest_value, str) else ""
        if not _SHA256_RE.fullmatch(digest):
            issues.append(f"artifacts.{path}.sha256 must be a lowercase SHA-256 hash")
        artifacts_by_path[path] = HandoffArtifact(path, size, digest)
    missing = [path for path in _REQUIRED_ARTIFACT_PATHS if path not in artifacts_by_path]
    if missing:
        issues.append(f"artifacts is missing required path(s): {', '.join(missing)}")
    if not any(path in artifacts_by_path for path in _CSV_ARTIFACT_PATHS):
        issues.append("artifacts must contain at least one platform CSV")
    return artifacts_by_path


@dataclass(frozen=True, slots=True)
class CampaignPlanHandoff:
    """Unsigned manifest that binds an approval to exact rendered plan artifacts."""

    handoff_id: str
    handoff_hash: str
    plan_id: str
    source_hash: str
    generated_at: datetime
    producer_version: str
    artifacts: tuple[HandoffArtifact, ...]

    def _core_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": 1,
            "artifactType": "plan-handoff",
            "planId": self.plan_id,
            "sourceHash": self.source_hash,
            "approval": "approval.json",
            "generatedAt": _format_utc(self.generated_at),
            "producer": {
                "name": "samsarix-creative-spirals",
                "version": self.producer_version,
            },
            "artifacts": {artifact.path: artifact.to_dict() for artifact in self.artifacts},
        }

    def to_dict(self) -> dict[str, Any]:
        core = self._core_dict()
        return {
            "schemaVersion": core["schemaVersion"],
            "artifactType": core["artifactType"],
            "handoffId": self.handoff_id,
            "handoffHash": self.handoff_hash,
            "planId": core["planId"],
            "sourceHash": core["sourceHash"],
            "approval": core["approval"],
            "generatedAt": core["generatedAt"],
            "producer": core["producer"],
            "artifacts": core["artifacts"],
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> CampaignPlanHandoff:
        issues: list[str] = []
        unknown = sorted(str(key) for key in raw if key not in _HANDOFF_KEYS)
        if unknown:
            issues.append(f"unknown handoff field(s): {', '.join(unknown)}")
        if raw.get("schemaVersion") != 1 or isinstance(raw.get("schemaVersion"), bool):
            issues.append("schemaVersion must be 1")
        if raw.get("artifactType") != "plan-handoff":
            issues.append("artifactType must be plan-handoff")

        handoff_id_value = raw.get("handoffId")
        handoff_id = handoff_id_value if isinstance(handoff_id_value, str) else ""
        if not _HANDOFF_ID_RE.fullmatch(handoff_id):
            issues.append("handoffId must be a Samsarix handoff ID")
        handoff_hash_value = raw.get("handoffHash")
        handoff_hash = handoff_hash_value if isinstance(handoff_hash_value, str) else ""
        if not _SHA256_RE.fullmatch(handoff_hash):
            issues.append("handoffHash must be a lowercase SHA-256 hash")
        plan_id_value = raw.get("planId")
        plan_id = plan_id_value if isinstance(plan_id_value, str) else ""
        if not _PLAN_ID_RE.fullmatch(plan_id):
            issues.append("planId must be a Samsarix campaign plan ID")
        source_hash_value = raw.get("sourceHash")
        source_hash = source_hash_value if isinstance(source_hash_value, str) else ""
        if not _SHA256_RE.fullmatch(source_hash):
            issues.append("sourceHash must be a lowercase SHA-256 hash")
        if raw.get("approval") != "approval.json":
            issues.append("approval must be approval.json")

        generated_at = _parse_timestamp(
            raw.get("generatedAt"),
            field="generatedAt",
            issues=issues,
        )
        producer_version = _parse_producer(raw, issues)
        artifacts_by_path = _parse_artifacts(raw, issues)

        if issues:
            raise ConfigError(issues)
        assert generated_at is not None
        artifacts = tuple(
            artifacts_by_path[path] for path in _ARTIFACT_PATHS if path in artifacts_by_path
        )
        return cls(
            handoff_id=handoff_id,
            handoff_hash=handoff_hash,
            plan_id=plan_id,
            source_hash=source_hash,
            generated_at=generated_at,
            producer_version=producer_version,
            artifacts=artifacts,
        )


@dataclass(frozen=True, slots=True)
class CampaignPlanHandoffPacket:
    """Validated handoff metadata, approval, and optional policy from one packet."""

    root: Path
    handoff: CampaignPlanHandoff
    approval: CampaignPlanApprovalEvidence
    content_policy: ContentPolicy | None = None
    media: CampaignPlanMedia | None = None


@dataclass(frozen=True, slots=True)
class HandoffIssue:
    """One stable reason an approved handoff packet is not current or intact."""

    code: str
    message: str
    path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "path": self.path, "message": self.message}


@dataclass(frozen=True, slots=True)
class HandoffCheck:
    """Offline verification result for current plan source and one handoff packet."""

    handoff_id: str
    plan_id: str
    valid: bool
    issues: tuple[HandoffIssue, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": 1,
            "valid": self.valid,
            "handoffId": self.handoff_id,
            "planId": self.plan_id,
            "issues": [issue.to_dict() for issue in self.issues],
        }


def _approval_payload(approval: CampaignPlanApprovalEvidence) -> bytes:
    return (json.dumps(approval.to_dict(), ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _content_policy_payload(content_policy: ContentPolicy) -> bytes:
    """Return normalized, human-readable policy source for a packet artifact."""
    return (json.dumps(content_policy.to_dict(), ensure_ascii=False, indent=2) + "\n").encode(
        "utf-8"
    )


def _handoff_payload(handoff: CampaignPlanHandoff) -> bytes:
    return (json.dumps(handoff.to_dict(), ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _handoff_artifact_payloads(
    bundle: CampaignPlanBundle,
    approval: CampaignPlanApprovalEvidence,
    generated_at: datetime,
    content_policy: ContentPolicy | None = None,
    media: CampaignPlanMedia | None = None,
) -> dict[str, bytes]:
    artifacts = _plan_artifact_payloads(bundle, generated_at)
    artifacts["approval.json"] = _approval_payload(approval)
    if content_policy is not None:
        artifacts["content-policy.json"] = _content_policy_payload(content_policy)
    if media is not None:
        artifacts["media-index.json"] = media_index_payload(media)
    return artifacts


def _artifact_descriptors(artifacts: dict[str, bytes]) -> tuple[HandoffArtifact, ...]:
    return tuple(
        HandoffArtifact(
            path=path,
            size=len(artifacts[path]),
            sha256=hashlib.sha256(artifacts[path]).hexdigest(),
        )
        for path in _ARTIFACT_PATHS
        if path in artifacts
    )


def _canonical_handoff_core(core: dict[str, Any]) -> bytes:
    return json.dumps(
        core,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _assemble_handoff(
    bundle: CampaignPlanBundle,
    approval: CampaignPlanApprovalEvidence,
    generated_at: datetime,
    content_policy: ContentPolicy | None = None,
    media: CampaignPlanMedia | None = None,
) -> CampaignPlanHandoff:
    artifacts = _artifact_descriptors(
        _handoff_artifact_payloads(bundle, approval, generated_at, content_policy, media)
    )
    provisional = CampaignPlanHandoff(
        handoff_id="sch_000000000000",
        handoff_hash="0" * 64,
        plan_id=bundle.plan_id,
        source_hash=bundle.source_hash,
        generated_at=generated_at.astimezone(timezone.utc),
        producer_version=__version__,
        artifacts=artifacts,
    )
    handoff_hash = hashlib.sha256(_canonical_handoff_core(provisional._core_dict())).hexdigest()
    return CampaignPlanHandoff(
        handoff_id=f"sch_{handoff_hash[:12]}",
        handoff_hash=handoff_hash,
        plan_id=provisional.plan_id,
        source_hash=provisional.source_hash,
        generated_at=provisional.generated_at,
        producer_version=provisional.producer_version,
        artifacts=provisional.artifacts,
    )


def build_campaign_plan_handoff(
    bundle: CampaignPlanBundle,
    approval: CampaignPlanApprovalEvidence,
    *,
    generated_at: datetime,
    content_policy: ContentPolicy | None = None,
    media: CampaignPlanMedia | None = None,
) -> CampaignPlanHandoff:
    """Build an unsigned handoff manifest after approval and aggregate quality verification."""
    issues: list[str] = []
    if generated_at.utcoffset() is None:
        issues.append("generated_at must include timezone information")
    if approval.approved_at.utcoffset() is None:
        issues.append("approval approved_at must include timezone information")
    approval_check = verify_campaign_plan_approval_evidence(
        bundle, approval, content_policy=content_policy, media=media
    )
    if not approval_check.valid:
        details = ", ".join(issue.message for issue in approval_check.issues)
        issues.append(f"cannot create handoff from an invalid plan approval: {details}")
    if (
        generated_at.utcoffset() is not None
        and approval.approved_at.utcoffset() is not None
        and generated_at < approval.approved_at
    ):
        issues.append("generated_at must not be earlier than approved_at")
    if issues:
        raise ConfigError(issues)
    return _assemble_handoff(bundle, approval, generated_at, content_policy, media)


def export_campaign_plan_handoff(
    bundle: CampaignPlanBundle,
    approval: CampaignPlanApprovalEvidence,
    output_root: str | Path = "handoff-outbox",
    *,
    generated_at: datetime | None = None,
    content_policy: ContentPolicy | None = None,
    media: CollectedCampaignPlanMedia | None = None,
) -> Path:
    """Atomically create a new approved handoff packet without overwriting evidence."""
    stamp = generated_at or datetime.now(timezone.utc)
    if media is not None:
        validate_collected_campaign_plan_media(media)
    media_index = media.index if media is not None else None
    handoff = build_campaign_plan_handoff(
        bundle,
        approval,
        generated_at=stamp,
        content_policy=content_policy,
        media=media_index,
    )
    artifacts = _handoff_artifact_payloads(
        bundle,
        approval,
        handoff.generated_at,
        content_policy,
        media_index,
    )

    root = Path(os.path.abspath(output_root))
    if root.exists():
        if is_link_like(root):
            raise OSError(
                f"refusing to export through a symbolic-link or other link-like directory: {root}"
            )
    else:
        root.mkdir(parents=True)
    root_identity = directory_identity(root, label="handoff output root")

    packet_name = f"{_slugify(bundle.name)}-{handoff.handoff_id}"
    target = root / packet_name
    if target.exists() or is_link_like(target):
        raise FileExistsError(f"handoff packet already exists: {target}")
    temporary = root / f".{packet_name}.{uuid.uuid4().hex}.tmp"
    require_directory_identity(root, root_identity, label="handoff output root")
    temporary.mkdir(mode=0o700)
    temporary_identity = directory_identity(temporary, label="temporary plan directory")
    try:
        _write_plan_artifacts(temporary, artifacts)
        if media is not None:
            _write_plan_artifacts(temporary, media.payloads())
        (temporary / "handoff.json").write_bytes(_handoff_payload(handoff))
        require_directory_identity(root, root_identity, label="handoff output root")
        if target.exists() or is_link_like(target):
            raise FileExistsError(f"handoff packet appeared during export: {target}")
        temporary.replace(target)
    finally:
        _clear_plan_temp(temporary, temporary_identity)
    return target


def _require_packet_json(root: Path, filename: str) -> Path:
    path = root / filename
    if is_link_like(path) or not path.is_file():
        raise ConfigError(f"handoff {filename} must be a regular file")
    return path


def load_campaign_plan_handoff(path: str | Path) -> CampaignPlanHandoffPacket:
    """Load bounded handoff and approval metadata from a non-symlink packet directory."""
    root = Path(os.path.abspath(path))
    if is_link_like(root) or not root.is_dir():
        raise ConfigError("handoff path must be a non-symbolic-link directory")
    handoff_path = _require_packet_json(root, "handoff.json")
    approval_path = _require_packet_json(root, "approval.json")
    handoff = CampaignPlanHandoff.from_dict(_load_json_object(handoff_path, kind="handoff"))
    approval = load_campaign_plan_approval_evidence(approval_path)
    content_policy_path = root / "content-policy.json"
    content_policy = None
    if content_policy_path.exists() or is_link_like(content_policy_path):
        content_policy = load_content_policy(_require_packet_json(root, "content-policy.json"))
    media_path = root / "media-index.json"
    media = None
    if media_path.exists() or is_link_like(media_path):
        media = load_campaign_plan_media(_require_packet_json(root, "media-index.json"))
    return CampaignPlanHandoffPacket(
        root=root,
        handoff=handoff,
        approval=approval,
        content_policy=content_policy,
        media=media,
    )


def _expected_packet_paths(
    artifacts: dict[str, bytes], media: CampaignPlanMedia | None
) -> set[str]:
    media_paths = {asset.packet_path for asset in media.assets} if media is not None else set()
    return {"handoff.json", *artifacts, *media_paths}


def _check_packet_entries(
    packet: CampaignPlanHandoffPacket,
    expected_paths: set[str],
    issues: list[HandoffIssue],
) -> None:
    expected_root = {path.split("/", 1)[0] for path in expected_paths}
    try:
        root_entries = list(packet.root.iterdir())
    except OSError as error:
        issues.append(HandoffIssue("packet-read-failed", f"Cannot list packet: {error}"))
        return
    for entry in sorted(root_entries, key=lambda candidate: candidate.name):
        if entry.name not in expected_root:
            issues.append(
                HandoffIssue(
                    "artifact-unexpected",
                    "Packet contains an unexpected root entry.",
                    entry.name,
                )
            )
    _check_packet_directory(packet.root, "csv", expected_paths, issues)
    _check_packet_directory(packet.root, "media", expected_paths, issues)


def _check_packet_directory(
    root: Path,
    name: str,
    expected_paths: set[str],
    issues: list[HandoffIssue],
) -> None:
    directory = root / name
    expected = {path for path in expected_paths if path.startswith(f"{name}/")}
    if is_link_like(directory) or (directory.exists() and not directory.is_dir()):
        issues.append(
            HandoffIssue(
                "artifact-type-invalid",
                f"{name} entry must be a regular directory.",
                name,
            )
        )
        return
    if not directory.exists():
        return
    try:
        entries = list(directory.iterdir())
    except OSError as error:
        issues.append(
            HandoffIssue(
                "packet-read-failed",
                f"Cannot list packet {name} directory: {error}",
                name,
            )
        )
        return
    for entry in sorted(entries, key=lambda candidate: candidate.name):
        relative = f"{name}/{entry.name}"
        if relative not in expected:
            issues.append(
                HandoffIssue(
                    "artifact-unexpected",
                    f"Packet contains an unexpected {name} artifact.",
                    relative,
                )
            )


def _hash_expected_file(
    root: Path,
    relative_path: str,
    expected_size: int,
    issues: list[HandoffIssue],
) -> str | None:
    segments = relative_path.split("/")
    parent = root
    for segment in segments[:-1]:
        parent /= segment
        if is_link_like(parent):
            issues.append(
                HandoffIssue(
                    "artifact-type-invalid",
                    "Packet artifact parent must not be a symbolic link.",
                    relative_path,
                )
            )
            return None
    path = root.joinpath(*segments)
    if is_link_like(path) or not path.exists():
        issues.append(
            HandoffIssue("artifact-missing", "Expected packet artifact is missing.", relative_path)
        )
        return None
    if not path.is_file():
        issues.append(
            HandoffIssue(
                "artifact-type-invalid",
                "Packet artifact must be a regular file.",
                relative_path,
            )
        )
        return None
    try:
        with path.open("rb") as handle:
            before = os.fstat(handle.fileno())
            if not stat.S_ISREG(before.st_mode):
                issues.append(
                    HandoffIssue(
                        "artifact-type-invalid",
                        "Packet artifact must open as a regular file.",
                        relative_path,
                    )
                )
                return None
            if before.st_size != expected_size:
                issues.append(
                    HandoffIssue(
                        "artifact-size-changed",
                        f"Artifact size is {before.st_size} bytes; expected {expected_size}.",
                        relative_path,
                    )
                )
                return None
            digest = hashlib.sha256()
            while chunk := handle.read(1024 * 1024):
                digest.update(chunk)
            after = os.fstat(handle.fileno())
    except OSError as error:
        issues.append(
            HandoffIssue(
                "artifact-read-failed",
                f"Cannot read packet artifact: {error}",
                relative_path,
            )
        )
        return None
    before_identity = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
    after_identity = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
    if before_identity != after_identity:
        issues.append(
            HandoffIssue(
                "artifact-changed-during-read",
                "Packet artifact changed while it was being verified.",
                relative_path,
            )
        )
        return None
    return digest.hexdigest()


def _check_handoff_identity_and_order(
    bundle: CampaignPlanBundle,
    packet: CampaignPlanHandoffPacket,
    issues: list[HandoffIssue],
    *,
    content_policy: ContentPolicy | None = None,
) -> bool:
    handoff = packet.handoff
    packet_root_valid = not is_link_like(packet.root) and packet.root.is_dir()
    if not packet_root_valid:
        issues.append(
            HandoffIssue(
                "packet-root-invalid",
                "Packet root must remain a non-symbolic-link directory.",
            )
        )
    approval_check = verify_campaign_plan_approval_evidence(
        bundle,
        packet.approval,
        content_policy=content_policy,
        media=packet.media,
    )
    for approval_issue in approval_check.issues:
        issues.append(
            HandoffIssue(
                f"approval-{approval_issue.code}",
                approval_issue.message,
                "approval.json",
            )
        )
    if handoff.plan_id != bundle.plan_id:
        issues.append(HandoffIssue("plan-id-changed", "Plan ID does not match current source."))
    if handoff.source_hash != bundle.source_hash:
        issues.append(
            HandoffIssue("source-changed", "Plan source hash does not match current source.")
        )
    if handoff.producer_version != __version__:
        issues.append(
            HandoffIssue(
                "producer-version-changed",
                (
                    f"Packet was produced by {handoff.producer_version}; "
                    f"current version is {__version__}."
                ),
                "handoff.json",
            )
        )
    if handoff.generated_at < packet.approval.approved_at:
        issues.append(
            HandoffIssue(
                "handoff-before-approval",
                "Packet generation time is earlier than its approval time.",
                "handoff.json",
            )
        )
    return packet_root_valid


def _regenerate_and_check_handoff(
    bundle: CampaignPlanBundle,
    packet: CampaignPlanHandoffPacket,
    issues: list[HandoffIssue],
    *,
    content_policy: ContentPolicy | None = None,
) -> tuple[dict[str, bytes], CampaignPlanHandoff]:
    handoff = packet.handoff
    expected_artifacts = _handoff_artifact_payloads(
        bundle,
        packet.approval,
        handoff.generated_at,
        content_policy,
        packet.media,
    )
    expected_handoff = _assemble_handoff(
        bundle,
        packet.approval,
        handoff.generated_at,
        content_policy,
        packet.media,
    )
    declared_core_hash = hashlib.sha256(_canonical_handoff_core(handoff._core_dict())).hexdigest()
    if handoff.handoff_hash != declared_core_hash:
        issues.append(
            HandoffIssue(
                "handoff-hash-invalid",
                "Handoff metadata does not match its declared hash.",
                "handoff.json",
            )
        )
    if handoff.handoff_hash != expected_handoff.handoff_hash:
        issues.append(
            HandoffIssue(
                "handoff-hash-changed",
                "Handoff metadata no longer matches its expected hash.",
                "handoff.json",
            )
        )
    if handoff.handoff_id != expected_handoff.handoff_id:
        issues.append(
            HandoffIssue(
                "handoff-id-changed",
                "Handoff ID no longer matches its expected identity.",
                "handoff.json",
            )
        )
    return expected_artifacts, expected_handoff


def _check_artifact_declarations(
    handoff: CampaignPlanHandoff,
    expected_handoff: CampaignPlanHandoff,
    issues: list[HandoffIssue],
) -> dict[str, HandoffArtifact]:
    declared = {artifact.path: artifact for artifact in handoff.artifacts}
    expected = {artifact.path: artifact for artifact in expected_handoff.artifacts}
    for relative_path in _ARTIFACT_PATHS:
        declared_artifact = declared.get(relative_path)
        expected_artifact = expected.get(relative_path)
        if expected_artifact is None and declared_artifact is not None:
            issues.append(
                HandoffIssue(
                    "artifact-declaration-unexpected",
                    "Manifest declares an artifact not generated by the current plan.",
                    relative_path,
                )
            )
        elif expected_artifact is not None and declared_artifact is None:
            issues.append(
                HandoffIssue(
                    "artifact-declaration-missing",
                    "Manifest is missing an expected artifact declaration.",
                    relative_path,
                )
            )
        elif expected_artifact is not None and declared_artifact != expected_artifact:
            issues.append(
                HandoffIssue(
                    "artifact-metadata-changed",
                    "Declared artifact size or checksum does not match regenerated output.",
                    relative_path,
                )
            )
    return declared


def _check_handoff_files(
    packet: CampaignPlanHandoffPacket,
    expected_artifacts: dict[str, bytes],
    declared: dict[str, HandoffArtifact],
    issues: list[HandoffIssue],
) -> None:
    expected_paths = _expected_packet_paths(expected_artifacts, packet.media)
    _check_packet_entries(packet, expected_paths, issues)
    expected_handoff_payload = _handoff_payload(packet.handoff)
    actual_handoff_digest = _hash_expected_file(
        packet.root,
        "handoff.json",
        len(expected_handoff_payload),
        issues,
    )
    if (
        actual_handoff_digest is not None
        and actual_handoff_digest != hashlib.sha256(expected_handoff_payload).hexdigest()
    ):
        issues.append(
            HandoffIssue(
                "handoff-file-changed",
                "On-disk handoff metadata does not match the loaded canonical record.",
                "handoff.json",
            )
        )
    for relative_path in _ARTIFACT_PATHS:
        payload = expected_artifacts.get(relative_path)
        if payload is None:
            continue
        actual_digest = _hash_expected_file(
            packet.root,
            relative_path,
            len(payload),
            issues,
        )
        if actual_digest is None:
            continue
        expected_digest = hashlib.sha256(payload).hexdigest()
        if actual_digest != expected_digest:
            issues.append(
                HandoffIssue(
                    "artifact-content-changed",
                    "Artifact bytes do not match regenerated current-plan output.",
                    relative_path,
                )
            )
        declared_artifact = declared.get(relative_path)
        if declared_artifact is not None and actual_digest != declared_artifact.sha256:
            issues.append(
                HandoffIssue(
                    "artifact-checksum-mismatch",
                    "Artifact bytes do not match the checksum declared by the packet.",
                    relative_path,
                )
            )
    if packet.media is not None:
        checked_paths: set[str] = set()
        for asset in packet.media.assets:
            if asset.packet_path in checked_paths:
                continue
            checked_paths.add(asset.packet_path)
            actual_digest = _hash_expected_file(
                packet.root,
                asset.packet_path,
                asset.size,
                issues,
            )
            if actual_digest is not None and actual_digest != asset.sha256:
                issues.append(
                    HandoffIssue(
                        "media-checksum-mismatch",
                        "Packaged media bytes do not match the approval-bound media index.",
                        asset.packet_path,
                    )
                )


def verify_campaign_plan_handoff(
    bundle: CampaignPlanBundle,
    packet: CampaignPlanHandoffPacket,
    *,
    content_policy: ContentPolicy | None = None,
) -> HandoffCheck:
    """Verify packet source, approval, shape, and regenerated artifact bytes offline."""
    issues: list[HandoffIssue] = []
    embedded_policy = packet.content_policy
    if (
        embedded_policy is not None
        and content_policy is not None
        and embedded_policy.binding != content_policy.binding
    ):
        issues.append(
            HandoffIssue(
                "content-policy-argument-changed",
                "Supplied content policy does not match the policy embedded in the packet.",
                "content-policy.json",
            )
        )
    effective_policy = embedded_policy or content_policy
    packet_root_valid = _check_handoff_identity_and_order(
        bundle, packet, issues, content_policy=effective_policy
    )
    expected_artifacts, expected_handoff = _regenerate_and_check_handoff(
        bundle,
        packet,
        issues,
        content_policy=effective_policy,
    )
    declared = _check_artifact_declarations(packet.handoff, expected_handoff, issues)
    if packet_root_valid:
        _check_handoff_files(packet, expected_artifacts, declared, issues)

    return HandoffCheck(
        handoff_id=packet.handoff.handoff_id,
        plan_id=bundle.plan_id,
        valid=not issues,
        issues=tuple(issues),
    )
