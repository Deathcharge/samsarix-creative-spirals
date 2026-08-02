# Architecture

## Product boundary

Samsarix Creative Spirals is a local transformation and export layer. It begins with human-approved
text and ends with reviewable local files. It has no provider clients, account connectors,
scheduler, background process, persistence service, analytics, or dependency on another Samsarix
repository.

```text
campaign.json + optional platform content overrides + media path metadata
    │ bounded UTF-8 read + strict validation
    ▼
CampaignConfig
    │ canonical JSON + SHA-256
    ├──────────────► deterministic campaign ID
    │ platform formatting and limit checks
    ▼
CampaignBundle
    ├──────────────► deterministic quality report / semantic diff
    ├──────────────► source-bound local approval verification
    │ explicit export only
    ▼
generated bundle directory
    ├── manifest.json
    └── one copy-ready Markdown file per platform
```

Campaign plans compose those standalone files without weakening their boundary:

```text
plan.json ──confined relative paths──► CampaignConfig (1..100)
    │                                      │
    │ canonical plan + campaign content    └──► CampaignBundle
    ▼
CampaignPlanBundle
    ├──► aggregate quality report
    ├──► deterministic plan diff / source-bound plan approval verification
    ├──► manifest.json + adapter.json + calendar.ics + per-platform CSV
    ├──► exclusive approved handoff packet
            ├── embedded approval.json + handoff.json
            └── exact regenerated plan-export artifacts
    └──► point-in-time readiness JSON / exclusive offline HTML board
            └── quality + schedule + approval + handoff evidence state
```

## Components

### `models.py`

Owns the schema and validation contract. It normalizes line endings and Unicode, rejects unknown
fields, bounds all collections and large text, restricts links to HTTP(S), and prevents embedded
URL credentials. Portable media paths and alt text are validated as metadata without touching the
filesystem. Models are immutable to keep one build internally consistent.

### `formatters.py`

Selects a complete platform content override when present, otherwise the campaign baseline, then
composes title, body, link, and hashtags. X uses its published weighted ranges
and 23-character URL accounting. Truncation keeps URLs atomic, avoids dangling combining marks and
joiners, preserves suffix metadata where possible, and records any omission. LinkedIn and Discord
use conservative character limits. Discord broadcast mentions are warnings, not silently altered.

### `workflow.py`

Separates pure building from I/O. Canonical normalized JSON produces a full source hash and short
deterministic campaign ID. Export derives, rather than accepts, the final child directory name.
New bundles are assembled in a private temporary sibling and renamed into place. Overwrite is
opt-in, rejects non-directory/symbolic-link targets, replaces the manifest last, and never writes
outside the generated child path.

### `quality.py`

Converts a built bundle into stable error/warning findings. Truncation is a blocking issue; review
warnings are optionally promoted to errors. The operation is pure and gives CI a distinct exit path
without conflating valid-but-unacceptable output with malformed configuration.

### `plans.py`

Validates a bounded sequence of relative campaign references and explicit-offset intended times.
References must remain beneath the plan directory even after symbolic-link resolution. Canonical
plan identity includes each normalized campaign configuration, so a referenced content change
changes the plan ID. Aggregate checks report missing required channels, duplicate or out-of-order
times, and every campaign finding. Export writes a commit-last manifest, neutral CSV files, and an
RFC 5545 calendar with UTF-8-safe 75-octet folding and CRLF line endings. Its deterministic
`adapter.json` preserves exact drafts and applicable media references for consumers of the
versioned publisher-neutral contract.

### `review.py`

Compares normalized campaign fields and generated platform drafts in stable order. Local approval
creation first runs the selected quality policy, then records the exact full source hash. Approval
verification compares current identity and re-runs that stored policy. Reviewer labels and files
are intentionally non-cryptographic; repository access control remains outside the package.

### `plan_review.py`

Compares normalized plan metadata and ordered positions, with nested campaign diffs when content
changes. Plan approval creation gates the whole built sequence and binds the full plan hash;
verification checks identity and re-runs the stored aggregate quality policy. The campaign
approval v1 contract remains separate so existing consumers do not need to distinguish a union.

### `handoff.py`

Creates an approved plan handoff only after current approval verification and a generation time at
or after approval. The handoff manifest binds plan identity, producer version, generation time,
embedded approval, and fixed rendered artifacts by size and SHA-256. Export is exclusive and uses
a private temporary sibling plus directory rename. Verification regenerates exact bytes from
current source, rejects unexpected entries, symbolic links, and non-regular files, and checks that
files remain stable during reads. Hashes are unsigned integrity metadata, not authenticated
provenance or authorization.

