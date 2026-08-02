# Copyright (c) 2026 Samsarix LLC
# SPDX-License-Identifier: MPL-2.0

"""Access to the packaged authoring and interchange JSON Schemas."""

from __future__ import annotations

import json
from importlib.resources import files
from typing import Any, cast


def load_campaign_schema() -> dict[str, Any]:
    """Return a fresh copy of the public campaign JSON Schema."""
    resource = files(__package__).joinpath("campaign.schema.json")
    payload = json.loads(resource.read_text(encoding="utf-8"))
    return cast(dict[str, Any], payload)


def load_plan_schema() -> dict[str, Any]:
    """Return a fresh copy of the public campaign-plan JSON Schema."""
    resource = files(__package__).joinpath("plan.schema.json")
    payload = json.loads(resource.read_text(encoding="utf-8"))
    return cast(dict[str, Any], payload)


def load_content_policy_schema() -> dict[str, Any]:
    """Return a fresh copy of the public content-policy JSON Schema."""
    resource = files(__package__).joinpath("content-policy.schema.json")
    payload = json.loads(resource.read_text(encoding="utf-8"))
    return cast(dict[str, Any], payload)


def load_approval_schema() -> dict[str, Any]:
    """Return a fresh copy of the public campaign-approval JSON Schema."""
    resource = files(__package__).joinpath("approval.schema.json")
    payload = json.loads(resource.read_text(encoding="utf-8"))
    return cast(dict[str, Any], payload)


def load_plan_approval_schema() -> dict[str, Any]:
    """Return a fresh copy of the public campaign-plan approval JSON Schema."""
    resource = files(__package__).joinpath("plan-approval.schema.json")
    payload = json.loads(resource.read_text(encoding="utf-8"))
    return cast(dict[str, Any], payload)


def load_handoff_schema() -> dict[str, Any]:
    """Return a fresh copy of the public approved-plan handoff JSON Schema."""
    resource = files(__package__).joinpath("handoff.schema.json")
    payload = json.loads(resource.read_text(encoding="utf-8"))
    return cast(dict[str, Any], payload)


def load_readiness_schema() -> dict[str, Any]:
    """Return a fresh copy of the public campaign-plan readiness JSON Schema."""
    resource = files(__package__).joinpath("readiness.schema.json")
    payload = json.loads(resource.read_text(encoding="utf-8"))
    return cast(dict[str, Any], payload)


def load_publication_schema() -> dict[str, Any]:
    """Return a fresh copy of the public plan-publication JSON Schema."""
    resource = files(__package__).joinpath("publication.schema.json")
    payload = json.loads(resource.read_text(encoding="utf-8"))
    return cast(dict[str, Any], payload)


def load_adapter_schema() -> dict[str, Any]:
    """Return a fresh copy of the public plan-adapter JSON Schema."""
    resource = files(__package__).joinpath("adapter.schema.json")
    payload = json.loads(resource.read_text(encoding="utf-8"))
    return cast(dict[str, Any], payload)
