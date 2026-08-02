# Samsarix Creative Spirals

Samsarix Creative Spirals is a local-first CLI and typed Python library that turns approved source
drafts into copy-ready files for X, LinkedIn, Bluesky, Mastodon, and Discord. It validates campaign
input, supports deliberate per-platform copy, applies platform-aware limits, checks complete launch sequences, and exports review bundles,
publisher-neutral CSV, and portable calendars. Portable image references, semantic diffs, and
deterministic link attribution, portable content-policy profiles, and source-bound campaign and
plan approval records make exact changes and guardrails visible before handoff.
Approved handoff packets then bind current source, approval metadata, exact rendered files, and
optionally the exact reviewed JPEG/PNG bytes for offline verification immediately before downstream
use. A handoff-bound publication ledger can
then reconcile operator-recorded published, failed, skipped, and pending outcomes without opening
a URL or claiming provider verification. A consolidated readiness command and offline HTML board
show the current quality, schedule, approval, handoff, and optional publication stage in one place.

It is for solo creators, developer advocates, and small content teams that want a scriptable
review/export step without connecting social accounts or sending draft content to a service.

> Maturity: **0.14 alpha.** Approval-bound static-image packets, publication reconciliation,
> deterministic link tracking, portable phrase policies, platform-native content variants,
> federated-platform drafts, campaign-plan quality gates, whole-plan semantic review and local
> approvals, portable image metadata, approved handoff verification, and
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
  "platformVariants": {
    "x": {
      "body": "One campaign, five reviewable outputs—without connecting an account.",
      "hashtags": ["buildinpublic"]
    }
  },
  "platformLimits": {"mastodon": 1000},
  "linkTracking": {
    "parameters": {"utm_campaign": "product-launch", "utm_medium": "social"},
    "platformParameters": {"x": {"utm_source": "x"}}
  },
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
| `platformVariants` | no | Complete content overrides keyed by a requested canonical platform. Each requires `body`; omitted `title`, `link`, and `hashtags` do not inherit from the baseline. |
| `platformLimits` | no | Stricter per-platform limits, or a Mastodon instance limit up to 100,000. Keys must also appear in `platforms`. |
| `linkTracking` | no | Up to 20 deterministic query parameters in each merged effective requested-platform map, with optional platform overrides. Existing-name conflicts are rejected. |
| `media` | no | Up to 20 portable JPEG/PNG references, with required alt text and at most four images targeted to each platform. |

Media paths are metadata relative to the campaign file. Ordinary validate, preview, check, diff,
approval, export, and handoff workflows do not dereference them. Add `--include-media` specifically
to plan approval creation to inspect and bind the exact local JPEG/PNG bytes; a later handoff then
packages those same approval-bound bytes automatically. References participate in campaign hashes,
diffs, approvals, manifests, and adapter v2 output. See
[Portable media references](docs/MEDIA.md) for targeting, path rules, platform rationale, and the
filesystem/provider checks required of an external adapter.

Use a variant when a channel needs genuinely different copy, mentions, call to action, link, or
hashtags. Platforms without a variant use the baseline. See
[Platform-native content variants](docs/VARIANTS.md) for replacement semantics, review behavior,
compatibility, and a runnable example.

Use `linkTracking` to append stable, percent-encoded attribution values to the effective structured
link before review. Per-platform values add to common parameters and replace common values with the
same name; fragments are preserved and existing-name collisions fail validation. Body text is never
scanned or rewritten. See
[Deterministic link tracking](docs/TRACKING.md) for the contract, current workflow evidence,
analytics limitations, and a runnable example.

Print the bundled JSON Schema for editor or CI integration, or write it to a new file:

```bash
samsarix-campaign schema
samsarix-campaign schema --kind plan
samsarix-campaign schema --kind approval
samsarix-campaign schema --kind plan-approval
samsarix-campaign schema --kind adapter
samsarix-campaign schema --kind handoff
samsarix-campaign schema --kind media-package
samsarix-campaign schema --kind readiness
samsarix-campaign schema --kind publication
samsarix-campaign schema --kind content-policy
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

Apply repository-owned literal phrase guardrails to the final rendered platform drafts:

```bash
samsarix-campaign policy validate examples/content-policy.json --json
samsarix-campaign check examples/campaign-variants.json \
  --policy examples/content-policy.json --json
