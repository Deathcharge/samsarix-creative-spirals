# Copyright (c) 2026 Samsarix LLC
# SPDX-License-Identifier: MPL-2.0

"""Command-line interface for Samsarix Creative Spirals."""

from __future__ import annotations

import argparse
import json
import sys
import unicodedata
from collections.abc import Sequence
from pathlib import Path

from . import __version__
from .approval_policy import (
    CampaignPlanApprovalAssignment,
    PlanApprovalEvidenceCheck,
    PlanApprovalSetCheck,
    create_campaign_plan_approval_set,
    export_campaign_plan_approval_set,
    load_approval_policy,
    load_campaign_plan_approval_evidence,
    verify_campaign_plan_approval_evidence,
)
from .handoff import (
    HandoffCheck,
    export_campaign_plan_handoff,
    load_campaign_plan_handoff,
    verify_campaign_plan_handoff,
)
from .media_package import collect_campaign_plan_media
from .models import CampaignBundle, CampaignCheck, ConfigError
from .policy import ContentPolicy, load_content_policy
from .plans import (
    CampaignPlanBundle,
    CampaignPlanCheck,
    build_campaign_plan,
    check_campaign_plan,
    export_campaign_plan,
    load_campaign_plan,
)
from .plan_review import (
    CampaignPlanDiff,
    create_campaign_plan_approval,
    diff_campaign_plans,
    export_campaign_plan_approval,
    load_campaign_plan_approval,
)
from .plan_feedback import (
    PlanReviewFinding,
    create_campaign_plan_review,
    export_campaign_plan_review,
    load_campaign_plan_review,
    parse_plan_review_timestamp,
    verify_campaign_plan_review,
)
from .plan_import import export_campaign_plan_import, inspect_campaign_plan_csv
from .quality import check_campaign
from .publication import (
    PublicationCheck,
    export_campaign_plan_publication,
    initialize_campaign_plan_publication,
    load_campaign_plan_publication,
    verify_campaign_plan_publication,
)
from .readiness import (
    CampaignPlanReadiness,
    build_campaign_plan_readiness,
    export_campaign_plan_readiness_html,
)
from .review import (
    ApprovalCheck,
    CampaignDiff,
    create_campaign_approval,
    diff_campaigns,
    export_campaign_approval,
    load_campaign_approval,
    parse_approval_timestamp,
    verify_campaign_approval,
)
from .schema import (
    load_adapter_schema,
    load_approval_policy_schema,
    load_approval_schema,
    load_campaign_schema,
    load_content_policy_schema,
    load_handoff_schema,
    load_media_package_schema,
    load_plan_approval_schema,
    load_plan_approval_set_schema,
    load_plan_import_schema,
    load_plan_review_schema,
    load_plan_schema,
    load_publication_schema,
    load_readiness_schema,
)
from .templates import starter_campaign
from .workflow import build_campaign, export_campaign, load_campaign


def _terminal_safe(value: object) -> str:
    """Render untrusted diagnostics without emitting terminal control characters."""
    result: list[str] = []
    for character in str(value):
        category = unicodedata.category(character)
        if category in {"Cc", "Cf", "Cs"} or ord(character) == 127:
            codepoint = ord(character)
            result.append(f"\\x{codepoint:02x}" if codepoint <= 0xFF else f"\\u{codepoint:04x}")
        else:
            result.append(character)
    return "".join(result)


def _json_print(value: object) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def _optional_content_policy(args: argparse.Namespace) -> ContentPolicy | None:
    path = getattr(args, "policy", None)
    return load_content_policy(path) if path else None


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
    if result.content_policy is not None:
        print(f"Content policy: {result.content_policy.name} ({result.content_policy.policy_id})")
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
    if result.content_policy is not None:
        print(f"Content policy: {result.content_policy.name} ({result.content_policy.policy_id})")
    for issue in result.issues:
        platform = f" [{issue.platform}]" if issue.platform else ""
        print(f"{issue.severity}: item {issue.item}{platform} {issue.message}")


def _display_diff_value(value: object) -> str:
    rendered = json.dumps(value, ensure_ascii=False, sort_keys=True)
    if len(rendered) <= 180:
        return rendered
    return f"{rendered[:177]}... ({len(rendered)} characters)"


def _print_diff(result: CampaignDiff) -> None:
    if not result.changed:
        print(f"No semantic changes ({result.before_campaign_id})")
        return
    print(f"Campaign changed: {result.before_campaign_id} -> {result.after_campaign_id}")
    for field_change in result.fields:
        print(
            f"field {field_change.field}: {_display_diff_value(field_change.before)} -> "
            f"{_display_diff_value(field_change.after)}"
        )
    for draft_change in result.drafts:
        fields = ", ".join(draft_change.fields)
        print(f"draft {draft_change.platform}: {draft_change.change} ({fields})")