### `readiness.py`

Combines existing verification primitives without duplicating or weakening them. It evaluates
aggregate quality under an explicit policy, compares intended times with one timezone-aware
assessment time, verifies optional approval/handoff evidence, and assigns one stable stage. The
pure model emits readiness v1 JSON; an explicit exporter writes a new self-contained, escaped,
script-free HTML board containing the generated drafts. The report is a snapshot, not persistent
workflow state or a publication receipt.

### `schema.py` and bundled JSON Schemas

Package the authoring and interchange contracts with the wheel and return a fresh decoded
dictionary to library callers. Campaign, plan, campaign-approval, plan-approval, handoff,
readiness, and adapter schemas help editors and generic validators, while runtime models remain
authoritative and provide more actionable error messages.

### `cli.py`

Provides the single-campaign, diff, approval, handoff, readiness, and nested plan operations. Successful
output and valid quality/review reports stay on stdout;
configuration/I/O errors stay on stderr. Validation/I/O errors return `1`, usage errors return `2`,
quality-gate failures return `3`, semantic-change/stale-approval/invalid-handoff results return `4`,
and success returns `0`. Readiness is informational unless an explicit stage is required; its
quality gate uses `3` and its approval/handoff gates use `4`.

## Trust boundaries

| Boundary | Untrusted input | Control |
| --- | --- | --- |
| Config file | Local path and bytes | 1 MB file cap, UTF-8 decoding, strict JSON object/schema. |
| Plan references | Relative campaign paths | 100-item cap, portable path rules, resolved containment beneath plan directory. |
| Campaign fields | Baseline and per-platform text, URL, hashtags, platforms, limit overrides | Length bounds, control checks, URL scheme/credential checks, canonical/requested platform allowlists, hard platform ceilings. |
| Media metadata | Relative path, alt text, target platforms | Portable path allowlist, case-insensitive uniqueness, alt-text/collection bounds, no core dereference. |
| Platform output | User-authored draft text | No execution or network send; visible limit and mention warnings. |
| Output root | User-selected filesystem path | Generated safe child name, existing-target checks, explicit overwrite. |
| Approval file | Local JSON and reviewer label | Strict bounded schema, full source-hash match, quality re-check; no identity claim. |
| Plan approval file | Local JSON and complete launch identity | Dedicated strict schema, plan/hash match, aggregate quality re-check; no identity claim. |
| Approved handoff packet | Local directory, metadata, and generated files | Exclusive atomic creation; fixed shape; source, approval, version, size, checksum, exact-byte, file-type, and read-stability checks; unsigned. |
| Readiness report | Local evidence, assessment time, and complete draft text | Existing verifiers; bounded schema; exclusive HTML output; escaping; CSP; no scripts/remote resources; point-in-time and unsigned. |

The package never interprets draft content as a command, template language, HTML, or filesystem
path. Media references are explicitly path metadata but core never resolves or opens them. It
never reads environment variables or logs draft content automatically. A separately permissioned
adapter that dereferences media crosses a new trust boundary and must enforce the containment,
symlink, file-type, size, MIME, provider, and authorization controls in `docs/MEDIA.md`.

## Reliability and recovery

- Preview is deterministic and has no write side effects.
- Campaign and plan identities change whenever normalized source input changes; plan identity also
  covers every referenced campaign configuration.
- Export refuses an existing ID by default, which protects reviewed artifacts from accidental
  replacement.
- New bundle creation uses a temporary sibling and atomic directory rename on the same filesystem.
- During an explicit overwrite, draft files are replaced before `manifest.json`; readers can treat
  the manifest as the commit marker.
- Plan calendars use transparent events for scheduled items and tasks for unscheduled items. They
  record intent but trigger no background work.
- Approved handoffs are immutable-by-convention and refuse replacement. Verification must precede
  downstream use of the same packet; it is an integrity boundary rather than a transaction lock or
  signer-authentication system.
- Readiness reports always record the assessment time and selected policies. Re-run them when time,
  source, evidence, or packet bytes may have changed; HTML files refuse implicit replacement.
- Failures are surfaced synchronously with actionable exceptions/exit codes. There are no retry
  loops, queues, concurrency, or shutdown concerns in the 0.10 scope.

## Dependency and cost model

Runtime uses only the Python standard library. Processing is linear in bounded local input size,
with no API calls, model tokens, hosted storage, or recurring operational cost.
