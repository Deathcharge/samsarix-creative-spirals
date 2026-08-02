# Copyright (c) 2026 Samsarix LLC
# SPDX-License-Identifier: MPL-2.0

"""Consolidated, offline launch-readiness reporting for campaign plans."""

from __future__ import annotations

import html
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from .handoff import (
    CampaignPlanHandoffPacket,
    verify_campaign_plan_handoff,
)
from .models import ConfigError
from .plan_review import CampaignPlanApproval, verify_campaign_plan_approval
from .plans import CampaignPlanBundle, PlanIssue, check_campaign_plan

ReadinessStage = Literal[
    "quality-blocked",
    "schedule-blocked",
    "ready-for-approval",
    "approval-invalid",
    "approved",
    "handoff-invalid",
    "handoff-ready",
]
EvidenceStatus = Literal["not-provided", "valid", "invalid"]
RequiredStage = Literal["quality", "approval", "handoff"]


def _format_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True, slots=True)
class ReadinessIssue:
    """One stable reason a launch-readiness stage needs attention."""

    code: str
    severity: str
    message: str
    item: int | None = None
    path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "item": self.item,
            "path": self.path,
            "message": self.message,
        }


@dataclass(frozen=True, slots=True)
class CampaignPlanReadinessItem:
    """Readiness detail for one generated campaign in plan order."""

    sequence: int
    campaign_id: str
    name: str
    source: str
    intended_at: datetime | None
    platforms: tuple[str, ...]
    quality_passed: bool
    quality_issues: tuple[PlanIssue, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "sequence": self.sequence,
            "campaignId": self.campaign_id,
            "name": self.name,
            "source": self.source,
            "intendedAt": _format_utc(self.intended_at) if self.intended_at else None,
            "platforms": list(self.platforms),
            "qualityPassed": self.quality_passed,
            "qualityIssues": [issue.to_dict() for issue in self.quality_issues],
        }


@dataclass(frozen=True, slots=True)
class CampaignPlanReadiness:
    """A point-in-time readiness view with optional approval and handoff evidence."""

    plan_id: str
    source_hash: str
    name: str
    assessed_at: datetime
    stage: ReadinessStage
    quality_policy: str
    schedule_policy: str
    quality_passed: bool
    schedule_complete: bool
    schedule_ready: bool
    approval_status: EvidenceStatus
    approval: CampaignPlanApproval | None
    handoff_status: EvidenceStatus
    handoff_id: str | None
    issues: tuple[ReadinessIssue, ...]
    items: tuple[CampaignPlanReadinessItem, ...]

    @property
    def ready(self) -> bool:
        """Return whether the plan has a current, verified handoff packet."""
        return self.stage == "handoff-ready"

    def meets(self, required_stage: RequiredStage) -> bool:
        """Return whether the report satisfies an explicit automation gate."""
        if required_stage == "quality":
            return self.quality_passed and self.schedule_ready
        if required_stage == "approval":
            return self.stage in {"approved", "handoff-ready"}
        return self.stage == "handoff-ready"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": 1,
            "artifactType": "plan-readiness",
            "assessedAt": _format_utc(self.assessed_at),
            "planId": self.plan_id,
            "sourceHash": self.source_hash,
            "name": self.name,
            "stage": self.stage,
            "ready": self.ready,
            "qualityPolicy": self.quality_policy,
            "schedulePolicy": self.schedule_policy,
            "qualityPassed": self.quality_passed,
            "scheduleComplete": self.schedule_complete,
            "scheduleReady": self.schedule_ready,
            "approvalStatus": self.approval_status,
            "approval": self.approval.to_dict() if self.approval else None,
            "handoffStatus": self.handoff_status,
            "handoffId": self.handoff_id,
            "counts": {
                "items": len(self.items),
                "scheduled": sum(item.intended_at is not None for item in self.items),
                "platformDrafts": sum(len(item.platforms) for item in self.items),
                "issues": len(self.issues),
            },
            "issues": [issue.to_dict() for issue in self.issues],
            "items": [item.to_dict() for item in self.items],
        }


def _quality_readiness_issues(quality_issues: tuple[PlanIssue, ...]) -> list[ReadinessIssue]:
    return [
        ReadinessIssue(
            code=f"quality-{issue.code}",
            severity=issue.severity,
            item=issue.item,
            message=issue.message,
        )
        for issue in quality_issues
    ]


