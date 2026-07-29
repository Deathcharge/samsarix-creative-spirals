from __future__ import annotations

from typing import Any

import pytest


@pytest.fixture
def campaign_data() -> dict[str, Any]:
    return {
        "schemaVersion": 1,
        "name": "Release note",
        "title": "A small, useful release",
        "body": "We made the core workflow easier to review and safer to run.",
        "link": "https://example.com/release",
        "hashtags": ["shipping", "localfirst"],
        "platforms": ["x", "linkedin", "discord"],
    }