def _print_approval_check(result: ApprovalCheck) -> None:
    status = "valid" if result.valid else "invalid"
    print(
        f"Approval {status} for {result.campaign_id}: "
        f"{result.approval.approved_by} at {result.approval.to_dict()['approvedAt']}"
    )
    for issue in result.issues:
        print(f"error: {issue.message}")


def _print_plan_diff(result: CampaignPlanDiff) -> None:
    if not result.changed:
        print(f"No semantic changes ({result.before_plan_id})")
        return
    print(f"Plan changed: {result.before_plan_id} -> {result.after_plan_id}")
    for field_change in result.fields:
        print(
            f"field {field_change.field}: {_display_diff_value(field_change.before)} -> "
            f"{_display_diff_value(field_change.after)}"
        )
    for item_change in result.items:
        fields = ", ".join(item_change.fields)
        print(f"item {item_change.sequence}: {item_change.change} ({fields})")
        if item_change.campaign_diff is not None:
            for campaign_field_change in item_change.campaign_diff.fields:
                print(f"  campaign field {campaign_field_change.field}")
            for draft_change in item_change.campaign_diff.drafts:
                draft_fields = ", ".join(draft_change.fields)
                print(f"  draft {draft_change.platform}: {draft_change.change} ({draft_fields})")


def _print_plan_approval_check(result: PlanApprovalEvidenceCheck) -> None:
    status = "valid" if result.valid else "invalid"
    if isinstance(result, PlanApprovalSetCheck):
        approval_set = result.approval_set
        print(
            f"Plan approval set {status} for {result.plan_id}: "
            f"{approval_set.approval_set_id} with {len(approval_set.approvals)} reviewers"
        )
    else:
        approval = result.approval
        print(
            f"Plan approval {status} for {result.plan_id}: "
            f"{approval.approved_by} at {approval.to_dict()['approvedAt']}"
        )
    for issue in result.issues:
        print(f"error: {issue.message}")


def _print_handoff_check(result: HandoffCheck) -> None:
    status = "valid" if result.valid else "invalid"
    print(f"Approved handoff {status} for {result.plan_id}: {result.handoff_id}")
    for issue in result.issues:
        location = f" [{_terminal_safe(issue.path)}]" if issue.path else ""
        print(f"error:{location} {_terminal_safe(issue.message)}")


def _print_publication_check(result: PublicationCheck) -> None:
    status = "complete" if result.complete else ("in progress" if result.current else "invalid")
    counts = dict(result.counts)
    print(f"Publication ledger {status} for {result.plan_id}: {result.publication_id}")
    print(
        f"Published: {counts['published']}; skipped: {counts['skipped']}; "
        f"pending: {counts['pending']}; failed: {counts['failed']}"
    )
    for issue in result.issues:
        location = (
            f" item {issue.item} [{issue.platform}]"
            if issue.item is not None and issue.platform is not None
            else ""
        )
        print(f"{issue.severity}:{location} {issue.message}")


def _print_plan_readiness(result: CampaignPlanReadiness) -> None:
    print(f"Launch readiness: {result.stage.replace('-', ' ')} for {result.plan_id}")
    if result.content_policy is not None:
        print(f"Content policy: {result.content_policy.name} ({result.content_policy.policy_id})")
    print(
        f"Quality: {'passed' if result.quality_passed else 'blocked'}; "
        f"schedule: {'ready' if result.schedule_ready else 'blocked'}; "
        f"approval: {result.approval_status}; handoff: {result.handoff_status}"
    )
    if result.publication_status != "not-provided":
        print(
            f"Publication: {result.publication_status}"
            + (f" ({result.publication_id})" if result.publication_id else "")
        )
    for issue in result.issues:
        location = f" item {issue.item}" if issue.item is not None else ""
        path = f" [{issue.path}]" if issue.path else ""
        print(f"{issue.severity}:{location}{path} {issue.message}")


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
    result = check_campaign(
        bundle,
        warnings_as_errors=args.warnings_as_errors,
        content_policy=_optional_content_policy(args),
    )
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


def _diff_command(args: argparse.Namespace) -> int:
    result = diff_campaigns(load_campaign(args.before), load_campaign(args.after))
    if args.json:
        _json_print(result.to_dict())
    else:
        _print_diff(result)
    return 4 if args.exit_code and result.changed else 0


def _approval_create_command(args: argparse.Namespace) -> int:
    bundle = build_campaign(load_campaign(args.config))
    approved_at = parse_approval_timestamp(args.approved_at) if args.approved_at else None
    approval = create_campaign_approval(
        bundle,
        approved_by=args.approved_by,
        approved_at=approved_at,
        warnings_as_errors=args.warnings_as_errors,
        note=args.note,
        content_policy=_optional_content_policy(args),
    )
    output = Path(args.output) if args.output else Path(f"{args.config}.approval.json")
    path = export_campaign_approval(approval, output)
    if args.json:
        _json_print({"path": str(path), "approval": approval.to_dict()})
    else:
        print(f"Recorded local approval for {bundle.campaign_id} in {path}")
        print("This record is source-bound review metadata, not a digital signature.")
    return 0


