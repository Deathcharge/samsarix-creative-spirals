# Samsarix Creative Spirals

Samsarix Creative Spirals is a local-first CLI and typed Python library that turns approved source
drafts into copy-ready files for X, LinkedIn, Bluesky, Mastodon, and Discord. It validates campaign
input, applies platform-aware limits, checks complete launch sequences, and exports review bundles,
publisher-neutral CSV, and portable calendars. Portable image references, semantic diffs, and
source-bound campaign and plan approval records make exact changes visible before handoff.
Approved handoff packets then bind current source, approval metadata, and exact rendered files for
offline verification immediately before downstream use. A consolidated readiness command and
offline HTML board show the current quality, schedule, approval, and handoff stage in one place.

It is for solo creators, developer advocates, and small content teams that want a scriptable
review/export step without connecting social accounts or sending draft content to a service.

> Maturity: **0.9 alpha.** Federated-platform drafts, campaign-plan quality gates, whole-plan
> semantic review and local approvals, portable image metadata, approved handoff verification, and
> launch-readiness reporting are implemented and tested. Automatic
> publishing,
> scheduling, analytics, and AI generation are deliberately not included.

## Fastest successful path

Prerequisite: Python 3.10 or newer.

```bash
git clone https://github.com/Deathcharge/samsarix-creative-spirals.git
cd samsarix-creative-spirals
python -m venv .venv
```

Activate the environment:

```bash
# macOS/Linux
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1
```

Install and preview the included campaign:

```bash
python -m pip install -e .
samsarix-campaign preview examples/campaign.json
```

No API keys, accounts, database, network connection, or other Samsarix repository is required.

## Core journey

Create a starter file, preview it, run the quality gate, then export after reviewing the output:

```bash
samsarix-campaign init campaign.json
samsarix-campaign validate campaign.json
samsarix-campaign preview campaign.json
samsarix-campaign check campaign.json
samsarix-campaign export campaign.json --output outbox
```

The export command creates a deterministic directory such as:

```text
outbox/
└── product-launch-scs_8b7f2a12c941/
    ├── manifest.json
    ├── x.md
    ├── linkedin.md
    ├── bluesky.md
    ├── mastodon.md
    └── discord.md
```

Re-exporting an unchanged campaign is refused by default. Use `--overwrite` only when replacing
that same deterministic bundle is intentional.

## Campaign format

Campaigns are UTF-8 JSON files. Unknown keys are errors so misspellings do not silently change
behavior.

```json
{
  "schemaVersion": 1,
  "name": "Product launch",
  "title": "We shipped something useful",
  "body": "One approved source draft becomes five reviewable outputs.",
  "link": "https://example.com/launch",
  "hashtags": ["buildinpublic", "product"],
  "platforms": ["x", "linkedin", "bluesky", "mastodon", "discord"],
  "platformLimits": {"mastodon": 1000},
  "media": [
    {
      "path": "media/launch.png",
      "altText": "Campaign review dashboard showing five platform drafts"
    }
  ]
}
```

| Field | Required | Rules |
| --- | --- | --- |
| `schemaVersion` | yes | Must be `1`. |
| `name` | yes | Single line, 1–120 characters; used to derive a safe folder name. |
| `body` | yes | 1–100,000 characters. |
| `platforms` | yes | Unique values from `x`, `linkedin`, `bluesky`, `mastodon`, `discord`. |
| `title` | no | Single line, at most 200 characters; omitted from X and Bluesky output. |
| `link` | no | Absolute HTTP(S) URL, at most 500 characters, no embedded credentials. |
| `hashtags` | no | Up to 10 unique values containing letters, numbers, or underscores. |
| `platformLimits` | no | Stricter per-platform limits, or a Mastodon instance limit up to 100,000. Keys must also appear in `platforms`. |
| `media` | no | Up to 20 portable JPEG/PNG references, with required alt text and at most four images targeted to each platform. |

Media paths are metadata relative to the campaign file. Core validates that metadata but never
resolves, reads, inspects, copies, or uploads the referenced files. References participate in
campaign hashes, diffs, approvals, manifests, and adapter v2 output. See
[Portable media references](docs/MEDIA.md) for targeting, path rules, platform rationale, and the
filesystem/provider checks required of an external adapter.

Print the bundled JSON Schema for editor or CI integration, or write it to a new file:

```bash
samsarix-campaign schema
samsarix-campaign schema --kind plan
samsarix-campaign schema --kind approval
samsarix-campaign schema --kind plan-approval
samsarix-campaign schema --kind adapter
samsarix-campaign schema --kind handoff
samsarix-campaign schema --output campaign.schema.json
```