```

Policies can block or require an exact phrase globally or on selected platforms, with warning or
error severity. They are bounded, deterministic JSON—not regex, AI moderation, or legal
compliance. See [Portable content policies](docs/POLICIES.md) for the contract and trust model.

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

Add the same `--policy content-policy.json` argument to both commands to bind the normalized policy
hash into approval. Once bound, omitting or changing that policy makes verification fail.

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

When a plan references real images and review must cover their exact pixels, create the plan
approval with `--include-media`. Samsarix resolves each reference beneath its campaign directory,
rejects symbolic links and unstable reads, validates bounded static JPEG/PNG structure and
dimensions, and records a content-addressed `scm_*` snapshot in the approval. The portable ceiling
is 2,000,000 bytes per file, 36,152,319 pixels, 400 plan references, and 100 MB of unique image
bytes per packet. Provider, account, and Mastodon-instance rules still require downstream
revalidation.

Plan export writes `manifest.json`, `calendar.ics`, and one UTF-8 CSV per used platform. Scheduled
items become transparent calendar events; unscheduled items become tasks. CSV timestamps are
explicit UTC values and the stable columns are publisher-neutral—they are intended for review and
spreadsheet workflows, not presented as a drop-in template for every publisher.

It also writes deterministic `adapter.json`, which preserves exact draft text and media references
in a versioned JSON contract for separately permissioned importers. See [ADAPTERS.md](docs/ADAPTERS.md) for schema,
identity, idempotency, authorization, and compatibility rules.

## Approved downstream handoff

After the complete plan is approved, create one non-overwriting packet that contains the embedded
approval, any approval-bound normalized policy, exact plan-export artifacts, and any exact image
snapshot bound with `--include-media`:

```bash
samsarix-campaign plan handoff create \
  examples/launch-plan.json \
  examples/launch-plan.json.approval.json \
  --output handoff-outbox
samsarix-campaign plan handoff verify \
  examples/launch-plan.json \
  handoff-outbox/RELEASE-SEQUENCE-SCH_ID
```

Verification rechecks current source and the recorded quality policy, uses an embedded content
policy automatically, regenerates every expected artifact, checks byte lengths and SHA-256 values,
and rejects missing, substituted, symbolic-link, or extra files. The packet is the safe input boundary for a manual workflow or separately
permissioned adapter; it does not connect an account, queue, schedule, or publish anything.
Media-bound packets add `media-index.json` and deduplicated content-addressed files beneath
`media/`; verification checks those bytes against the exact snapshot named by the approval.

The hashes are unsigned integrity checks. They do not authenticate the reviewer or producer and
are not cryptographic attestations. See [Approved handoff packets](docs/HANDOFFS.md) for the packet
contract, CLI/adapter workflow, threat model, and retention guidance.

## Publication reconciliation

After a verified handoff is used by a person or separately authorized publisher, initialize one
sidecar record for every generated plan/platform draft:

```bash
samsarix-campaign plan publication init \
  examples/launch-plan.json \
  handoff-outbox/RELEASE-SEQUENCE-SCH_ID \
  --output launch-plan.publication.json
```

Edit each `pending` record to `published`, `failed`, or `skipped`, adding the required operator,
time, URL, or note fields. Then verify exact coverage and current bindings:

```bash
samsarix-campaign plan publication verify \
  examples/launch-plan.json \
  handoff-outbox/RELEASE-SEQUENCE-SCH_ID \
  launch-plan.publication.json
