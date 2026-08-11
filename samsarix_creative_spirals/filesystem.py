# Copyright (c) 2026 Samsarix LLC
# SPDX-License-Identifier: MPL-2.0

"""Small fail-closed helpers for local filesystem mutation boundaries."""

from __future__ import annotations

import stat
from pathlib import Path

DirectoryIdentity = tuple[int, int, int, int]


def is_link_like(path: Path) -> bool:
    """Return whether *path* is a symlink, junction, or other reparse point."""
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return False
    attributes = int(getattr(metadata, "st_file_attributes", 0))
    reparse_flag = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))
    junction_check = getattr(path, "is_junction", None)
    return bool(
        stat.S_ISLNK(metadata.st_mode)
        or (reparse_flag and attributes & reparse_flag)
        or (junction_check is not None and junction_check())
    )


def directory_identity(path: Path, *, label: str) -> DirectoryIdentity:
    """Capture one non-link directory identity without following reparse points."""
    try:
        metadata = path.lstat()
    except OSError as error:
        raise OSError(f"cannot inspect {label}: {error}") from error
    if is_link_like(path) or not stat.S_ISDIR(metadata.st_mode):
        raise OSError(f"{label} is not a directory or is link-like: {path}")
    return (
        int(metadata.st_dev),
        int(metadata.st_ino),
        int(metadata.st_mode),
        int(getattr(metadata, "st_file_attributes", 0)),
    )


def require_directory_identity(path: Path, expected: DirectoryIdentity, *, label: str) -> None:
    """Fail if a directory was replaced or became link-like since validation."""
    if directory_identity(path, label=label) != expected:
        raise OSError(f"{label} changed during the operation: {path}")