def _approval_verify_command(args: argparse.Namespace) -> int:
    bundle = build_campaign(load_campaign(args.config))
    result = verify_campaign_approval(
        bundle,
        load_campaign_approval(args.approval),
        content_policy=_optional_content_policy(args),
    )
    if args.json:
        _json_print(result.to_dict())
    else:
        _print_approval_check(result)
    return 0 if result.valid else 4


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
    result = check_campaign_plan(
        bundle,
        warnings_as_errors=args.warnings_as_errors,
        content_policy=_optional_content_policy(args),
    )
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


def _plan_import_command(args: argparse.Namespace) -> int:
    check = inspect_campaign_plan_csv(
        args.csv,
        name=args.name,
        required_platforms=args.required_platforms,
    )
    if not check.valid:
        if args.json:
            _json_print(check.to_dict())
        else:
            print(f"CSV import invalid ({len(check.issues)} issue(s))")
            for issue in check.issues:
                location = f"row {issue.row}" if issue.row is not None else "file"
                if issue.field is not None:
                    location += f".{issue.field}"
                print(f"- {issue.code} [{location}]: {issue.message}")
        return 1
    assert check.imported is not None
    output = args.output or f"{Path(args.csv).stem}-import"
    plan_path = export_campaign_plan_import(check.imported, output)
    bundle = build_campaign_plan(load_campaign_plan(plan_path))
    if args.json:
        _json_print(
            {
                "check": check.to_dict(),
                "path": str(plan_path),
                "planId": bundle.plan_id,
            }
        )
    else:
        print(f"Imported {check.row_count} campaign(s) into {plan_path}")
        print(f"Validated campaign plan {bundle.plan_id}")
    return 0


def _plan_diff_command(args: argparse.Namespace) -> int:
    result = diff_campaign_plans(
        load_campaign_plan(args.before),
        load_campaign_plan(args.after),
    )
    if args.json:
        _json_print(result.to_dict())
    else:
        _print_plan_diff(result)
    return 4 if args.exit_code and result.changed else 0


def _plan_approval_create_command(args: argparse.Namespace) -> int:
    plan_path = Path(args.plan)
    bundle = build_campaign_plan(load_campaign_plan(plan_path))
    approved_at = parse_approval_timestamp(args.approved_at) if args.approved_at else None
    media = (
        collect_campaign_plan_media(bundle, plan_path.resolve().parent).index
        if args.include_media
        else None
    )
    approval = create_campaign_plan_approval(
        bundle,
        approved_by=args.approved_by,
        approved_at=approved_at,
        warnings_as_errors=args.warnings_as_errors,
        note=args.note,
        content_policy=_optional_content_policy(args),
        media=media,
    )
    output = Path(args.output) if args.output else Path(f"{args.plan}.approval.json")
    path = export_campaign_plan_approval(approval, output)
    if args.json:
        _json_print({"path": str(path), "approval": approval.to_dict()})
    else:
        print(f"Recorded local plan approval for {bundle.plan_id} in {path}")
        if approval.media is not None:
            print(
                f"Exact media: {approval.media.media_id} "
                f"({approval.media.asset_count} references, {approval.media.total_bytes} bytes)"
            )
        print("This record is source-bound review metadata, not a digital signature.")
    return 0


def _plan_approval_verify_command(args: argparse.Namespace) -> int:
    plan_path = Path(args.plan)
    bundle = build_campaign_plan(load_campaign_plan(plan_path))
    approval = load_campaign_plan_approval_evidence(args.approval)
    media = (
        collect_campaign_plan_media(bundle, plan_path.resolve().parent).index
        if approval.media is not None
        else None
    )
    result = verify_campaign_plan_approval_evidence(
        bundle,
        approval,
        content_policy=_optional_content_policy(args),
        media=media,
    )
    if args.json:
        _json_print(result.to_dict())
    else:
        _print_plan_approval_check(result)
    return 0 if result.valid else 4


def _plan_approval_collect_command(args: argparse.Namespace) -> int:
    plan_path = Path(args.plan)
    bundle = build_campaign_plan(load_campaign_plan(plan_path))
    assignments: list[CampaignPlanApprovalAssignment] = []
    for value in args.approvals:
        role, separator, path = value.partition("=")
        if not separator or not role or not path:
            raise ConfigError("each --approval must use ROLE=PATH")
        assignments.append(CampaignPlanApprovalAssignment(role, load_campaign_plan_approval(path)))
    media = (
        collect_campaign_plan_media(bundle, plan_path.resolve().parent).index
        if any(assignment.approval.media is not None for assignment in assignments)
        else None
    )
    approval_set = create_campaign_plan_approval_set(
        bundle,
        load_approval_policy(args.approval_policy),
        assignments,
        content_policy=_optional_content_policy(args),
        media=media,
    )
    output = Path(args.output) if args.output else Path(f"{args.plan}.approval-set.json")
    path = export_campaign_plan_approval_set(approval_set, output)
    if args.json:
        _json_print({"path": str(path), "approvalSet": approval_set.to_dict()})
    else:
        print(
            f"Collected {len(approval_set.approvals)} approvals into "
            f"{approval_set.approval_set_id} in {path}"
        )
        print(
            f"Approval policy: {approval_set.approval_policy.name} "
            f"({approval_set.approval_policy.policy_id})"
        )
        print("Reviewer labels and roles are local metadata, not authenticated identities.")
    return 0


