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

The referenced image files are intentionally not bundled: validation and preview still pass
because core treats paths as review metadata and never opens them. Replace the paths with real
campaign-relative JPEG/PNG files only when handing the source tree to a separately permissioned
adapter that implements the controls in `docs/MEDIA.md`.

`launch-plan.json` references `campaign.json` and `campaign-follow-up.json` as one release sequence:

```bash
samsarix-campaign plan validate examples/launch-plan.json
samsarix-campaign plan preview examples/launch-plan.json
samsarix-campaign plan check examples/launch-plan.json
samsarix-campaign plan diff examples/launch-plan.json examples/launch-plan.json --json --exit-code
samsarix-campaign plan approval create examples/launch-plan.json --by "Launch reviewer"
samsarix-campaign plan approval verify examples/launch-plan.json examples/launch-plan.json.approval.json
samsarix-campaign plan handoff create examples/launch-plan.json examples/launch-plan.json.approval.json --output handoff-outbox
samsarix-campaign plan status examples/launch-plan.json --approval examples/launch-plan.json.approval.json --require-stage approval --json
samsarix-campaign plan export examples/launch-plan.json --output plan-outbox
```

The plan export contains a manifest, v2 adapter JSON, an RFC 5545 calendar, and one
publisher-neutral CSV for each used platform. It records intended UTC times but never schedules or
publishes a post. The self-diff demonstrates the unchanged exit path; compare against a saved prior
plan to review schedule, order, required-channel, and referenced campaign changes. Plan approval is
local source-bound metadata, not an authenticated identity or digital signature.

The handoff command creates a new `sch_*` directory with the embedded approval and exact plan
artifacts. Pass the printed directory to `plan handoff verify` immediately before downstream use.
The packet hashes provide unsigned integrity checks, not authenticated provenance or permission to
publish; see `docs/HANDOFFS.md`.

`plan status` consolidates quality, intended-time, approval, and optional handoff state. Pass the
created packet with `--handoff`, add `--require-stage handoff` for a CI gate, or add
`--html launch-readiness.html` for a self-contained offline board. The HTML includes the full
drafts; see `docs/READINESS.md` for timing, privacy, and trust-boundary details.
