# Copyright (c) 2026 Samsarix LLC
# SPDX-License-Identifier: MPL-2.0

"""Portable, deterministic content-policy profiles and evaluation."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import (
    CampaignBundle,
    ConfigError,
    QualityIssue,
    SUPPORTED_PLATFORMS,
)
from .workflow import _load_json_object

MAX_POLICY_RULES = 50
MAX_POLICY_PHRASE_LENGTH = 200
_POLICY_KEYS = {"schemaVersion", "name", "rules"}
_RULE_KEYS = {"id", "kind", "phrase", "platforms", "severity", "caseSensitive"}
_RULE_ID_RE = re.compile(r"^[a-z][a-z0-9-]{0,63}$")
_POLICY_ID_RE = re.compile(r"^scpol_[0-9a-f]{12}$")
_SOURCE_HASH_RE = re.compile(r"^[0-9a-f]{64}$")


def _normalize_text(value: str) -> str:
    return unicodedata.normalize("NFC", value.replace("\r\n", "\n").replace("\r", "\n"))


def _has_control(value: str) -> bool:
    return any(unicodedata.category(character) in {"Cc", "Cs"} for character in value)


@dataclass(frozen=True, slots=True)
class ContentPolicyRule:
    """One literal phrase rule applied to selected rendered platform drafts."""

    rule_id: str
    kind: str
    phrase: str
    platforms: tuple[str, ...]
    severity: str = "error"
    case_sensitive: bool = False

    def applies_to(self, platform: str) -> bool:
        """Return whether this rule targets a platform."""
        return platform in self.platforms

    def to_dict(self) -> dict[str, Any]:
        """Return the normalized policy-source representation."""
        result: dict[str, Any] = {
            "id": self.rule_id,
            "kind": self.kind,
            "phrase": self.phrase,
            "platforms": list(self.platforms),
            "severity": self.severity,
            "caseSensitive": self.case_sensitive,
        }
        return result


@dataclass(frozen=True, slots=True)
class ContentPolicyBinding:
    """Normalized identity embedded in checks and source-bound approvals."""

    policy_id: str
    source_hash: str
    name: str

    def to_dict(self) -> dict[str, str]:
        """Return the stable machine-readable binding."""
        return {
            "policyId": self.policy_id,
            "sourceHash": self.source_hash,
            "name": self.name,
        }

    @classmethod
    def from_dict(
        cls,
        raw: object,
        *,
        field: str,
        issues: list[str],
    ) -> ContentPolicyBinding | None:
        """Parse a strict binding nested in another artifact."""
        if not isinstance(raw, Mapping):
            issues.append(f"{field} must be an object")
            return None
        unknown = sorted(str(key) for key in raw if key not in {"policyId", "sourceHash", "name"})
        if unknown:
            issues.append(f"{field} has unknown field(s): {', '.join(unknown)}")
        policy_id_value = raw.get("policyId")
        policy_id = policy_id_value if isinstance(policy_id_value, str) else ""
        if not _POLICY_ID_RE.fullmatch(policy_id):
            issues.append(f"{field}.policyId must be a Samsarix content policy ID")
        source_hash_value = raw.get("sourceHash")
        source_hash = source_hash_value if isinstance(source_hash_value, str) else ""
        if not _SOURCE_HASH_RE.fullmatch(source_hash):
            issues.append(f"{field}.sourceHash must be a lowercase SHA-256 hash")
        name_value = raw.get("name")
        if not isinstance(name_value, str):
            issues.append(f"{field}.name must be a string")
            name = ""
        else:
            name = _normalize_text(name_value).strip()
            if not name:
                issues.append(f"{field}.name must not be empty")
            elif len(name) > 120:
                issues.append(f"{field}.name must be at most 120 characters")
            if _has_control(name):
                issues.append(f"{field}.name must be a single line without control characters")
        if not policy_id or not source_hash or not name:
            return None
        return cls(policy_id=policy_id, source_hash=source_hash, name=name)


@dataclass(frozen=True, slots=True)
class ContentPolicy:
    """A bounded reusable policy evaluated against final rendered drafts."""

    schema_version: int
    name: str
    rules: tuple[ContentPolicyRule, ...]

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> ContentPolicy:
        """Validate and normalize a JSON-compatible content policy mapping."""
        if not isinstance(raw, Mapping):
            raise ConfigError("content policy must be a JSON object")
        issues: list[str] = []
        unknown = sorted(str(key) for key in raw if key not in _POLICY_KEYS)
        if unknown:
            issues.append(f"unknown content policy field(s): {', '.join(unknown)}")
        schema_version = raw.get("schemaVersion")
        if schema_version != 1 or isinstance(schema_version, bool):
            issues.append("schemaVersion must be 1")

        name_value = raw.get("name")
        if not isinstance(name_value, str):
            issues.append("name must be a string")
            name = ""
        else:
            name = _normalize_text(name_value).strip()
            if not name:
                issues.append("name must not be empty")
            elif len(name) > 120:
                issues.append("name must be at most 120 characters")
            if _has_control(name):
                issues.append("name must be a single line without control characters")

        rules_value = raw.get("rules")
        rules: list[ContentPolicyRule] = []
        seen_ids: set[str] = set()
        if not isinstance(rules_value, list):
            issues.append("rules must be a non-empty array")
        else:
            if not rules_value:
                issues.append("rules must contain at least one rule")
            if len(rules_value) > MAX_POLICY_RULES:
                issues.append(f"rules must contain at most {MAX_POLICY_RULES} items")
            for index, value in enumerate(rules_value[:MAX_POLICY_RULES]):
                rule = _parse_rule(value, index=index, seen_ids=seen_ids, issues=issues)
                if rule is not None:
                    rules.append(rule)
        if issues:
            raise ConfigError(issues)
        return cls(schema_version=1, name=name, rules=tuple(rules))

    def to_dict(self) -> dict[str, Any]:
        """Return normalized JSON-compatible policy source."""
        return {
            "schemaVersion": self.schema_version,
            "name": self.name,
            "rules": [rule.to_dict() for rule in self.rules],
        }

    @property
    def source_hash(self) -> str:
        """Return the full deterministic SHA-256 of normalized policy source."""
        payload = json.dumps(
            self.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    @property
    def policy_id(self) -> str:
        """Return a short display identity derived from the full policy hash."""
        return f"scpol_{self.source_hash[:12]}"

    @property
    def binding(self) -> ContentPolicyBinding:
        """Return the identity embedded in reports and approval evidence."""
        return ContentPolicyBinding(self.policy_id, self.source_hash, self.name)


def _parse_rule(
    value: object,
    *,
    index: int,
    seen_ids: set[str],
    issues: list[str],
) -> ContentPolicyRule | None:
    """Parse one strict literal phrase rule while accumulating all issues."""
    field = f"rules[{index}]"
    if not isinstance(value, Mapping):
        issues.append(f"{field} must be an object")
        return None
    unknown = sorted(str(key) for key in value if key not in _RULE_KEYS)
    if unknown:
        issues.append(f"{field} has unknown field(s): {', '.join(unknown)}")

    rule_id_value = value.get("id")
    rule_id = rule_id_value if isinstance(rule_id_value, str) else ""
    if not _RULE_ID_RE.fullmatch(rule_id):
        issues.append(f"{field}.id must match {_RULE_ID_RE.pattern}")
    elif rule_id in seen_ids:
        issues.append(f"{field}.id duplicates {rule_id}")
    else:
        seen_ids.add(rule_id)

    kind_value = value.get("kind")
    kind = kind_value if isinstance(kind_value, str) else ""
    if kind not in {"blockedPhrase", "requiredPhrase"}:
        issues.append(f"{field}.kind must be blockedPhrase or requiredPhrase")

    phrase_value = value.get("phrase")
    if not isinstance(phrase_value, str):
        issues.append(f"{field}.phrase must be a string")
        phrase = ""
    else:
        phrase = _normalize_text(phrase_value).strip()
        if not phrase:
            issues.append(f"{field}.phrase must not be empty")
        elif len(phrase) > MAX_POLICY_PHRASE_LENGTH:
            issues.append(f"{field}.phrase must be at most {MAX_POLICY_PHRASE_LENGTH} characters")
        if _has_control(phrase):
            issues.append(f"{field}.phrase must be a single line without control characters")

    targets_value = value.get("platforms")
    targets: list[str] = []
    if targets_value is None:
        targets.extend(SUPPORTED_PLATFORMS)
    elif not isinstance(targets_value, list):
        issues.append(f"{field}.platforms must be a non-empty array")
    else:
        if not targets_value:
            issues.append(f"{field}.platforms must contain at least one platform")
        if len(targets_value) > len(SUPPORTED_PLATFORMS):
            issues.append(
                f"{field}.platforms must contain at most {len(SUPPORTED_PLATFORMS)} items"
            )
        selected: set[str] = set()
        for target_index, target_value in enumerate(targets_value):
            target_field = f"{field}.platforms[{target_index}]"
            if not isinstance(target_value, str):
                issues.append(f"{target_field} must be a string")
                continue
            target = target_value.strip().lower()
            if target not in SUPPORTED_PLATFORMS:
                issues.append(f"{target_field} must be one of: {', '.join(SUPPORTED_PLATFORMS)}")
            elif target in selected:
                issues.append(f"{target_field} duplicates {target}")
            else:
                selected.add(target)
        targets.extend(platform for platform in SUPPORTED_PLATFORMS if platform in selected)

    severity_value = value.get("severity", "error")
    severity = severity_value if isinstance(severity_value, str) else ""
    if severity not in {"warning", "error"}:
        issues.append(f"{field}.severity must be warning or error")
    case_sensitive_value = value.get("caseSensitive", False)
    if not isinstance(case_sensitive_value, bool):
        issues.append(f"{field}.caseSensitive must be a boolean")
        case_sensitive = False
    else:
        case_sensitive = case_sensitive_value

    if not rule_id or not kind or not phrase or not targets or not severity:
        return None
    return ContentPolicyRule(
        rule_id=rule_id,
        kind=kind,
        phrase=phrase,
        platforms=tuple(targets),
        severity=severity,
        case_sensitive=case_sensitive,
    )


def load_content_policy(path: str | Path) -> ContentPolicy:
    """Load one bounded UTF-8 policy JSON file with duplicate-key protection."""
    return ContentPolicy.from_dict(_load_json_object(path, kind="content policy"))


def content_policy_binding_issues(
    approved: ContentPolicyBinding | None,
    current: ContentPolicy | None,
) -> tuple[tuple[str, str], ...]:
    """Return stable verification issues for approved and current policy identity."""
    if approved is None and current is None:
        return ()
    if approved is not None and current is None:
        return (
            (
                "content-policy-required",
                "Approval requires the exact content policy recorded at review time.",
            ),
        )
    if approved is None:
        return (
            (
                "content-policy-unapproved",
                "A content policy was supplied, but this approval did not review it.",
            ),
        )
    assert current is not None
    if approved != current.binding:
        return (
            (
                "content-policy-changed",
                "Current content policy no longer matches the policy recorded by the approval.",
            ),
        )
    return ()


def evaluate_content_policy(
    bundle: CampaignBundle,
    policy: ContentPolicy,
    *,
    warnings_as_errors: bool = False,
) -> tuple[QualityIssue, ...]:
    """Evaluate literal rules against final copy-ready platform content."""
    findings: list[QualityIssue] = []
    for draft in bundle.drafts:
        for rule in policy.rules:
            if not rule.applies_to(draft.platform):
                continue
            content = draft.content if rule.case_sensitive else draft.content.casefold()
            phrase = rule.phrase if rule.case_sensitive else rule.phrase.casefold()
            matched = phrase in content
            violated = matched if rule.kind == "blockedPhrase" else not matched
            if not violated:
                continue
            severity = (
                "error" if warnings_as_errors and rule.severity == "warning" else rule.severity
            )
            action = "contains blocked phrase" if matched else "is missing required phrase"
            message = f"Content policy rule {rule.rule_id!r}: " f"draft {action} {rule.phrase!r}."
            findings.append(
                QualityIssue(
                    code=(
                        "policy-blocked-phrase"
                        if rule.kind == "blockedPhrase"
                        else "policy-required-phrase"
                    ),
                    severity=severity,
                    platform=draft.platform,
                    message=message,
                    rule_id=rule.rule_id,
                )
            )
    return tuple(findings)
