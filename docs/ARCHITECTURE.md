# Architecture

## Product boundary

Samsarix Creative Spirals is a local transformation and export layer. It begins with human-approved
text and ends with reviewable local files. It has no provider clients, account connectors,
scheduler, background process, persistence service, analytics, or dependency on another Samsarix
repository.

```text
campaign.json + optional platform content overrides + link tracking + media path metadata
    │ bounded UTF-8 read + strict validation
    ▼
CampaignConfig
    │ canonical JSON + SHA-256
    ├──────────────► deterministic campaign ID
    │ platform formatting and limit checks
    ▼
CampaignBundle
    ├── content-policy.json ──► deterministic quality report
    ├── another CampaignBundle ──► semantic diff of campaign fields and rendered drafts
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
    │       ├── approval-policy.json + independent approvals ──► canonical scas_* set
    │       └── optional exact media collection ──► approval-bound scm_* snapshot
    ├──► manifest.json + adapter.json + calendar.ics + per-platform CSV
    ├──► exclusive approved handoff packet
            ├── embedded approval.json + optional content-policy.json + handoff.json
            └── exact regenerated plan-export artifacts + optional content-addressed images
    └──► point-in-time readiness JSON / exclusive offline HTML board
            └── quality + schedule + approval + handoff + optional publication evidence state

verified handoff + plan-publication.json
    └──► exact per-draft outcome reconciliation
            ├── pending / failed ──► incomplete
            └── published / skipped ──► complete when every draft is terminal
```

## Components

### `models.py`

Owns the schema and validation contract. It normalizes line endings and Unicode, rejects unknown
fields, bounds all collections and large text, restricts links to HTTP(S), prevents embedded URL
credentials, and validates bounded common/per-platform tracking parameter maps. Portable media
paths and alt text are validated as metadata without touching the filesystem. Models are
immutable to keep one build internally consistent.

### `formatters.py`

Selects a complete platform content override when present, otherwise the campaign baseline,
applies deterministic tracking parameters to the effective structured link, then composes title,
body, link, and hashtags. Existing query strings and fragments are preserved; collisions fail
source validation instead of being replaced. X uses its published weighted ranges
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

### `policy.py`

Validates bounded portable policy profiles, normalizes rule defaults, and derives a full SHA-256
identity plus short display ID. It applies literal blocked/required phrases to final rendered draft
content with optional platform targets, casing, and warning/error severity. Regex, semantic models,
network calls, and media dereferencing are deliberately excluded. A small binding verifier makes
approval omission or substitution explicit.

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
verification compares current identity, requires the exact external content policy when one was
bound, and re-runs that stored policy. Reviewer labels and files
are intentionally non-cryptographic; repository access control remains outside the package.

### `plan_review.py`

Compares normalized plan metadata and ordered positions, with nested campaign diffs when content
changes. Plan approval creation gates the whole built sequence and binds the full plan hash;
verification checks identity, requires the exact external content policy when one was bound, and
re-runs the stored aggregate quality policy. The campaign
approval v1 contract remains separate so existing consumers do not need to distinguish a union.

### `approval_policy.py`

Validates bounded role/count policies, derives deterministic `scap_*` policy identities, and
normalizes independently created plan approvals into canonical `scas_*` sets. Collection requires
one exact plan/source/content-policy/media binding, rejects duplicate evidence, enforces all role
and total minimums, optionally compares case-folded reviewer labels, and reverifies every member.
Labels and roles are unsigned metadata; the module supplies no account or authorization system.

### `media_package.py`

Implements the sole opt-in media dereference boundary. A trusted plan root plus normalized campaign
references resolve to campaign-relative files with no symbolic-link component. One stable bounded
open captures regular-file bytes, structural JPEG/PNG inspection derives dimensions and normalized
content type, and SHA-256 content addressing deduplicates packet files. The canonical media index
binds every source reference, alt text, target set, dimension, size, and checksum to an `scm_*`
identity. Collection performs no network request, full pixel decode, transformation, or upload.

### `handoff.py`

Creates an approved plan handoff only after current approval verification and a generation time at
or after approval. The handoff manifest binds plan identity, producer version, generation time,
embedded approval, optional normalized approval-bound policy, and fixed rendered artifacts by size
and SHA-256. An optional media index is itself a declared artifact and transitively binds every
content-addressed image. Export is exclusive and uses a private temporary sibling plus directory rename.
Verification uses the embedded policy by default, regenerates exact bytes from current source,
rejects unexpected entries, symbolic links, and non-regular files, and checks that files remain
stable during reads. Hashes are unsigned integrity metadata, not authenticated provenance or
authorization.

### `readiness.py`

Combines existing verification primitives without duplicating or weakening them. It evaluates
aggregate quality under an explicit policy, compares intended times with one timezone-aware
assessment time, verifies optional approval/handoff evidence, and assigns one stable stage. The
pure model emits readiness v1 JSON; an explicit exporter writes a new self-contained, escaped,
script-free HTML board containing the generated drafts. The report is a snapshot, not persistent
workflow state or a provider-verified publication receipt.

