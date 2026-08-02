# Quick start

Samsarix Creative Spirals needs Python 3.10+ and no API credentials.

## 1. Install from this checkout

```bash
python -m venv .venv
```

```bash
# macOS/Linux
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1
```

```bash
python -m pip install -e .
samsarix-campaign --version
```

## 2. Create, preview, and check a campaign

```bash
samsarix-campaign init campaign.json
samsarix-campaign preview campaign.json
samsarix-campaign check campaign.json
```

Edit `campaign.json`, then run `preview` and `check` again. Both are side-effect free: they read the
file and write only to stdout/stderr. `check` exits with `3` when any draft was truncated.

To carry reviewed image choices alongside the text, add portable metadata without giving the core
permission to open or upload the file:

```json
"media": [
  {
    "path": "media/launch.png",
    "altText": "Campaign review dashboard showing five platform drafts"
  }
]
```

The path is relative to the campaign JSON. JPEG and PNG are supported, alt text is required, and a
campaign may target no more than four images to one platform. Add a `platforms` array inside a
reference when a visual applies only to selected campaign platforms. Full rules and adapter safety
requirements are in [MEDIA.md](MEDIA.md).

## 3. Validate for automation

```bash
samsarix-campaign validate campaign.json --json
```

Example success:

```json
{
  "valid": true,
  "campaignId": "scs_8b7f2a12c941",
  "platforms": ["x", "linkedin", "bluesky", "mastodon", "discord"]
}
```

Validation failures return exit code `1` and write the reason to stderr.

To make every review warning block CI as well as truncation:

```bash
samsarix-campaign check campaign.json --warnings-as-errors --json
```

For editor or CI support, print the bundled schema or write it to a new file:

```bash
samsarix-campaign schema
samsarix-campaign schema --output campaign.schema.json
```

### Optional: apply a portable content policy

Validate and run the included literal phrase guardrails against final platform drafts:

```bash
samsarix-campaign policy validate examples/content-policy.json --json
samsarix-campaign check examples/campaign-variants.json \
  --policy examples/content-policy.json --json
```

Policy files can block or require phrases per platform. They stay local and deterministic. See
[POLICIES.md](POLICIES.md) for exact matching, limits, approval binding, and security boundaries.

## 4. Compare and record local approval

Review a proposed campaign against the previously accepted file:

```bash
samsarix-campaign diff campaign-before.json campaign.json
samsarix-campaign diff campaign-before.json campaign.json --json --exit-code
```

The second form returns exit `4` when semantic fields or generated drafts changed. After the
quality gate and human review pass, create and verify source-bound metadata:

```bash
samsarix-campaign approval create campaign.json --by "Release reviewer"
samsarix-campaign approval verify campaign.json campaign.json.approval.json
```

If approval used a content policy, supply the exact same file to both commands:

```bash
samsarix-campaign approval create campaign.json --by "Release reviewer" \
  --policy content-policy.json
samsarix-campaign approval verify campaign.json campaign.json.approval.json \
  --policy content-policy.json
```

Any normalized source change makes verification return `4`. The reviewer label is not
authenticated, so keep the record in a repository with appropriate write/review controls when
identity matters.

## 5. Export the approved drafts

```bash
samsarix-campaign export campaign.json --output outbox
```

The resulting folder contains one Markdown file per requested platform and `manifest.json` with the source
hash, limits, media metadata, truncation state, warnings, and UTC export time. Referenced image
bytes are not copied into the bundle. The tool does not publish anything;
copy the reviewed content into the destination platform or pass the files to a separate approved
integration.

If the exact same campaign was already exported, the command refuses to replace it. An intentional
replacement is explicit:

```bash
samsarix-campaign export campaign.json --output outbox --overwrite
```

## 6. Review and export a complete campaign plan

The included plan references two standalone campaign files and declares the channels every item
must cover:

```bash
samsarix-campaign plan validate examples/launch-plan.json --json
samsarix-campaign plan preview examples/launch-plan.json
samsarix-campaign plan check examples/launch-plan.json
samsarix-campaign plan diff launch-plan-before.json examples/launch-plan.json --json --exit-code
samsarix-campaign plan approval create examples/launch-plan.json --by "Launch reviewer"
samsarix-campaign plan approval verify examples/launch-plan.json examples/launch-plan.json.approval.json
samsarix-campaign plan export examples/launch-plan.json --output plan-outbox
```