Formatting defaults are 280 weighted characters for X, 3,000 UTF-16 code units for LinkedIn, 300
graphemes plus 3,000 UTF-8 bytes for Bluesky, 500 characters for Mastodon, and 2,000 UTF-16 code
units for Discord. X and Mastodon apply their documented 23-character URL rule. Mastodon instances
may advertise another maximum; record it explicitly in `platformLimits`. Content is normalized to
NFC and truncated on conservative text clusters; links and suffix metadata are preserved where
possible. Every modification is recorded in preview output and `manifest.json`.

## Quality gate

`check` makes content QA useful in scripts and pull requests. It returns `3` if any platform draft
was truncated. Review warnings are visible but non-blocking by default; promote them to failures
when a workflow requires a clean report:

```bash
samsarix-campaign check campaign.json --json
samsarix-campaign check campaign.json --warnings-as-errors
```

This command performs no writes or network calls. A successful JSON report has
`"publishable": true`; findings have stable `code`, `severity`, `platform`, and `message` fields.

## Semantic review and local approval

Compare normalized source fields and every generated platform draft before accepting a change:

```bash
samsarix-campaign diff campaign-before.json campaign.json
samsarix-campaign diff campaign-before.json campaign.json --json --exit-code
```

Formatting-only differences that normalize to the same campaign produce no change. `--exit-code`
returns `4` when semantic changes exist; without it, diff remains an informational command.

After `check` passes, record the exact normalized source hash and quality policy reviewed:

```bash
samsarix-campaign approval create campaign.json --by "Release reviewer"
samsarix-campaign approval verify campaign.json campaign.json.approval.json
```

Changing the campaign invalidates the approval. Existing approval files are never overwritten.
`approvedBy` is a human-readable label, not an authenticated identity: approval records are useful
Git review metadata, not digital signatures or authorization tokens.

## Campaign plans

A plan keeps a launch sequence reviewable in Git while reusing standalone campaign files. Campaign
paths are portable, relative to the plan, and confined beneath its directory. Intended times must
include `Z` or an explicit offset and are normalized to UTC.

```json
{
  "schemaVersion": 1,
  "name": "Release sequence",
  "requiredPlatforms": ["x", "linkedin", "bluesky", "mastodon", "discord"],
  "items": [
    {"campaign": "campaign.json", "intendedAt": "2026-08-10T13:00:00Z"},
    {"campaign": "campaign-follow-up.json"}
  ]
}
```

Validate every reference, preview the sequence, run the aggregate gate, then export:

```bash
samsarix-campaign plan validate examples/launch-plan.json
samsarix-campaign plan preview examples/launch-plan.json
samsarix-campaign plan check examples/launch-plan.json
samsarix-campaign plan diff launch-plan-before.json examples/launch-plan.json
samsarix-campaign plan approval create examples/launch-plan.json --by "Launch reviewer"
samsarix-campaign plan approval verify examples/launch-plan.json examples/launch-plan.json.approval.json
samsarix-campaign plan export examples/launch-plan.json --output plan-outbox
```

The plan gate reports missing required channels and campaign-level truncation as errors. Duplicate
times, out-of-order scheduled items, and ordinary review warnings are visible but non-blocking
unless `--warnings-as-errors` is set. Unscheduled items are allowed.

Plan diff compares normalized plan metadata and each one-based sequence position. It reports
schedule, source-reference, membership/order, and nested campaign/draft changes. Plan approval
binds the complete normalized plan—including order, intended times, required platforms, media, and
every referenced campaign—to one quality policy. Any of those changes makes verification return
`4`. See [Plan review and approval](docs/PLAN_REVIEW.md) for the machine-readable contract, CI
pattern, and trust boundary.

Plan export writes `manifest.json`, `calendar.ics`, and one UTF-8 CSV per used platform. Scheduled
items become transparent calendar events; unscheduled items become tasks. CSV timestamps are
explicit UTC values and the stable columns are publisher-neutral—they are intended for review and
spreadsheet workflows, not presented as a drop-in template for every publisher.

It also writes deterministic `adapter.json`, which preserves exact draft text and media references
in a versioned JSON contract for separately permissioned importers. See [ADAPTERS.md](docs/ADAPTERS.md) for schema,
identity, idempotency, authorization, and compatibility rules.

## Approved downstream handoff

After the complete plan is approved, create one non-overwriting packet that contains the embedded
approval and exact plan-export artifacts:

```bash
samsarix-campaign plan handoff create \
  examples/launch-plan.json \
  examples/launch-plan.json.approval.json \
  --output handoff-outbox
samsarix-campaign plan handoff verify \
  examples/launch-plan.json \
  handoff-outbox/RELEASE-SEQUENCE-SCH_ID
```

Verification rechecks current source and the recorded quality policy, regenerates every expected
artifact, checks byte lengths and SHA-256 values, and rejects missing, substituted, symbolic-link,
or extra files. The packet is the safe input boundary for a manual workflow or separately
permissioned adapter; it does not connect an account, queue, schedule, or publish anything.

The hashes are unsigned integrity checks. They do not authenticate the reviewer or producer and
are not cryptographic attestations. See [Approved handoff packets](docs/HANDOFFS.md) for the packet
contract, CLI/adapter workflow, threat model, and retention guidance.

## Launch readiness

Get a single point-in-time status after quality checks, approval, or handoff creation:

```bash
samsarix-campaign plan status examples/launch-plan.json --json
samsarix-campaign plan status examples/launch-plan.json \
  --handoff handoff-outbox/RELEASE-SEQUENCE-SCH_ID \
  --require-stage handoff \
  --html launch-readiness.html
```

The stable stages distinguish quality and schedule blockers, readiness for approval, stale/current
approval, and invalid/current handoff evidence. `--at RFC3339` makes a time-aware report
reproducible; intended times that are due or past require rescheduling. Unscheduled items remain
visible and become blockers only with `--require-scheduled`.

The HTML board is exclusively created, self-contained, script-free, and usable offline. It includes
full draft content, so handle it like sensitive campaign source. It is a local snapshot—not hosted
team state, authenticated approval, a publisher queue, or proof of publication. See
[Launch readiness reports](docs/READINESS.md) for stages, JSON/schema and CI contracts, current
workflow research, privacy, and trust boundaries.

## CLI reference

```text
samsarix-campaign --help
samsarix-campaign --version
samsarix-campaign init [PATH]
samsarix-campaign validate CONFIG [--json]
samsarix-campaign preview CONFIG [--json]
samsarix-campaign check CONFIG [--warnings-as-errors] [--json]
samsarix-campaign export CONFIG [--output DIRECTORY] [--overwrite] [--json]
samsarix-campaign diff BEFORE AFTER [--json] [--exit-code]
samsarix-campaign approval create CONFIG --by LABEL [--at RFC3339] [--note TEXT] [--warnings-as-errors] [--output PATH] [--json]
samsarix-campaign approval verify CONFIG APPROVAL [--json]
samsarix-campaign plan validate PLAN [--json]
samsarix-campaign plan preview PLAN [--json]
samsarix-campaign plan check PLAN [--warnings-as-errors] [--json]
samsarix-campaign plan status PLAN [--approval PATH] [--handoff DIRECTORY] [--at RFC3339] [--warnings-as-errors] [--require-scheduled] [--require-stage quality|approval|handoff] [--html PATH] [--json]
samsarix-campaign plan diff BEFORE AFTER [--json] [--exit-code]
samsarix-campaign plan approval create PLAN --by LABEL [--at RFC3339] [--note TEXT] [--warnings-as-errors] [--output PATH] [--json]
samsarix-campaign plan approval verify PLAN APPROVAL [--json]
samsarix-campaign plan handoff create PLAN APPROVAL [--at RFC3339] [--output DIRECTORY] [--json]
samsarix-campaign plan handoff verify PLAN HANDOFF [--json]
samsarix-campaign plan export PLAN [--output DIRECTORY] [--overwrite] [--json]
samsarix-campaign schema [--kind campaign|plan|approval|plan-approval|adapter|handoff|readiness] [--output PATH]
```

Successful commands return exit code `0`. Validation and I/O failures return `1`; invalid CLI
usage returns `2`; a valid campaign that fails `check` returns `3`. Human-readable errors go to
stderr. Exit `4` means a requested diff detected changes, an approval is stale/invalid, or a
handoff is not current and intact, or a requested approval/handoff readiness stage is unmet.
`plan status --require-stage quality` uses `3` when its quality/schedule gate is unmet. Without a
required stage, status is informational. Quality, diff, approval, handoff, and readiness
reports—including non-passing JSON reports—stay on stdout for scripts.

## Python API

```python
from samsarix_creative_spirals import build_campaign, check_campaign, export_campaign, load_campaign

config = load_campaign("examples/campaign.json")
bundle = build_campaign(config)       # deterministic and side-effect free
report = check_campaign(bundle)
if not report.publishable:
    raise SystemExit(report.to_dict())
for draft in bundle.drafts:
    print(draft.platform, draft.character_count, draft.content)

path = export_campaign(bundle, "outbox")
print(path)
```

