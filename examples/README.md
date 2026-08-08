# Examples

`campaign.json` is a complete input for the primary CLI journey:

```bash
samsarix-campaign validate examples/campaign.json
samsarix-campaign preview examples/campaign.json
samsarix-campaign check examples/campaign.json
samsarix-campaign export examples/campaign.json --output outbox
```

Expected behavior:

- validation reports one deterministic campaign ID and the five requested platforms;
- preview prints bounded X, LinkedIn, Bluesky, Mastodon, and Discord drafts without writing files;
- check reports truncation and review warnings with a CI-safe exit code;
- export creates `manifest.json` and one Markdown file per requested platform beneath a generated
  campaign folder;
- running the same export again fails safely unless `--overwrite` is explicit.

`library_usage.py` demonstrates the same journey through the documented Python API:

```bash
python examples/library_usage.py
```

This script writes an `outbox/` directory. It does not use the network or publish content.

`campaign-media.json` demonstrates campaign-wide and LinkedIn-only image metadata:

```bash
samsarix-campaign preview examples/campaign-media.json --json
samsarix-campaign diff examples/campaign.json examples/campaign-media.json --json
```

`campaign-tracking.json` demonstrates deterministic campaign defaults plus per-platform source
parameters. The tracked URL is generated locally and remains visible in preview, diff, approval,
adapter, and handoff artifacts:

```bash
samsarix-campaign validate examples/campaign-tracking.json --json
samsarix-campaign preview examples/campaign-tracking.json --json
samsarix-campaign check examples/campaign-tracking.json --json
```

The referenced image files are intentionally not bundled: validation and preview still pass
because core treats paths as review metadata and never opens them. Replace the paths with real
campaign-relative JPEG/PNG files only when handing the source tree to a separately permissioned
adapter that implements the controls in `docs/MEDIA.md`.

`campaign-variants.json` demonstrates complete X, LinkedIn, and Discord content overrides while
Bluesky and Mastodon continue to use the baseline:

```bash
samsarix-campaign validate examples/campaign-variants.json
samsarix-campaign preview examples/campaign-variants.json
samsarix-campaign check examples/campaign-variants.json
```

Omitted fields inside a variant do not inherit. This lets a channel intentionally omit the baseline
title, link, or hashtags. See `docs/VARIANTS.md` for the contract and review implications.

`content-policy.json` demonstrates repository-owned literal phrase guardrails:

```bash
samsarix-campaign policy validate examples/content-policy.json --json
samsarix-campaign check examples/campaign-variants.json \
  --policy examples/content-policy.json --json
```

The example blocks `internal only`, requires `local` in every rendered draft, and emits a
non-blocking Discord review warning. Pass the same `--policy` path to approval, handoff, and status
commands when policy identity must remain bound to evidence. See `docs/POLICIES.md`.

`launch-plan.json` references `campaign.json` and `campaign-follow-up.json` as one release sequence:

```bash
samsarix-campaign plan validate examples/launch-plan.json
samsarix-campaign plan preview examples/launch-plan.json
samsarix-campaign plan check examples/launch-plan.json
samsarix-campaign plan diff examples/launch-plan.json examples/launch-plan.json --json --exit-code
samsarix-campaign plan approval create examples/launch-plan.json --by "Launch reviewer"
samsarix-campaign plan approval verify examples/launch-plan.json examples/launch-plan.json.approval.json
samsarix-campaign plan handoff create examples/launch-plan.json examples/launch-plan.json.approval.json --output handoff-outbox
samsarix-campaign plan status examples/launch-plan.json --approval examples/launch-plan.json.approval.json --at 2026-08-05T12:00:00Z --require-stage approval --json
samsarix-campaign plan export examples/launch-plan.json --output plan-outbox
```

`approval-policy.json` demonstrates a two-role quorum. Create separate plan approvals for the
brand and release-owner labels, then collect and verify them:

```bash
samsarix-campaign plan approval collect examples/launch-plan.json \
  --approval-policy examples/approval-policy.json \
  --approval brand=brand.approval.json \
  --approval release-owner=release-owner.approval.json \
  --output launch-plan.approval-set.json
samsarix-campaign plan approval verify examples/launch-plan.json launch-plan.approval-set.json
```

The example policy requires distinct reviewer labels, but labels and role assignments remain
unsigned local metadata. See `docs/APPROVAL_POLICIES.md` before using the pattern as a release gate.

The plan export contains a manifest, v2 adapter JSON, an RFC 5545 calendar, and one
publisher-neutral CSV for each used platform. It records intended UTC times but never schedules or
publishes a post. The self-diff demonstrates the unchanged exit path; compare against a saved prior
plan to review schedule, order, required-channel, and referenced campaign changes. Plan approval is
local source-bound metadata, not an authenticated identity or digital signature.

The handoff command creates a new `sch_*` directory with the embedded approval and exact plan
artifacts. Pass the printed directory to `plan handoff verify` immediately before downstream use.
The packet hashes provide unsigned integrity checks, not authenticated provenance or permission to
publish; see `docs/HANDOFFS.md`.

After that packet is used, generate a publication ledger from the real packet path rather than
copying a static example with stale identities:

```bash
samsarix-campaign plan publication init \
  examples/launch-plan.json \
  handoff-outbox/LOCAL-FIRST-RELEASE-SEQUENCE-SCH_ID \
  --output launch-plan.publication.json
samsarix-campaign plan publication verify \
  examples/launch-plan.json \
  handoff-outbox/LOCAL-FIRST-RELEASE-SEQUENCE-SCH_ID \
  launch-plan.publication.json
```

Initialization creates one pending record per exact platform draft. Edit outcomes according to
`docs/PUBLICATIONS.md`; the verifier returns `4` until every record is published or intentionally
skipped. A static completed ledger is deliberately not bundled because it would be falsely bound
to an unrelated handoff.

`plan status` consolidates quality, intended-time, approval, optional handoff, and optional
publication state. Pass the
created packet with `--handoff`, add `--require-stage handoff` for a CI gate, or add
`--html launch-readiness.html` for a self-contained offline board. The HTML includes the full
drafts; see `docs/READINESS.md` for timing, privacy, and trust-boundary details.