Plan paths use forward slashes, remain relative to the plan file, and cannot escape its directory.
`intendedAt` is optional; when present it must be RFC 3339 with an explicit offset or `Z`.
The plan diff covers metadata, order, intended times, source references, and nested campaign/draft
changes. Plan approval binds all of that state plus every referenced campaign to the recorded
quality policy. Any later schedule, membership, required-platform, copy, or media change makes
verification return `4`.

The exported directory contains:

```text
plan-outbox/
└── local-first-release-sequence-scp_<content-id>/
    ├── manifest.json
    ├── adapter.json
    ├── calendar.ics
    └── csv/
        ├── x.csv
        ├── linkedin.csv
        ├── bluesky.csv
        ├── mastodon.csv
        └── discord.csv
```

The calendar is an interchange artifact, not a scheduler. CSV files use stable Samsarix columns
and explicit UTC timestamps for review and spreadsheet workflows; publisher-specific imports may
require a separate transformation.
Use `adapter.json` for programmatic importers that need exact draft text; its bundled contract is
available with `samsarix-campaign schema --kind adapter`. The core package does not authenticate or
publish on an adapter's behalf.

## 7. Create and verify the approved handoff

Use the plan approval to create an exclusive packet for a manual or separately permissioned
publisher workflow:

```bash
samsarix-campaign plan handoff create \
  examples/launch-plan.json \
  examples/launch-plan.json.approval.json \
  --output handoff-outbox
```

The command prints the generated `sch_*` packet path. Verify that exact directory immediately
before downstream use:

```bash
samsarix-campaign plan handoff verify \
  examples/launch-plan.json \
  handoff-outbox/local-first-release-sequence-sch_<handoff-id>
```

Verification returns `4` when current source or approval is stale, a rendered file changed, a file
is missing or unexpected, or the producer version differs. A packet contains `handoff.json`, the
embedded `approval.json`, and the same manifest, adapter, calendar, and platform CSV files as plan
export. It is never overwritten in place.

These checksums are unsigned integrity metadata, not authenticated reviewer/producer provenance.
Read [HANDOFFS.md](HANDOFFS.md) before connecting a downstream adapter.

## 8. Assess launch readiness

Use the packet's embedded approval to check the complete local launch state and create a reviewable
offline board:

```bash
samsarix-campaign plan status \
  examples/launch-plan.json \
  --handoff handoff-outbox/local-first-release-sequence-sch_<handoff-id> \
  --at 2026-08-05T12:00:00Z \
  --require-scheduled \
  --require-stage handoff \
  --html launch-readiness.html \
  --json
```

The report compares scheduled times with the current clock. Use `--at RFC3339` for a reproducible
CI snapshot. The HTML contains the complete drafts and should be protected like the campaign
source. It does not schedule or publish anything; see [READINESS.md](READINESS.md).

## Troubleshooting

- `unknown field(s)`: fix the spelling or remove unsupported keys.
- `body must not be empty`: provide the approved source draft.
- `link must be an absolute http or https URL`: include the full scheme and hostname.
- `bundle already exists`: review the existing bundle, change the campaign, choose another output
  root, or explicitly pass `--overwrite`.
- `Quality check failed`: inspect the listed platform findings; shorten the source, reduce suffix
  metadata, or use an accurate `platformLimits.mastodon` value for the intended instance.
- `resolves outside the plan directory`: move the campaign JSON beneath the plan directory and use
  a portable relative path without `..` or a symbolic-link escape.
- `Approval invalid`: diff the approved and current source, repeat human review, then create a new
  approval file; existing records are intentionally not overwritten.
- `Plan approval invalid`: run `plan diff` against the reviewed plan, repeat review of the complete
  sequence, and create a new plan approval file.
- `Approved handoff invalid`: stop downstream use, inspect the stable issue codes, then re-check
  source and approval. Create a new packet instead of editing or replacing the existing one.
- `Launch readiness: ... blocked/invalid`: inspect the reported quality, schedule, approval, and
  handoff issues. Reschedule due items or create new approval/handoff evidence instead of editing
  immutable evidence in place.
- `samsarix-campaign: command not found`: activate the environment where the package was installed,
  or run `python -m samsarix_creative_spirals` with the same arguments.