def build_campaign_plan_readiness(
    bundle: CampaignPlanBundle,
    *,
    approval: CampaignPlanApproval | None = None,
    handoff: CampaignPlanHandoffPacket | None = None,
    assessed_at: datetime | None = None,
    warnings_as_errors: bool = False,
    require_scheduled: bool = False,
) -> CampaignPlanReadiness:
    """Assess current quality, schedule, approval, and handoff evidence offline."""
    timestamp = assessed_at or datetime.now(timezone.utc)
    if timestamp.utcoffset() is None:
        raise ConfigError("assessed_at must include timezone information")
    timestamp = timestamp.astimezone(timezone.utc)

    quality = check_campaign_plan(bundle, warnings_as_errors=warnings_as_errors)
    issues = _quality_readiness_issues(quality.issues)
    schedule_complete = all(item.intended_at is not None for item in bundle.items)
    schedule_blocked = False
    for item in bundle.items:
        if item.intended_at is None:
            issues.append(
                ReadinessIssue(
                    code="schedule-missing",
                    severity="error" if require_scheduled else "warning",
                    item=item.sequence,
                    message=(
                        "Item has no intended time."
                        + (" A complete schedule is required." if require_scheduled else "")
                    ),
                )
            )
            schedule_blocked = schedule_blocked or require_scheduled
        elif item.intended_at <= timestamp:
            schedule_blocked = True
            issues.append(
                ReadinessIssue(
                    code="schedule-past",
                    severity="error",
                    item=item.sequence,
                    message="Intended time has passed or is due now; reschedule before launch.",
                )
            )
    schedule_ready = not schedule_blocked

    selected_approval = approval
    approval_status: EvidenceStatus = "not-provided"
    handoff_status: EvidenceStatus = "not-provided"
    handoff_id: str | None = None
    evidence_mismatch = False
    if handoff is not None:
        handoff_id = handoff.handoff.handoff_id
        if approval is None:
            selected_approval = handoff.approval
        elif approval.to_dict() != handoff.approval.to_dict():
            evidence_mismatch = True
            issues.append(
                ReadinessIssue(
                    code="approval-handoff-mismatch",
                    severity="error",
                    message=(
                        "Provided approval does not match the approval embedded in the handoff."
                    ),
                )
            )

    approval_valid = False
    if selected_approval is not None:
        approval_check = verify_campaign_plan_approval(bundle, selected_approval)
        approval_valid = approval_check.valid and not evidence_mismatch
        approval_status = "valid" if approval_valid else "invalid"
        for approval_issue in approval_check.issues:
            issues.append(
                ReadinessIssue(
                    code=f"approval-{approval_issue.code}",
                    severity="error",
                    message=approval_issue.message,
                )
            )

    handoff_valid = False
    if handoff is not None:
        handoff_check = verify_campaign_plan_handoff(bundle, handoff)
        handoff_valid = handoff_check.valid and approval_valid and not evidence_mismatch
        handoff_status = "valid" if handoff_valid else "invalid"
        for handoff_issue in handoff_check.issues:
            issues.append(
                ReadinessIssue(
                    code=f"handoff-{handoff_issue.code}",
                    severity="error",
                    path=handoff_issue.path,
                    message=handoff_issue.message,
                )
            )

    if not quality.publishable:
        stage: ReadinessStage = "quality-blocked"
    elif not schedule_ready:
        stage = "schedule-blocked"
    elif handoff is not None:
        stage = "handoff-ready" if handoff_valid else "handoff-invalid"
    elif selected_approval is not None:
        stage = "approved" if approval_valid else "approval-invalid"
    else:
        stage = "ready-for-approval"

    item_reports = tuple(
        CampaignPlanReadinessItem(
            sequence=item.sequence,
            campaign_id=item.bundle.campaign_id,
            name=item.bundle.name,
            source=item.source,
            intended_at=item.intended_at,
            platforms=tuple(draft.platform for draft in item.bundle.drafts),
            quality_passed=not any(
                issue.severity == "error" and issue.item == item.sequence
                for issue in quality.issues
            ),
            quality_issues=tuple(issue for issue in quality.issues if issue.item == item.sequence),
        )
        for item in bundle.items
    )
    return CampaignPlanReadiness(
        plan_id=bundle.plan_id,
        source_hash=bundle.source_hash,
        name=bundle.name,
        assessed_at=timestamp,
        stage=stage,
        quality_policy="warnings-as-errors" if warnings_as_errors else "errors-only",
        schedule_policy="required" if require_scheduled else "optional",
        quality_passed=quality.publishable,
        schedule_complete=schedule_complete,
        schedule_ready=schedule_ready,
        approval_status=approval_status,
        approval=selected_approval,
        handoff_status=handoff_status,
        handoff_id=handoff_id,
        issues=tuple(issues),
        items=item_reports,
    )


def _escape(value: object) -> str:
    return html.escape(str(value), quote=True)


