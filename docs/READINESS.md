# Launch readiness reports

`samsarix-campaign plan status` answers one bounded operational question: **what is the current
launch stage, and what blocks the next gate?** It combines existing plan quality, intended times,
source-bound approval, and exact handoff verification into one point-in-time local report.

It does not create a hosted calendar, sync team state, send notifications, connect accounts,
schedule posts, publish content, or prove that publication occurred.

## Why this workflow exists

Current publishing products make calendar and approval state central to campaign operations:

- Sprout Social describes its Publishing Calendar as a single place to see and manage planned
  messages, with list/week/month views, filters, notes, and PDF sharing. Its approval workflow
  exposes a **Needs Approval** state and does not publish a message that misses approval before its
  scheduled time: <https://support.sproutsocial.com/hc/en-us/articles/360000121343-How-do-I-use-the-Publishing-Calendar>
  and <https://support.sproutsocial.com/hc/en-us/articles/205974715-Message-Approval-Workflows>.
- Buffer exposes an **Awaiting Approval** list and lets an approver add a post to the queue or
  schedule it: <https://support.buffer.com/article/665-managing-and-approving-draft-posts>.
- Buffer's July 13, 2026 product update explicitly identifies difficulty finding drafts from the
  calendar as friction and adds calendar access to drafts and pending approvals:
  <https://buffer.com/changelog/access-your-drafts-from-the-calendar>.

Those products keep shared server state and can operate connected accounts. Samsarix instead
provides a credential-free, Git-friendly snapshot that can be generated in CI, opened offline, or
attached to an existing review process.

## Core commands

Create an informational JSON snapshot at an explicit reproducible time:

```bash
samsarix-campaign plan status examples/launch-plan.json \
  --at 2026-08-05T12:00:00Z \
  --json
```

Require every item to have a future intended time and require current plan approval:

```bash
samsarix-campaign plan status examples/launch-plan.json \
  --approval examples/launch-plan.json.approval.json \
  --require-scheduled \
  --require-stage approval
```

Verify the approval embedded in an exact handoff and write a self-contained status board:

```bash
samsarix-campaign plan status examples/launch-plan.json \
  --handoff handoff-outbox/local-first-release-sequence-sch_0123456789ab \
  --require-stage handoff \
  --html launch-readiness.html
```

If both `--approval` and `--handoff` are supplied, the explicit approval must exactly equal the
record embedded in the packet. The handoff can otherwise supply its embedded approval by itself.
Add `--policy POLICY` to assess literal phrase rules and to verify any policy binding in approval
or handoff evidence. The JSON and HTML reports show the applied policy identity. See
[`POLICIES.md`](POLICIES.md).

## Stages

| Stage | Meaning |
|---|---|
| `quality-blocked` | The selected errors-only or warnings-as-errors plan policy fails. |
| `schedule-blocked` | An intended time is due/past, or a required schedule is incomplete. |
| `ready-for-approval` | Quality and schedule policy pass; no approval was supplied. |
| `approval-invalid` | Supplied approval is stale or fails its recorded quality policy. |
| `approved` | Current approval verifies; no handoff was supplied. |
| `handoff-invalid` | Packet, embedded approval, explicit approval match, or exact artifacts fail verification. |
| `handoff-ready` | Current quality, time policy, approval, and exact handoff all verify. |

Only `handoff-ready` sets JSON `ready` to `true`. An unscheduled item sets `scheduleComplete` to
`false`; it is a warning under the default optional policy and a blocker with
`--require-scheduled`. An intended time equal to or earlier than `assessedAt` is always a blocker
because the local intent needs rescheduling. Use `--at` in tests and CI so results are reproducible.

## Automation contract

Without `--require-stage`, status is informational and returns `0` after valid input and successful
I/O. Explicit gates return:

- `0` when the requested stage is met;
- `3` when `--require-stage quality` is not met;
- `4` when an approval or handoff requirement is not met;
- `1` for malformed input or I/O failure; and
- `2` for invalid CLI usage.

`--json` emits the exact plan-readiness v1 document, not a CLI wrapper. Retrieve its bundled Draft
2020-12 schema with:

```bash
samsarix-campaign schema --kind readiness
```

The report records the assessment time and policies, stable stage and issue codes, evidence
status, counts, and one item record per campaign. Version 0.11 adds only optional content-policy
identity and rule context to this v1 JSON shape; existing reports remain valid.

## Offline HTML and privacy

`--html` writes a new file exclusively and refuses to replace an existing report. The report is
self-contained, script-free, and has no external resources. It sets a restrictive Content
Security Policy, a no-referrer policy, escapes all campaign-controlled text, and communicates
status in text rather than color alone. It includes the generated platform drafts so reviewers can
use it without the CLI.

That convenience also means the HTML contains potentially confidential draft content, links,
media paths, alt text, plan identity, reviewer metadata status, and intended launch times. Protect,
retain, and delete it like the source campaign. Opening it does not trigger network access from the
report itself, but downstream browsers, extensions, synchronization tools, and the surrounding
filesystem remain outside this package's control.

## Trust boundary

Readiness is a local observation, not durable shared state. Approval labels and hashes are
unsigned. A person who can rewrite the source and all evidence can forge a consistent replacement.
Repository permissions and required pull-request reviews can supply an authenticated collaboration
boundary; cryptographic signatures would require a separate design.

Handoff verification detects stale source, malformed packet shape, missing or extra files,
symbolic links, changed sizes/checksums, and bytes that do not match freshly regenerated output.
Run status immediately before the same packet directory is consumed. The report cannot establish
reviewer identity, publisher authorization, provider acceptance, delivery, or final publication.