def _plan_review_create_command(args: argparse.Namespace) -> int:
    plan_path = Path(args.plan)
    bundle = build_campaign_plan(load_campaign_plan(plan_path))
    if args.suggestion is not None and len(args.findings) != 1:
        raise ConfigError("--suggestion requires exactly one --finding")
    findings = tuple(
        PlanReviewFinding(
            message=message,
            item=args.item,
            platform=args.platform,
            suggestion=args.suggestion if index == 0 else None,
        )
        for index, message in enumerate(args.findings)
    )
    media = (
        collect_campaign_plan_media(bundle, plan_path.resolve().parent).index
        if args.include_media
        else None
    )
    reviewed_at = parse_plan_review_timestamp(args.reviewed_at) if args.reviewed_at else None
    review = create_campaign_plan_review(
        bundle,
        decision=args.decision,
        reviewed_by=args.reviewed_by,
        reviewed_at=reviewed_at,
        findings=findings,
        note=args.note,
        media=media,
    )
    output = (
        Path(args.output) if args.output else Path(f"{args.plan}.{review.review_id}.review.json")
    )
    path = export_campaign_plan_review(review, output)
    if args.json:
        _json_print({"path": str(path), "review": review.to_dict()})
    else:
        print(
            f"Recorded {review.decision} review {review.review_id} for "
            f"{bundle.plan_id} in {path}"
        )
        if review.media is not None:
            print(
                f"Exact media: {review.media.media_id} "
                f"({review.media.asset_count} references, {review.media.total_bytes} bytes)"
            )
        print("This record is source-bound feedback metadata, not authenticated identity.")
    return 0


def _plan_review_verify_command(args: argparse.Namespace) -> int:
    plan_path = Path(args.plan)
    bundle = build_campaign_plan(load_campaign_plan(plan_path))
    review = load_campaign_plan_review(args.review)
    media = (
        collect_campaign_plan_media(bundle, plan_path.resolve().parent).index
        if review.media is not None
        else None
    )
    result = verify_campaign_plan_review(bundle, review, media=media)
    if args.json:
        _json_print(result.to_dict())
    elif result.valid:
        state = "blocking" if result.blocking else "informational"
        print(f"Review valid for {bundle.plan_id}: {review.decision} ({state})")
    else:
        print(f"Review invalid for {bundle.plan_id}")
        for issue in result.issues:
            print(f"- {issue.code}: {issue.message}")
    if not result.valid or (args.fail_on_blocking and result.blocking):
        return 4
    return 0


def _plan_handoff_create_command(args: argparse.Namespace) -> int:
    plan_path = Path(args.plan)
    bundle = build_campaign_plan(load_campaign_plan(plan_path))
    approval = load_campaign_plan_approval_evidence(args.approval)
    media = (
        collect_campaign_plan_media(bundle, plan_path.resolve().parent)
        if approval.media is not None
        else None
    )
    generated_at = parse_approval_timestamp(args.generated_at) if args.generated_at else None
    path = export_campaign_plan_handoff(
        bundle,
        approval,
        args.output,
        generated_at=generated_at,
        content_policy=_optional_content_policy(args),
        media=media,
    )
    packet = load_campaign_plan_handoff(path)
    if args.json:
        _json_print({"path": str(path), "handoff": packet.handoff.to_dict()})
    else:
        print(f"Exported approved handoff {packet.handoff.handoff_id} to {path}")
        if packet.media is not None:
            print(
                f"Packaged exact media: {packet.media.media_id} "
                f"({len(packet.media.assets)} references, {packet.media.total_bytes} bytes)"
            )
        print("Checksums provide offline integrity, not signer identity or provenance.")
    return 0


def _plan_handoff_verify_command(args: argparse.Namespace) -> int:
    bundle = build_campaign_plan(load_campaign_plan(args.plan))
    result = verify_campaign_plan_handoff(
        bundle,
        load_campaign_plan_handoff(args.handoff),
        content_policy=_optional_content_policy(args),
    )
    if args.json:
        _json_print(result.to_dict())
    else:
        _print_handoff_check(result)
    return 0 if result.valid else 4


