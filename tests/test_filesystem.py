from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from samsarix_creative_spirals.filesystem import is_link_like


@pytest.mark.skipif(os.name != "nt", reason="Windows junction semantics")
def test_windows_junction_is_treated_as_link_like(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.mkdir()
    sentinel = target / "sentinel.txt"
    sentinel.write_text("keep", encoding="utf-8")
    junction = tmp_path / "junction"
    result = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(junction), str(target)],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        pytest.skip("directory junctions are not available in this environment")
    try:
        assert is_link_like(junction) is True
    finally:
        junction.rmdir()
    assert sentinel.read_text(encoding="utf-8") == "keep"
