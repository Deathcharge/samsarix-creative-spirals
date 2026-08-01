# Architecture

## Product boundary

Samsarix Creative Spirals is a local transformation and export layer. It begins with human-approved
text and ends with reviewable local files. It has no provider clients, account connectors,
scheduler, background process, persistence service, analytics, or dependency on another Samsarix
repository.

```text
campaign.json
    │ bounded UTF-8 read + strict validation
    ▼
CampaignConfig
    │ canonical JSON + SHA-256
    ├──────────────► deterministic campaign ID
    │ platform formatting and limit checks
    ▼
CampaignBundle
    ├──────────────► deterministic quality report
    │ explicit export only
    ▼
generated bundle directory
    ├── manifest.json
    └── one copy-ready Markdown file per platform
```

## Components

### `models.py`

Owns the schema and validation contract. It normalizes line endings and Unicode, rejects unknown
fields, bounds all collections and large text, restricts links to HTTP(S), and prevents embedded
URL credentials. Models are immutable to keep one build internally consistent.

### `formatters.py`

Composes title, body, link, and hashtags for each platform. X uses its published weighted ranges
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

### `schema.py` and `campaign.schema.json`

Package the authoring contract with the wheel and return a fresh decoded dictionary to library
callers. The schema helps editors and generic validators, while `CampaignConfig` remains the
authoritative runtime validator and provides more actionable error messages.

### `cli.py`

Provides `init`, `validate`, `preview`, `check`, `export`, and `schema`. Successful output and
valid quality reports stay on stdout; configuration/I/O errors stay on stderr. Validation/I/O
errors return `1`, usage errors return `2`, quality-gate failures return `3`, and success returns `0`.

## Trust boundaries

| Boundary | Untrusted input | Control |
| --- | --- | --- |
| Config file | Local path and bytes | 1 MB file cap, UTF-8 decoding, strict JSON object/schema. |
| Campaign fields | Text, URL, hashtags, platforms, limit overrides | Length bounds, control checks, URL scheme/credential checks, allowlists, hard platform ceilings. |
| Platform output | User-authored draft text | No execution or network send; visible limit and mention warnings. |
| Output root | User-selected filesystem path | Generated safe child name, existing-target checks, explicit overwrite. |

The package never interprets draft content as a command, template language, HTML, or filesystem
path. It never reads environment variables or logs draft content automatically.

## Reliability and recovery

- Preview is deterministic and has no write side effects.
- Campaign identity changes whenever normalized source input changes.
- Export refuses an existing ID by default, which protects reviewed artifacts from accidental
  replacement.
- New bundle creation uses a temporary sibling and atomic directory rename on the same filesystem.
- During an explicit overwrite, draft files are replaced before `manifest.json`; readers can treat
  the manifest as the commit marker.
- Failures are surfaced synchronously with actionable exceptions/exit codes. There are no retry
  loops, queues, concurrency, or shutdown concerns in the 0.3 scope.

## Dependency and cost model

Runtime uses only the Python standard library. Processing is linear in bounded local input size,
with no API calls, model tokens, hosted storage, or recurring operational cost.