def _plan_publication_init_command(args: argparse.Namespace) -> int:
    bundle = build_campaign_plan(load_campaign_plan(args.plan))
    packet = load_campaign_plan_handoff(args.handoff)
    created_at = parse_approval_timestamp(args.created_at) if args.created_at else None
    publication = initialize_campaign_plan_publication(
        bundle,
        packet,
        created_at=created_at,
        content_policy=_optional_content_policy(args),
    )
    output = Path(args.output) if args.output else Path(f"{args.plan}.publication.json")
    path = export_campaign_plan_publication(publication, output)
    if args.json:
        _json_print(
            {
                "path": str(path),
                "publicationId": publication.publication_id,
                "publication": publication.to_dict(),
            }
        )
    else:
        print(f"Initialized publication ledger {publication.publication_id} in {path}")
        print("Edit each pending record, then run plan publication verify.")
        print("This is unsigned operator metadata, not platform-verified proof.")
    return 0


def _plan_publication_verify_command(args: argparse.Namespace) -> int:
    bundle = build_campaign_plan(load_campaign_plan(args.plan))
    assessed_at = parse_approval_timestamp(args.assessed_at) if args.assessed_at else None
    result = verify_campaign_plan_publication(
        bundle,
        load_campaign_plan_handoff(args.handoff),
        load_campaign_plan_publication(args.publication),
        assessed_at=assessed_at,
        content_policy=_optional_content_policy(args),
    )
    if args.json:
        _json_print(result.to_dict())
    else:
        _print_publication_check(result)
    return 0 if result.complete else 4


def _plan_status_command(args: argparse.Namespace) -> int:
    plan_path = Path(args.plan)
    bundle = build_campaign_plan(load_campaign_plan(plan_path))
    approval = load_campaign_plan_approval_evidence(args.approval) if args.approval else None
    handoff = load_campaign_plan_handoff(args.handoff) if args.handoff else None
    publication = load_campaign_plan_publication(args.publication) if args.publication else None
    assessed_at = parse_approval_timestamp(args.assessed_at) if args.assessed_at else None
    media = (
        collect_campaign_plan_media(bundle, plan_path.resolve().parent).index
        if approval is not None and approval.media is not None and handoff is None
        else None
    )
    result = build_campaign_plan_readiness(
        bundle,
        approval=approval,
        handoff=handoff,
        publication=publication,
        assessed_at=assessed_at,
        warnings_as_errors=args.warnings_as_errors,
        require_scheduled=args.require_scheduled,
        content_policy=_optional_content_policy(args),
        media=media,
    )
    if args.html:
        export_campaign_plan_readiness_html(result, bundle, args.html)
    if args.json:
        _json_print(result.to_dict())
    else:
        _print_plan_readiness(result)
        if args.html:
            print(f"Wrote offline readiness report to {args.html}")
    if args.require_stage is None or result.meets(args.require_stage):
        return 0
    return 3 if args.require_stage == "quality" else 4


def _schema_command(args: argparse.Namespace) -> int:
    schema_loaders = {
        "adapter": load_adapter_schema,
        "approval": load_approval_schema,
        "approval-policy": load_approval_policy_schema,
        "campaign": load_campaign_schema,
        "content-policy": load_content_policy_schema,
        "handoff": load_handoff_schema,
        "media-package": load_media_package_schema,
        "plan": load_plan_schema,
        "plan-approval": load_plan_approval_schema,
        "plan-approval-set": load_plan_approval_set_schema,
        "plan-import": load_plan_import_schema,
        "plan-review": load_plan_review_schema,
        "publication": load_publication_schema,
        "readiness": load_readiness_schema,
    }
    schema = schema_loaders[args.kind]()
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


