# Copyright (c) 2026 Samsarix LLC
# SPDX-License-Identifier: MPL-2.0

"""Reproduce an offline first-use journey using only the installed CLI.

Run with the same Python environment used to install Samsarix. Every source and
outcome is synthetic; nothing is sent to a provider. Existing directories are
never reused or removed, including on failure, so diagnostic evidence is retained.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, cast


def command(*arguments: str, expected: int = 0) -> dict[str, Any]:
    """Run a bounded CLI step and enforce its expected exit and JSON contract."""
    result = subprocess.run(
        [sys.executable, "-m", "samsarix_creative_spirals", *arguments, "--json"],
        text=True,
        encoding="utf-8",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        capture_output=True,
        timeout=30,
        check=False,
    )
    if result.returncode != expected:
        raise RuntimeError(
            f"{arguments[:3]!r}: expected exit {expected}, got {result.returncode}; "
            f"stderr={result.stderr!r}; stdout={result.stdout!r}"
        )
    payload = json.loads(result.stdout)
    if not isinstance(payload, dict):
        raise RuntimeError(f"{arguments[:3]!r} did not emit a JSON object")
    return cast(dict[str, Any], payload)


def evaluate(output: Path) -> dict[str, Any]:
    """Retain a synthetic starter-to-reconciliation journey under a new directory."""
    output.mkdir(parents=True, exist_ok=False)
    initialized = command("plan", "init", str(output / "sources"), "--name", "Offline evaluation")
    plan = str(initialized["path"])
    check = command("plan", "check", plan)
    if check["publishable"] is not True:
        raise RuntimeError("Starter failed quality checks")

    # Fixed explicit times make the dry run independent of wall clock and local timezone.
    approval_path = str(output / "approval.json")
    command(
        "plan",
        "approval",
        "create",
        plan,
        "--by",
        "Evaluation reviewer (simulated)",
        "--at",
        "2030-01-01T09:00:00Z",
        "--output",
        approval_path,
    )
    command("plan", "approval", "verify", plan, approval_path)

    campaign_path = output / "sources" / "campaigns" / "001-announcement.json"
    original = campaign_path.read_bytes()
    changed = json.loads(original)
    changed["body"] += " This sentence was added after review."
    try:
        campaign_path.write_text(json.dumps(changed), encoding="utf-8")
        stale = command("plan", "approval", "verify", plan, approval_path, expected=4)
        if stale["valid"] is not False:
            raise RuntimeError("Changed source did not invalidate approval")
    finally:
        campaign_path.write_bytes(original)
    command("plan", "approval", "verify", plan, approval_path)

    handoff = command(
        "plan",
        "handoff",
        "create",
        plan,
        approval_path,
        "--at",
        "2030-01-01T09:05:00Z",
        "--output",
        str(output / "handoffs"),
    )
    packet = str(handoff["path"])
    command("plan", "handoff", "verify", plan, packet)
    ledger_path = str(output / "publication-0.json")
    ledger = command(
        "plan",
        "publication",
        "init",
        plan,
        packet,
        "--at",
        "2030-01-01T09:10:00Z",
        "--output",
        ledger_path,
    )
    pending = command(
        "plan",
        "publication",
        "verify",
        plan,
        packet,
        ledger_path,
        "--at",
        "2030-01-01T10:00:00Z",
        expected=4,
    )
    if pending["current"] is not True or pending["complete"] is not False:
        raise RuntimeError("Pending ledger state did not match expectations")

    for index, record in enumerate(ledger["publication"]["records"], start=1):
        next_path = str(output / f"publication-{index}.json")
        command(
            "plan",
            "publication",
            "record",
            plan,
            packet,
            ledger_path,
            "--item",
            str(record["sequence"]),
            "--platform",
            record["platform"],
            "--status",
            "skipped",
            "--by",
            "Evaluation operator (simulated)",
            "--at",
            "2030-01-01T09:15:00Z",
            "--assessed-at",
            "2030-01-01T10:00:00Z",
            "--note",
            "Dry run only. No provider was contacted and nothing was published.",
            "--output",
            next_path,
        )
        ledger_path = next_path
    complete = command(
        "plan",
        "publication",
        "verify",
        plan,
        packet,
        ledger_path,
        "--at",
        "2030-01-01T10:00:00Z",
    )
    status = command(
        "plan",
        "status",
        plan,
        "--handoff",
        packet,
        "--publication",
        ledger_path,
        "--at",
        "2030-01-01T10:00:00Z",
        "--require-stage",
        "publication",
        "--html",
        str(output / "readiness.html"),
    )
    if status["stage"] != "publication-complete" or complete["complete"] is not True:
        raise RuntimeError("Final completion gate failed")
    summary = {
        "kind": "synthetic-offline-evaluation",
        "planId": initialized["planId"],
        "items": initialized["items"],
        "records": complete["counts"]["records"],
        "stage": status["stage"],
        "staleApprovalRejected": True,
        "providerActions": 0,
        "publication": ledger_path,
        "board": str(output / "readiness.html"),
        "meaning": (
            "Technical dry run only; not user feedback, authenticated approval, or publishing."
        ),
    }
    with (output / "evaluation.json").open("x", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, required=True, help="new directory to retain artifacts"
    )
    args = parser.parse_args()
    try:
        summary = evaluate(args.output.absolute())
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
        print(f"Evaluation failed: {error!r}", file=sys.stderr)
        return 1
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
