# Copyright (c) 2026 Samsarix LLC
# SPDX-License-Identifier: MPL-2.0

"""Access to the packaged campaign and plan JSON Schemas."""

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