def _policy_validate_command(args: argparse.Namespace) -> int:
    policy = load_content_policy(args.policy)
    if args.json:
        _json_print({"valid": True, "contentPolicy": policy.binding.to_dict()})
    else:
        print(
            f"Valid content policy {policy.policy_id}: {policy.name} "
            f"({len(policy.rules)} rules)"
        )
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
    check_parser.add_argument("--policy", help="optional local content-policy JSON")
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

    diff_parser = subparsers.add_parser(
        "diff", help="compare normalized campaign source and generated drafts"
    )
    diff_parser.add_argument("before")
    diff_parser.add_argument("after")
    diff_parser.add_argument("--json", action="store_true", help="emit machine-readable output")
    diff_parser.add_argument(
        "--exit-code",
        action="store_true",
        help="return exit code 4 when semantic changes are present",
    )
    diff_parser.set_defaults(handler=_diff_command)

    approval_parser = subparsers.add_parser(
        "approval", help="create or verify source-bound local approval metadata"
    )
    approval_subparsers = approval_parser.add_subparsers(dest="approval_command")
    approval_create_parser = approval_subparsers.add_parser(
        "create", help="record approval after the selected quality policy passes"
    )
    approval_create_parser.add_argument("config")
    approval_create_parser.add_argument(
        "--policy", help="content policy to evaluate and bind to this approval"
    )
    approval_create_parser.add_argument(
        "--by", dest="approved_by", required=True, help="human-readable reviewer label"
    )
    approval_create_parser.add_argument(
        "--at", dest="approved_at", help="explicit RFC 3339 approval time (default: now)"
    )
    approval_create_parser.add_argument("--note", help="optional review note (maximum 500 chars)")
    approval_create_parser.add_argument(
        "--warnings-as-errors",
        action="store_true",
        help="require a warning-free campaign and record that stricter policy",
    )
    approval_create_parser.add_argument(
        "--output", help="new approval file (default: CONFIG.approval.json)"
    )
    approval_create_parser.add_argument(
        "--json", action="store_true", help="emit machine-readable output"
    )
    approval_create_parser.set_defaults(handler=_approval_create_command)

    approval_verify_parser = approval_subparsers.add_parser(
        "verify", help="verify an approval against current source and its quality policy"
    )
    approval_verify_parser.add_argument("config")
    approval_verify_parser.add_argument("approval")
    approval_verify_parser.add_argument(
        "--policy", help="exact content policy bound to the approval, when present"
    )
    approval_verify_parser.add_argument(
        "--json", action="store_true", help="emit machine-readable output"
    )
    approval_verify_parser.set_defaults(handler=_approval_verify_command)

    plan_parser = subparsers.add_parser(
        "plan", help="validate, review, approve, or export a multi-campaign plan"
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
    plan_check_parser.add_argument("--policy", help="optional local content-policy JSON")
    plan_check_parser.add_argument(
        "--warnings-as-errors",
        action="store_true",
        help="also fail on duplicate times, ordering, and review warnings",
    )
    plan_check_parser.add_argument(
        "--json", action="store_true", help="emit machine-readable output"
    )
    plan_check_parser.set_defaults(handler=_plan_check_command)

    plan_import_parser = plan_subparsers.add_parser(
        "import", help="atomically import a canonical UTF-8 CSV into campaign and plan sources"
    )
    plan_import_parser.add_argument("csv", help="canonical Samsarix authoring CSV")
    plan_import_parser.add_argument("--name", required=True, help="campaign-plan name")
    plan_import_parser.add_argument(
        "--required-platform",
        dest="required_platforms",
        action="append",
        default=[],
        choices=("x", "linkedin", "bluesky", "mastodon", "discord"),
        help="require every imported campaign to request this platform; repeat as needed",
    )
    plan_import_parser.add_argument(
        "--output", help="new source-package directory (default: CSV stem plus -import)"
    )
    plan_import_parser.add_argument(
        "--json", action="store_true", help="emit machine-readable diagnostics and result"
    )
    plan_import_parser.set_defaults(handler=_plan_import_command)

    plan_status_parser = plan_subparsers.add_parser(
        "status", help="assess launch readiness and optionally write an offline HTML board"
    )
    plan_status_parser.add_argument("plan")
    plan_status_parser.add_argument(
        "--policy", help="content policy to assess and verify against evidence"
    )
    plan_status_parser.add_argument("--approval", help="optional source-bound plan approval JSON")
    plan_status_parser.add_argument("--handoff", help="optional approved handoff packet directory")
    plan_status_parser.add_argument(
        "--publication", help="optional handoff-bound publication ledger JSON"
    )
    plan_status_parser.add_argument(
        "--at", dest="assessed_at", help="explicit RFC 3339 assessment time (default: now)"
    )
    plan_status_parser.add_argument(
        "--warnings-as-errors",
        action="store_true",
        help="apply the strict warning-free quality policy to this status view",
    )
    plan_status_parser.add_argument(
        "--require-scheduled",
        action="store_true",
        help="treat every unscheduled plan item as a blocker",
    )
    plan_status_parser.add_argument(
        "--require-stage",
        choices=("quality", "approval", "handoff", "publication"),
        help="return a nonzero CI exit code unless this readiness gate is met",
    )
    plan_status_parser.add_argument(
        "--html", help="write a new self-contained, offline HTML status board"
    )
    plan_status_parser.add_argument(
        "--json", action="store_true", help="emit the readiness JSON contract"
    )
    plan_status_parser.set_defaults(handler=_plan_status_command)

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

    plan_diff_parser = plan_subparsers.add_parser(
        "diff", help="compare plan metadata, order, schedules, and campaign semantics"
    )
    plan_diff_parser.add_argument("before")
    plan_diff_parser.add_argument("after")
    plan_diff_parser.add_argument(
        "--json", action="store_true", help="emit machine-readable output"
    )
    plan_diff_parser.add_argument(
        "--exit-code",
        action="store_true",
        help="return exit code 4 when semantic changes are present",
    )
    plan_diff_parser.set_defaults(handler=_plan_diff_command)

    plan_approval_parser = plan_subparsers.add_parser(
        "approval", help="create or verify source-bound plan approval metadata"
    )
    plan_approval_subparsers = plan_approval_parser.add_subparsers(dest="plan_approval_command")
    plan_approval_create_parser = plan_approval_subparsers.add_parser(
        "create", help="record approval after the complete plan quality policy passes"
    )
    plan_approval_create_parser.add_argument("plan")
    plan_approval_create_parser.add_argument(
        "--policy", help="content policy to evaluate and bind to this approval"
    )
    plan_approval_create_parser.add_argument(
        "--by", dest="approved_by", required=True, help="human-readable reviewer label"
    )
    plan_approval_create_parser.add_argument(
        "--at", dest="approved_at", help="explicit RFC 3339 approval time (default: now)"
    )
    plan_approval_create_parser.add_argument(
        "--note", help="optional review note (maximum 500 chars)"
    )
    plan_approval_create_parser.add_argument(
        "--warnings-as-errors",
        action="store_true",
        help="require a warning-free plan and record that stricter policy",
    )
    plan_approval_create_parser.add_argument(
        "--include-media",
        action="store_true",
        help="inspect and bind exact referenced JPEG/PNG bytes to this approval",
    )
    plan_approval_create_parser.add_argument(
        "--output", help="new approval file (default: PLAN.approval.json)"
    )
    plan_approval_create_parser.add_argument(
        "--json", action="store_true", help="emit machine-readable output"
    )
    plan_approval_create_parser.set_defaults(handler=_plan_approval_create_command)

    plan_approval_collect_parser = plan_approval_subparsers.add_parser(
        "collect", help="combine independent approvals under a reusable role policy"
    )
    plan_approval_collect_parser.add_argument("plan")
    plan_approval_collect_parser.add_argument(
        "--approval-policy",
        required=True,
        help="approval-policy JSON defining roles, minima, and reviewer distinctness",
    )
    plan_approval_collect_parser.add_argument(
        "--approval",
        dest="approvals",
        action="append",
        required=True,
        metavar="ROLE=PATH",
        help="assign one existing single-reviewer approval to a role; repeat as needed",
    )
    plan_approval_collect_parser.add_argument(
        "--policy", help="exact content policy bound to every approval, when present"
    )
    plan_approval_collect_parser.add_argument(
        "--output", help="new approval-set file (default: PLAN.approval-set.json)"
    )
    plan_approval_collect_parser.add_argument(
        "--json", action="store_true", help="emit machine-readable output"
    )
    plan_approval_collect_parser.set_defaults(handler=_plan_approval_collect_command)

    plan_approval_verify_parser = plan_approval_subparsers.add_parser(
        "verify", help="verify approval against the current plan and its quality policy"
    )
    plan_approval_verify_parser.add_argument("plan")
    plan_approval_verify_parser.add_argument("approval")
    plan_approval_verify_parser.add_argument(
        "--policy", help="exact content policy bound to the approval, when present"
    )
    plan_approval_verify_parser.add_argument(
        "--json", action="store_true", help="emit machine-readable output"
    )
    plan_approval_verify_parser.set_defaults(handler=_plan_approval_verify_command)

    plan_review_parser = plan_subparsers.add_parser(
        "review", help="record or verify source-bound comments and negative review decisions"
    )
    plan_review_subparsers = plan_review_parser.add_subparsers(dest="plan_review_command")
    plan_review_create_parser = plan_review_subparsers.add_parser(
        "create", help="write immutable feedback for the current exact plan revision"
    )
    plan_review_create_parser.add_argument("plan")
    plan_review_create_parser.add_argument(
        "--decision",
        required=True,
        choices=("comment", "request-changes", "reject"),
        help="review outcome; positive authorization stays in plan approval",
    )
    plan_review_create_parser.add_argument(
        "--by", dest="reviewed_by", required=True, help="human-readable reviewer label"
    )
    plan_review_create_parser.add_argument(
        "--at", dest="reviewed_at", help="explicit RFC 3339 review time (default: now)"
    )
    plan_review_create_parser.add_argument(
        "--finding",
        dest="findings",
        action="append",
        required=True,
        help="one bounded feedback message; repeat for additional findings",
    )
    plan_review_create_parser.add_argument(
        "--item", type=int, help="optional plan item number targeted by every finding"
    )
    plan_review_create_parser.add_argument(
        "--platform",
        choices=("x", "linkedin", "bluesky", "mastodon", "discord"),
        help="optional platform target; requires --item",
    )
    plan_review_create_parser.add_argument(
        "--suggestion", help="optional replacement suggestion when exactly one finding is supplied"
    )
    plan_review_create_parser.add_argument(
        "--note", help="optional overall review context (maximum 500 chars)"
    )
    plan_review_create_parser.add_argument(
        "--include-media",
        action="store_true",
        help="inspect and bind exact referenced JPEG/PNG bytes to this review",
    )
    plan_review_create_parser.add_argument(
        "--output", help="new review file (default includes the deterministic review ID)"
    )
    plan_review_create_parser.add_argument(
        "--json", action="store_true", help="emit machine-readable output"
    )
    plan_review_create_parser.set_defaults(handler=_plan_review_create_command)

    plan_review_verify_parser = plan_review_subparsers.add_parser(
        "verify", help="verify a review against current plan source and exact media"
    )
    plan_review_verify_parser.add_argument("plan")
    plan_review_verify_parser.add_argument("review")
    plan_review_verify_parser.add_argument(
        "--fail-on-blocking",
        action="store_true",
        help="return exit code 4 for a current request-changes or reject decision",
    )
    plan_review_verify_parser.add_argument(
        "--json", action="store_true", help="emit machine-readable output"
    )
    plan_review_verify_parser.set_defaults(handler=_plan_review_verify_command)

    plan_handoff_parser = plan_subparsers.add_parser(
        "handoff", help="create or verify an approved offline handoff packet"
    )
    plan_handoff_subparsers = plan_handoff_parser.add_subparsers(dest="plan_handoff_command")
    plan_handoff_create_parser = plan_handoff_subparsers.add_parser(
        "create", help="verify approval and export an integrity-checked handoff"
    )
    plan_handoff_create_parser.add_argument("plan")
    plan_handoff_create_parser.add_argument("approval")
    plan_handoff_create_parser.add_argument(
        "--policy", help="exact content policy bound to the approval, when present"
    )
    plan_handoff_create_parser.add_argument(
        "--at", dest="generated_at", help="explicit RFC 3339 handoff time (default: now)"
    )
    plan_handoff_create_parser.add_argument(
        "--output", default="handoff-outbox", help="output root (default: handoff-outbox)"
    )
    plan_handoff_create_parser.add_argument(
        "--json", action="store_true", help="emit machine-readable output"
    )
    plan_handoff_create_parser.set_defaults(handler=_plan_handoff_create_command)

    plan_handoff_verify_parser = plan_handoff_subparsers.add_parser(
        "verify", help="verify current source, approval, packet shape, and exact artifact bytes"
    )
    plan_handoff_verify_parser.add_argument("plan")
    plan_handoff_verify_parser.add_argument("handoff")
    plan_handoff_verify_parser.add_argument(
        "--policy", help="exact content policy bound to the packet approval, when present"
    )

    plan_handoff_verify_parser.add_argument(
        "--json", action="store_true", help="emit machine-readable output"
    )
    plan_handoff_verify_parser.set_defaults(handler=_plan_handoff_verify_command)

    plan_publication_parser = plan_subparsers.add_parser(
        "publication", help="initialize or verify operator-attested publication outcomes"
    )
    plan_publication_subparsers = plan_publication_parser.add_subparsers(
        dest="plan_publication_command"
    )
    plan_publication_init_parser = plan_publication_subparsers.add_parser(
        "init", help="create a pending ledger for every draft in an exact verified handoff"
    )
    plan_publication_init_parser.add_argument("plan")
    plan_publication_init_parser.add_argument("handoff")
    plan_publication_init_parser.add_argument(
        "--policy", help="exact content policy bound to the packet approval, when present"
    )
    plan_publication_init_parser.add_argument(
        "--at", dest="created_at", help="explicit RFC 3339 ledger creation time (default: now)"
    )
    plan_publication_init_parser.add_argument(
        "--output", help="new ledger file (default: PLAN.publication.json)"
    )
    plan_publication_init_parser.add_argument(
        "--json", action="store_true", help="emit machine-readable output"
    )
    plan_publication_init_parser.set_defaults(handler=_plan_publication_init_command)

    plan_publication_verify_parser = plan_publication_subparsers.add_parser(
        "verify", help="verify current bindings, complete coverage, and recorded outcomes"
    )
    plan_publication_verify_parser.add_argument("plan")
    plan_publication_verify_parser.add_argument("handoff")
    plan_publication_verify_parser.add_argument("publication")
    plan_publication_verify_parser.add_argument(
        "--policy", help="exact content policy bound to the packet approval, when present"
    )
    plan_publication_verify_parser.add_argument(
        "--at", dest="assessed_at", help="explicit RFC 3339 assessment time (default: now)"
    )
    plan_publication_verify_parser.add_argument(
        "--json", action="store_true", help="emit machine-readable output"
    )
    plan_publication_verify_parser.set_defaults(handler=_plan_publication_verify_command)

    policy_parser = subparsers.add_parser(
        "policy", help="validate portable local content-policy profiles"
    )
    policy_subparsers = policy_parser.add_subparsers(dest="policy_command")
    policy_validate_parser = policy_subparsers.add_parser(
        "validate", help="validate and identify a content-policy JSON file"
    )
    policy_validate_parser.add_argument("policy")
    policy_validate_parser.add_argument(
        "--json", action="store_true", help="emit machine-readable output"
    )
    policy_validate_parser.set_defaults(handler=_policy_validate_command)

    schema_parser = subparsers.add_parser(
        "schema", help="print or write a bundled authoring or adapter JSON Schema"
    )
    schema_parser.add_argument(
        "--kind",
        choices=(
            "campaign",
            "content-policy",
            "approval-policy",
            "plan",
            "approval",
            "plan-approval",
            "plan-approval-set",
            "plan-import",
            "plan-review",
            "publication",
            "adapter",
            "handoff",
            "media-package",
            "readiness",
        ),
        default="campaign",
        help="schema to emit",
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
        print(f"error: {_terminal_safe(error)}", file=sys.stderr)
        return 1
    except BrokenPipeError:
        return 0