```

Completion means every exact draft is recorded as `published` or intentionally `skipped`.
Operator labels are unauthenticated, URLs are never opened, and neither a URL nor a `published`
status proves remote delivery, visibility, authorship, or continued availability. See
[Publication ledgers](docs/PUBLICATIONS.md) for the JSON contract, current workflow evidence,
failure/retry semantics, CI gate, and trust boundary.

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
approval, invalid/current handoff evidence, and optional publication progress/completion.
`--at RFC3339` makes a time-aware report
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
samsarix-campaign check CONFIG [--policy POLICY] [--warnings-as-errors] [--json]
samsarix-campaign export CONFIG [--output DIRECTORY] [--overwrite] [--json]
samsarix-campaign diff BEFORE AFTER [--json] [--exit-code]
samsarix-campaign approval create CONFIG --by LABEL [--policy POLICY] [--at RFC3339] [--note TEXT] [--warnings-as-errors] [--output PATH] [--json]
samsarix-campaign approval verify CONFIG APPROVAL [--policy POLICY] [--json]
samsarix-campaign policy validate POLICY [--json]
samsarix-campaign plan validate PLAN [--json]
samsarix-campaign plan preview PLAN [--json]
samsarix-campaign plan check PLAN [--policy POLICY] [--warnings-as-errors] [--json]
samsarix-campaign plan status PLAN [--policy POLICY] [--approval PATH] [--handoff DIRECTORY] [--publication PATH] [--at RFC3339] [--warnings-as-errors] [--require-scheduled] [--require-stage quality|approval|handoff|publication] [--html PATH] [--json]
samsarix-campaign plan diff BEFORE AFTER [--json] [--exit-code]
samsarix-campaign plan approval create PLAN --by LABEL [--policy POLICY] [--at RFC3339] [--note TEXT] [--warnings-as-errors] [--include-media] [--output PATH] [--json]
samsarix-campaign plan approval verify PLAN APPROVAL [--policy POLICY] [--json]
samsarix-campaign plan handoff create PLAN APPROVAL [--policy POLICY] [--at RFC3339] [--output DIRECTORY] [--json]
samsarix-campaign plan handoff verify PLAN HANDOFF [--policy POLICY] [--json]
samsarix-campaign plan publication init PLAN HANDOFF [--policy POLICY] [--at RFC3339] [--output PATH] [--json]
samsarix-campaign plan publication verify PLAN HANDOFF PUBLICATION [--policy POLICY] [--at RFC3339] [--json]
samsarix-campaign plan export PLAN [--output DIRECTORY] [--overwrite] [--json]
samsarix-campaign schema [--kind campaign|content-policy|plan|approval|plan-approval|adapter|handoff|media-package|publication|readiness] [--output PATH]
```

Successful commands return exit code `0`. Validation and I/O failures return `1`; invalid CLI
usage returns `2`; a valid campaign that fails `check` returns `3`. Human-readable errors go to
stderr. Exit `4` means a requested diff detected changes, an approval is stale/invalid, or a
handoff is not current and intact, a publication ledger is incomplete/invalid, or a requested
approval/handoff/publication readiness stage is unmet.
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
- `formatters.py` applies deterministic link attribution and creates bounded platform drafts without network access.
- `workflow.py` computes deterministic IDs and safely exports review bundles.
- `quality.py` evaluates deterministic, machine-readable campaign quality gates.
- `plans.py` validates, builds, checks, and exports bounded multi-campaign sequences.
- `review.py` computes semantic diffs and creates/verifies source-bound local approvals.
- `plan_review.py` reviews and approves complete launch-plan state without publishing it.
- `media_package.py` captures, validates, indexes, and approval-binds opt-in static image bytes.
- `handoff.py` creates and verifies exclusive approved-plan packets and exact artifact bytes.
- `publication.py` initializes and verifies handoff-bound operator outcome ledgers.
- `readiness.py` consolidates time-aware quality and evidence state and renders offline HTML.
- `schema.py` exposes campaign, plan, approval, media-package, handoff, publication, readiness, and adapter JSON Schemas bundled in the wheel.
- `cli.py` maps these operations to stable commands and exit codes.

Build and check functions have no file or network side effects. Load, explicit schema output, and
export functions touch disk; none contact a platform. See [ARCHITECTURE.md](docs/ARCHITECTURE.md)
for trust boundaries and failure behavior.

## Security, privacy, cost, and limitations

- Draft content stays on the local machine; there is no network client, telemetry, database, or
  credential loading.
- Input files are capped at 1 MB and content fields are bounded. Duplicate or excessively nested
  JSON, unknown fields, control characters, unsafe URL schemes, URL credentials, duplicate
  platforms, unrequested or non-canonical variant keys, and invalid hashtags are rejected.
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
- `--include-media` performs a bounded local read and structural JPEG/PNG inspection; it does not
  fully decode pixels, scan for malware, establish copyright or consent, or prove acceptance by a
  particular account or Mastodon instance. Packaged images may contain sensitive data and increase
  local storage by up to 100 MB per handoff.
- Publication records are unsigned operator assertions. Their URLs are bounded and never opened;
  they do not prove provider acceptance, remote visibility, authorship, or continued availability.
- Media transformation, per-account capabilities and mention resolution, cryptographic approvals,
  hosted collaboration, network publishing, click collection, and analytics reporting are outside
  the 0.14 scope. Calendar, readiness, and publication files record
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