def render_campaign_plan_readiness_html(
    report: CampaignPlanReadiness,
    bundle: CampaignPlanBundle,
) -> str:
    """Render a self-contained, script-free status board with copy-ready drafts."""
    issue_rows = (
        "".join(
            "<li><strong>"
            + _escape(issue.severity.upper())
            + " · "
            + _escape(issue.code)
            + "</strong>"
            + (f" · item {_escape(issue.item)}" if issue.item is not None else "")
            + (f" · <code>{_escape(issue.path)}</code>" if issue.path else "")
            + f"<br>{_escape(issue.message)}</li>"
            for issue in report.issues
        )
        or "<li>None.</li>"
    )
    item_rows = "".join(
        "<tr>"
        f"<td>{item.sequence}</td>"
        f"<td>{_escape(item.name)}<br><code>{_escape(item.campaign_id)}</code></td>"
        f"<td>{_escape(_format_utc(item.intended_at) if item.intended_at else 'Unscheduled')}</td>"
        f"<td>{_escape(', '.join(item.platforms))}</td>"
        f"<td>{'Passed' if item.quality_passed else 'Blocked'}</td>"
        "</tr>"
        for item in report.items
    )
    draft_sections = "".join(
        "<section class=campaign>"
        f"<h3>Item {planned.sequence}: {_escape(planned.bundle.name)}</h3>"
        f"<p><code>{_escape(planned.source)}</code></p>"
        + "".join(
            "<article class=draft>"
            f"<h4>{_escape(draft.platform)} · {draft.character_count}/{draft.character_limit}</h4>"
            f"<pre>{_escape(draft.content)}</pre>"
            + (
                "<p><strong>Media:</strong> "
                + _escape("; ".join(f"{media.path} — {media.alt_text}" for media in draft.media))
                + "</p>"
                if draft.media
                else ""
            )
            + "</article>"
            for draft in planned.bundle.drafts
        )
        + "</section>"
        for planned in bundle.items
    )
    stage_label = report.stage.replace("-", " ").title()
    approval_detail = (
        _escape(
            f"{report.approval.approved_by} at "
            f"{report.approval.to_dict()['approvedAt']} ({report.approval.quality_policy})"
        )
        if report.approval
        else "Not provided"
    )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="referrer" content="no-referrer">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'">
<title>{_escape(report.name)} · launch readiness</title>
<style>
:root {{ color-scheme: light dark; font-family: ui-sans-serif, system-ui, sans-serif; }}
body {{ max-width: 1100px; margin: 0 auto; padding: 2rem; line-height: 1.5; }}
.summary {{ border: 2px solid currentColor; border-radius: .75rem; padding: 1rem 1.25rem; }}
.facts {{ display: grid; grid-template-columns: repeat(auto-fit,minmax(12rem,1fr)); gap: .75rem; }}
.fact,.draft {{ border: 1px solid #8888; border-radius: .5rem; padding: .75rem; }}
table {{ border-collapse: collapse; width: 100%; }}
th,td {{ border: 1px solid #8888; padding: .6rem; text-align: left; }}
pre {{ white-space: pre-wrap; overflow-wrap: anywhere; font: inherit; }}
code {{ overflow-wrap: anywhere; }} li {{ margin: .5rem 0; }}
@media print {{ body {{ max-width: none; }} .draft {{ break-inside: avoid; }} }}
</style>
</head>
<body>
<header>
<p>Samsarix Creative Spirals · offline status board</p>
<h1>{_escape(report.name)}</h1>
</header>
<section class="summary" aria-labelledby="summary-title">
<h2 id="summary-title">{_escape(stage_label)}</h2>
<p><strong>Launch ready: {'Yes' if report.ready else 'No'}</strong></p>
<div class="facts">
<p class="fact"><strong>Plan</strong><br><code>{_escape(report.plan_id)}</code></p>
<p class="fact"><strong>Assessed</strong><br>{_escape(_format_utc(report.assessed_at))}</p>
<p class="fact"><strong>Quality</strong><br>
{'Passed' if report.quality_passed else 'Blocked'} ({_escape(report.quality_policy)})</p>
<p class="fact"><strong>Schedule</strong><br>
{'Ready' if report.schedule_ready else 'Blocked'};
{'complete' if report.schedule_complete else 'incomplete'}</p>
<p class="fact"><strong>Approval</strong><br>{_escape(report.approval_status)}<br>
{approval_detail}</p>
<p class="fact"><strong>Handoff</strong><br>{_escape(report.handoff_status)}<br>
{_escape(report.handoff_id or 'Not provided')}</p>
</div></section>
<section><h2>Findings</h2><ul>{issue_rows}</ul></section>
<section><h2>Schedule</h2><table><thead><tr>
<th>Item</th><th>Campaign</th><th>Intended time</th><th>Platforms</th><th>Quality</th>
</tr></thead><tbody>{item_rows}</tbody></table></section>
<section><h2>Copy-ready drafts</h2>
<p>This report contains campaign content and may be sensitive. It does not publish,
notify, authenticate a reviewer, or prove publication.</p>{draft_sections}</section>
<footer><p>Generated locally by Samsarix Creative Spirals.
No network resources or scripts are used.</p></footer>
</body>
</html>
"""


def export_campaign_plan_readiness_html(
    report: CampaignPlanReadiness,
    bundle: CampaignPlanBundle,
    path: str | Path,
) -> Path:
    """Write a new offline HTML report without replacing an existing file."""
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        with destination.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(render_campaign_plan_readiness_html(report, bundle))
    except FileExistsError:
        raise ConfigError(
            f"refusing to overwrite existing readiness report: {destination}"
        ) from None
    return destination