See [API.md](docs/API.md) for the deliberately small public surface and error behavior.

## Development and verification

Install the pinned development toolchain:

```bash
python -m pip install -r requirements-dev.txt
```

Run the same checks enforced by CI:

```bash
python -m black --check samsarix_creative_spirals tests examples
python -m flake8 samsarix_creative_spirals tests examples
python -m mypy
python -m pytest --cov=samsarix_creative_spirals --cov-report=term-missing
python -m build
```

CI runs these checks on Python 3.10 and 3.13 and smoke-tests the built wheel, schema resource, and
console command. The package has no third-party runtime dependencies.

## Architecture and boundaries

- `models.py` validates and normalizes local JSON input.
- `formatters.py` creates bounded platform drafts without network access.
- `workflow.py` computes deterministic IDs and safely exports review bundles.
- `quality.py` evaluates deterministic, machine-readable campaign quality gates.
- `plans.py` validates, builds, checks, and exports bounded multi-campaign sequences.
- `review.py` computes semantic diffs and creates/verifies source-bound local approvals.
- `plan_review.py` reviews and approves complete launch-plan state without publishing it.
- `handoff.py` creates and verifies exclusive approved-plan packets and exact artifact bytes.
- `readiness.py` consolidates time-aware quality and evidence state and renders offline HTML.
- `schema.py` exposes campaign, plan, approval, handoff, readiness, and adapter JSON Schemas bundled in the wheel.
- `cli.py` maps these operations to stable commands and exit codes.

Build and check functions have no file or network side effects. Load, explicit schema output, and
export functions touch disk; none contact a platform. See [ARCHITECTURE.md](docs/ARCHITECTURE.md)
for trust boundaries and failure behavior.

## Security, privacy, cost, and limitations

- Draft content stays on the local machine; there is no network client, telemetry, database, or
  credential loading.
- Input files are capped at 1 MB and content fields are bounded. Duplicate or excessively nested
  JSON, unknown fields, control characters, unsafe URL schemes, URL credentials, duplicate
  platforms, and invalid hashtags are rejected.
- Plans contain at most 100 items. Referenced campaign paths cannot be absolute, traverse parents,
  use platform-specific separators, or escape through symbolic links.
- Export paths are generated from a sanitized name plus a content hash. Existing bundles are not
  overwritten without explicit opt-in, and symbolic-link bundle targets are rejected.
- Discord broadcast mentions are surfaced as warnings. This tool never posts them.
- Runtime operating cost is zero beyond local compute and storage.
- Platform policies and edge-case counting rules change. Review final text in each platform's own
  composer before publishing; this tool does not claim API conformance.
- Mastodon limits are instance-configurable; the default is 500 and `platformLimits` records a
  known instance maximum without contacting that instance.
- Local approval labels are not authenticated and approval files are forgeable by anyone who can
  write them. Use repository permissions, pull-request review, or a separately designed signing
  system when verified identity is required.
- Approved handoff hashes detect stale source and modified bytes but remain unsigned. They do not
  prove signer identity or authenticated provenance, and verification should occur immediately
  before a downstream consumer uses the same packet directory.
- Media-file processing, per-account capabilities, cryptographic approvals, hosted collaboration,
  network publishing, and analytics are outside the 0.9 scope. Calendar and readiness files record
  intent and local evidence; they do not schedule or publish anything.

Security reports belong at `support@samsarix.com`; see [SECURITY.md](SECURITY.md).

## Distribution and license

The simplest distribution is a source checkout or locally built wheel installed with `pipx` or
`pip`. The package is not currently published on PyPI, so do not assume
`pip install samsarix-creative-spirals` resolves from the public index.

The code is licensed under [MPL-2.0](LICENSE), a file-level copyleft license selected to keep
distributed changes to covered source files open while allowing use in larger works. Copyright
and origin notices are in [NOTICE](NOTICE), practical licensing context is in
[LICENSING.md](LICENSING.md), and brand use is addressed in [TRADEMARKS.md](TRADEMARKS.md).

General and licensing contact: `contact@samsarix.com`

Support and security contact: `support@samsarix.com`

See [PRODUCTIZATION.md](docs/PRODUCTIZATION.md) for the evidence, completed work, known risks, and
release gates. Contribution instructions are in [CONTRIBUTING.md](CONTRIBUTING.md).