### `publication.py`

Creates a canonical pending sidecar only after exact handoff verification. It validates strict
operator outcome combinations, derives content identity, and verifies current plan/handoff
bindings, exact draft coverage/order, chronology, and completion. Published URLs are bounded text:
the module never opens them, restricts federated hostnames, or claims remote state. Operator
labels and hashes are unsigned.

### `schema.py` and bundled JSON Schemas

Package the authoring and interchange contracts with the wheel and return a fresh decoded
dictionary to library callers. Campaign, content-policy, plan, campaign-approval, plan-approval,
approval-policy, plan-approval-set, media-package, handoff, publication, readiness, and adapter schemas help editors and generic
validators, while runtime models remain
authoritative and provide more actionable error messages.

### `cli.py`

Provides the single-campaign, diff, approval, handoff, publication, readiness, and nested plan operations. Successful
output and valid quality/review reports stay on stdout;
configuration/I/O errors stay on stderr. Validation/I/O errors return `1`, usage errors return `2`,
quality-gate failures return `3`, semantic-change/stale-approval/invalid-handoff/incomplete-publication results return `4`,
and success returns `0`. Readiness is informational unless an explicit stage is required; its
quality gate uses `3` and its approval/handoff/publication gates use `4`.

## Trust boundaries

| Boundary | Untrusted input | Control |
| --- | --- | --- |
| Config file | Local path and bytes | 1 MB file cap, UTF-8 decoding, strict JSON object/schema. |
| Plan references | Relative campaign paths | 100-item cap, portable path rules, resolved containment beneath plan directory. |
| Campaign fields | Baseline and per-platform text, URL, hashtags, platforms, limit overrides | Length bounds, control checks, URL scheme/credential checks, canonical/requested platform allowlists, hard platform ceilings. |
| Link tracking | Common and per-platform query parameter names/values | Lowercase name grammar; parameter/value/count/final-URL bounds; requested-platform checks; existing-name collision rejection; deterministic percent encoding; no URL open or analytics collection. |
| Content policy | Local JSON, rule phrases, targets, severity, casing | Shared file/nesting limits, 50-rule and 200-character phrase caps, strict fields/IDs, literal matching only, deterministic identity. |
| Media metadata | Relative path, alt text, target platforms | Portable path allowlist, case-insensitive uniqueness, alt-text/collection bounds; no dereference by default. |
| Exact media collection | Trusted plan root and referenced local image files | Explicit opt-in; campaign-relative containment; no symlink components; stable regular-file read; 2,000,000-byte/file, 36,152,319-pixel, 400-reference, and 100 MB packet bounds; structural JPEG/PNG checks; content addressing. |
| Platform output | User-authored draft text | No execution or network send; visible limit and mention warnings. |
| Output root | User-selected filesystem path | Generated safe child name, existing-target checks, explicit overwrite. |
| Approval file | Local JSON and reviewer label | Strict bounded schema, full source-hash match, quality re-check; no identity claim. |
| Plan approval file | Local JSON and complete launch identity | Dedicated strict schema, plan/hash match, optional exact-media binding, aggregate quality re-check; no identity claim. |
| Approval policy/set | Role names, count rules, reviewer labels, and embedded approvals | 20-role/50-approval bounds; canonical identity; per-role/total/distinct-label checks; duplicate rejection; every approval reverified; no human identity or authorization claim. |
| Approved handoff packet | Local directory, metadata, approval/policy/media evidence, and generated files | Exclusive atomic creation; exact expected shape; source, approval, embedded-policy/media, version, size, checksum, exact-byte, file-type, and read-stability checks; unsigned. |
| Publication ledger | Local outcome JSON, operator labels, times, URLs, and notes | Shared file/nesting bounds; strict state combinations; exact plan/handoff/draft binding; chronology; URL scheme/credential/length checks; no network verification; unsigned. |
| Readiness report | Local evidence, assessment time, and complete draft text | Existing verifiers; bounded schema; exclusive HTML output; escaping; CSP; no scripts/remote resources; point-in-time and unsigned. |

The package never interprets draft or tracking content as a command, template language, HTML, environment substitution, or filesystem
path. Media references are path metadata unless the caller explicitly invokes exact-media
collection for plan approval; only that bounded operation resolves and opens them. It
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
- Publication ledgers are exclusive at initialization but intentionally edited as outcomes occur.
  Their derived identity changes with content. Commit or archive meaningful revisions when history
  matters; the core is not a transactional multi-user store.
- Readiness reports always record the assessment time and selected policies. Re-run them when time,
  source, evidence, or packet bytes may have changed; HTML files refuse implicit replacement.
- Failures are surfaced synchronously with actionable exceptions/exit codes. There are no retry
  loops, queues, concurrency, or shutdown concerns in the 0.15 scope.

## Dependency and cost model

Runtime uses only the Python standard library. Processing is linear in bounded local input size;
exact-media mode may copy up to 100 MB into each handoff. There are no API calls, model tokens,
hosted storage, or recurring operational costs.
