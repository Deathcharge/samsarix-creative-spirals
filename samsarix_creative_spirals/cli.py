# Copyright (c) 2026 Samsarix LLC
# SPDX-License-Identifier: MPL-2.0

"""Command-line interface for Samsarix Creative Spirals."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from . import __version__
from .models import CampaignBundle, CampaignCheck, ConfigError
from .plans import (
    CampaignPlanBundle,
    CampaignPlanCheck,
    build_campaign_plan,
    check_campaign_plan,
    export_campaign_plan,
    load_campaign_plan,
)
from .quality import check_campaign
from .schema import load_campaign_schema, load_plan_schema
from .templates import starter_campaign
from .workflow import build_campaign, export_campaign, load_campaign


def _json_print(value: object) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def _print_preview(bundle: CampaignBundle) -> None:
    print(f"Campaign: {bundle.name}")
    print(f"ID: {bundle.campaign_id}")
    for draft in bundle.drafts:
        status = "truncated" if draft.truncated else "within limit"
        print(f"\n[{draft.platform}] {draft.character_count}/{draft.character_limit} ({status})")
        print("-" * 72)
        print(draft.content)
        for warning in draft.warnings:
            print(f"warning: {warning}")


def _print_check(result: CampaignCheck) -> None:
    status = "passed" if result.publishable else "failed"
    print(f"Quality check {status} for {result.campaign_id}")
    for issue in result.issues:
        print(f"{issue.severity}: [{issue.platform}] {issue.message}")


def _print_plan_preview(bundle: CampaignPlanBundle) -> None:
    print(f"Plan: {bundle.name}")
    print(f"ID: {bundle.plan_id}")
    for item in bundle.items:
        intended = (
            item.intended_at.isoformat().replace("+00:00", "Z")
            if item.intended_at
            else "unscheduled"
        )
        print(f"\nItem {item.sequence}: {item.bundle.name} ({intended})")
        _print_preview(item.bundle)


def _print_plan_check(result: CampaignPlanCheck) -> None:
    status = "passed" if result.publishable else "failed"
    print(f"Plan quality check {status} for {result.plan_id}")
    for issue in result.issues:
        platform = f" [{issue.platform}]" if issue.platform else ""
        print(f"{issue.severity}: item {issue.item}{platform} {issue.message}")


def _init_command(args: argparse.Namespace) -> int:
    path = Path(args.path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(starter_campaign(), ensure_ascii=False, indent=2) + "\n"
    try:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
    except FileExistsError:
        raise ConfigError(f"refusing to overwrite existing file: {path}") from None
    print(f"Created {path}")
    print(f"Next: samsarix-campaign preview {path}")
    return 0


def _validate_command(args: argparse.Namespace) -> int:
    bundle = build_campaign(load_campaign(args.config))
    if args.json:
        _json_print(
            {
                "valid": True,
                "campaignId": bundle.campaign_id,
                "platforms": [draft.platform for draft in bundle.drafts],
            }
        )
    else:
        platforms = ", ".join(draft.platform for draft in bundle.drafts)
        print(f"Valid campaign {bundle.campaign_id} ({platforms})")
    return 0


def _preview_command(args: argparse.Namespace) -> int:
    bundle = build_campaign(load_campaign(args.config))
    if args.json:
        _json_print(bundle.to_dict())
    else:
        _print_preview(bundle)
    return 0


def _check_command(args: argparse.Namespace) -> int:
    bundle = build_campaign(load_campaign(args.config))
    result = check_campaign(bundle, warnings_as_errors=args.warnings_as_errors)
    if args.json:
        _json_print(result.to_dict())
    else:
        _print_check(result)
    return 0 if result.publishable else 3


def _export_command(args: argparse.Namespace) -> int:
    bundle = build_campaign(load_campaign(args.config))
    path = export_campaign(bundle, args.output, overwrite=args.overwrite)
    if args.json:
        _json_print({"campaignId": bundle.campaign_id, "path": str(path)})
    else:
        print(f"Exported {bundle.campaign_id} to {path}")
    return 0


def _plan_validate_command(args: argparse.Namespace) -> int:
    bundle = build_campaign_plan(load_campaign_plan(args.plan))
    if args.json:
        _json_print(
            {
                "valid": True,
                "planId": bundle.plan_id,
                "items": len(bundle.items),
                "requiredPlatforms": list(bundle.required_platforms),
            }
        )
    else:
        print(f"Valid campaign plan {bundle.plan_id} ({len(bundle.items)} items)")
    return 0


def _plan_preview_command(args: argparse.Namespace) -> int:
    bundle = build_campaign_plan(load_campaign_plan(args.plan))
    if args.json:
        _json_print(bundle.to_dict())
    else:
        _print_plan_preview(bundle)
    return 0


def _plan_check_command(args: argparse.Namespace) -> int:
    bundle = build_campaign_plan(load_campaign_plan(args.plan))
    result = check_campaign_plan(bundle, warnings_as_errors=args.warnings_as_errors)
    if args.json:
        _json_print(result.to_dict())
    else:
        _print_plan_check(result)
    return 0 if result.publishable else 3


def _plan_export_command(args: argparse.Namespace) -> int:
    bundle = build_campaign_plan(load_campaign_plan(args.plan))
    path = export_campaign_plan(bundle, args.output, overwrite=args.overwrite)
    if args.json:
        _json_print({"planId": bundle.plan_id, "path": str(path)})
    else:
        print(f"Exported {bundle.plan_id} to {path}")
    return 0


def _schema_command(args: argparse.Namespace) -> int:
    schema = load_plan_schema() if args.kind == "plan" else load_campaign_schema()
    if args.output is None:
        _json_print(schema)
        return 0

    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(schema, ensure_ascii=False, indent=2) + "\n"
    try:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
    except FileExistsError:
        raise ConfigError(f"refusing to overwrite existing file: {path}") from None
    print(f"Wrote {args.kind} schema to {path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the public argument parser."""
    parser = argparse.ArgumentParser(
        prog="samsarix-campaign",
        description=(
            "Review and export campaigns or launch sequences for social platforms, locally."
        ),
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command")

    init_parser = subparsers.add_parser("init", help="create a starter campaign JSON file")
    init_parser.add_argument("path", nargs="?", default="campaign.json")
    init_parser.set_defaults(handler=_init_command)

    validate_parser = subparsers.add_parser(
        "validate", help="validate a campaign without writing files"
    )
    validate_parser.add_argument("config")
    validate_parser.add_argument("--json", action="store_true", help="emit machine-readable output")
    validate_parser.set_defaults(handler=_validate_command)

    preview_parser = subparsers.add_parser("preview", help="render drafts without writing files")
    preview_parser.add_argument("config")
    preview_parser.add_argument("--json", action="store_true", help="emit machine-readable output")
    preview_parser.set_defaults(handler=_preview_command)

    check_parser = subparsers.add_parser(
        "check", help="fail when generated drafts require quality intervention"
    )
    check_parser.add_argument("config")
    check_parser.add_argument(
        "--warnings-as-errors",
        action="store_true",
        help="also fail on non-truncation review warnings",
    )
    check_parser.add_argument("--json", action="store_true", help="emit machine-readable output")
    check_parser.set_defaults(handler=_check_command)

    export_parser = subparsers.add_parser("export", help="write a reviewable local outbox bundle")
    export_parser.add_argument("config")
    export_parser.add_argument("--output", default="outbox", help="output root (default: outbox)")
    export_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="replace an existing bundle with the same deterministic ID",
    )
    export_parser.add_argument("--json", action="store_true", help="emit machine-readable output")
    export_parser.set_defaults(handler=_export_command)

    plan_parser = subparsers.add_parser(
        "plan", help="validate, preview, check, or export a multi-campaign plan"
    )
    plan_subparsers = plan_parser.add_subparsers(dest="plan_command")

    plan_validate_parser = plan_subparsers.add_parser(
        "validate", help="validate a plan and all referenced campaigns"
    )
    plan_validate_parser.add_argument("plan")
    plan_validate_parser.add_argument(
        "--json", action="store_true", help="emit machine-readable output"
    )
    plan_validate_parser.set_defaults(handler=_plan_validate_command)

    plan_preview_parser = plan_subparsers.add_parser(
        "preview", help="render the complete campaign sequence without writing files"
    )
    plan_preview_parser.add_argument("plan")
    plan_preview_parser.add_argument(
        "--json", action="store_true", help="emit machine-readable output"
    )
    plan_preview_parser.set_defaults(handler=_plan_preview_command)

    plan_check_parser = plan_subparsers.add_parser(
        "check", help="run aggregate campaign and plan quality gates"
    )
    plan_check_parser.add_argument("plan")
    plan_check_parser.add_argument(
        "--warnings-as-errors",
        action="store_true",
        help="also fail on duplicate times, ordering, and review warnings",
    )
    plan_check_parser.add_argument(
        "--json", action="store_true", help="emit machine-readable output"
    )
    plan_check_parser.set_defaults(handler=_plan_check_command)

    plan_export_parser = plan_subparsers.add_parser(
        "export", help="write a plan manifest, calendar, and per-platform CSV files"
    )
    plan_export_parser.add_argument("plan")
    plan_export_parser.add_argument(
        "--output", default="plan-outbox", help="output root (default: plan-outbox)"
    )
    plan_export_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="replace an existing plan bundle with the same deterministic ID",
    )
    plan_export_parser.add_argument(
        "--json", action="store_true", help="emit machine-readable output"
    )
    plan_export_parser.set_defaults(handler=_plan_export_command)

    schema_parser = subparsers.add_parser(
        "schema", help="print or write a bundled campaign or plan JSON Schema"
    )
    schema_parser.add_argument(
        "--kind", choices=("campaign", "plan"), default="campaign", help="schema to emit"
    )
    schema_parser.add_argument("--output", help="write to a new file instead of standard output")
    schema_parser.set_defaults(handler=_schema_command)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and return a meaningful process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "handler"):
        parser.print_help(sys.stderr)
        return 2
    try:
        return int(args.handler(args))
    except (ConfigError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    except BrokenPipeError:
        return 0
