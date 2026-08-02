# Python API

The supported public API is intentionally small. Imports not listed here are internal and may
change without notice.

## Models

### `CampaignConfig`

`CampaignConfig.from_dict(mapping)` validates and normalizes a JSON-compatible mapping. It returns
an immutable dataclass with `schema_version`, `name`, `body`, `platforms`, `title`, `link`,
`hashtags`, normalized `platform_limits`, and `media`. `limit_for(platform)` returns an explicit override or
the supported default. `to_dict()` returns the normalized JSON shape.

### `MediaReference`

An immutable portable image reference with `path`, required `alt_text`, and normalized target
`platforms`. `applies_to(platform)` reports draft applicability. `to_dict()` emits source-level
metadata; `to_attachment_dict()` emits the exact `{path, altText}` shape carried by one draft. Core
does not dereference the path.

### `PlatformDraft`

An immutable result for one platform:

- `platform`
- `content`
- `character_count`
- `original_character_count`
- `character_limit`
- `truncated`
- `warnings`
- `media`

### `CampaignBundle`

An immutable collection with deterministic `campaign_id`, full SHA-256 `source_hash`, `name`,
normalized `media`, and ordered `drafts`. `to_dict()` produces machine-readable preview output.

### `QualityIssue`

One stable quality finding with `code`, `severity`, `platform`, and human-readable `message`.

### `CampaignCheck`

An immutable quality result with `campaign_id`, `publishable`, and ordered `issues`. `to_dict()`
returns the same schema used by `samsarix-campaign check --json`.

### Campaign-plan models

`CampaignPlan` is the validated source sequence and contains immutable `CampaignPlanItem` values.
`CampaignPlanBundle` contains deterministic `PlannedCampaign` builds. `PlanIssue` and
`CampaignPlanCheck` provide the aggregate quality contract, including a one-based item number and
optional campaign/platform context. Every model has `to_dict()` for stable JSON output.

### Semantic-review models

`CampaignDiff` contains ordered `CampaignFieldChange` and `CampaignDraftChange` values plus the
before/after campaign IDs and full source hashes. `CampaignApproval` is source-bound local metadata;
`ApprovalIssue` and `ApprovalCheck` report whether that metadata still matches current source and
quality. These immutable models provide `to_dict()` output. Approval labels are not authenticated
identities or digital signatures.

`CampaignPlanDiff` contains ordered `PlanFieldChange` and `PlanItemChange` values. Each item change
has compact before/after `PlanItemSnapshot` values and, when referenced campaign content changed,
a nested `CampaignDiff`. `CampaignPlanApproval` is full-plan source-bound metadata;
`PlanApprovalCheck` reports whether it still matches plan identity and quality.

### Approved-handoff models

`CampaignPlanHandoff` is the strict unsigned handoff v1 manifest. It contains the `sch_*` identity,
full metadata hash, plan identity, UTC generation time, producer version, and ordered
`HandoffArtifact` descriptors. `CampaignPlanHandoffPacket` pairs that metadata and its embedded
`CampaignPlanApproval` with the packet root. `HandoffIssue` and `HandoffCheck` provide stable
machine-readable verification results. These hashes authenticate no person or system.

### `ConfigError`

Subclasses `ValueError`. `issues` is a tuple of one or more actionable validation messages. File
decoding and JSON syntax failures from `load_campaign` are also presented as `ConfigError` so CLI
and library consumers have one validation failure contract.

## Functions

### `load_campaign(path) -> CampaignConfig`

Reads a UTF-8 or UTF-8-with-BOM JSON file. Files larger than 1,000,000 bytes, non-object roots,
invalid JSON, invalid encodings, and schema violations raise `ConfigError`. No network access is
performed.

### `build_campaign(config) -> CampaignBundle`

Accepts a `CampaignConfig` or plain dictionary. It normalizes the source, hashes canonical JSON,
and formats each requested platform. Media metadata is selected into applicable drafts but no
referenced path is opened. Repeated calls with equal normalized input return equal bundles. It
performs no file or network I/O.

Supported platform defaults are X (280 weighted characters), LinkedIn (3,000 UTF-16 code units),
Bluesky (300 graphemes and 3,000 UTF-8 bytes), Mastodon (500 characters with 23-character URL
accounting), and Discord (2,000 UTF-16 code units). `platformLimits` may make any platform stricter;
Mastodon may be raised to match an intended instance's advertised limit.

### `check_campaign(bundle, *, warnings_as_errors=False) -> CampaignCheck`

Produces a deterministic quality report without file or network I/O. Truncation is always an error.
Other platform review warnings remain warnings unless `warnings_as_errors=True`. `publishable` is
true when the report contains no error-severity issue.

### `export_campaign(bundle, output_root="outbox", *, overwrite=False, exported_at=None) -> Path`

Creates `<safe-name>-<campaign-id>` beneath the resolved output root, writes one UTF-8 Markdown
file per draft, writes `manifest.json`, and returns the absolute bundle path.

The default refuses an existing bundle. `overwrite=True` replaces files only inside the generated
bundle directory. A non-directory or symbolic-link bundle target is rejected. `exported_at` exists
for reproducible tests; normal callers should leave it unset.

I/O failures raise the relevant `OSError` subclass.

### `diff_campaigns(before, after) -> CampaignDiff`

Accepts two validated `CampaignConfig` values or plain dictionaries. It compares normalized
`name`, `title`, `body`, `link`, hashtags, platform order, platform limits, and media, then compares every
generated draft in supported-platform order. Equivalent spelling that normalizes to the same
campaign produces `changed=False`. It performs no file or network I/O.

### `create_campaign_approval(bundle, *, approved_by, approved_at=None, warnings_as_errors=False, note=None) -> CampaignApproval`

Re-runs the selected quality policy and refuses to create an approval if it fails. The result binds
the reviewer label, UTC time, policy, optional note, campaign ID, and full normalized source hash.
`approved_at` must be timezone-aware when supplied. The result records review state; it does not
authenticate `approved_by`.

### `export_campaign_approval(approval, path) -> Path`

Writes one UTF-8 approval JSON file with exclusive-create behavior. Existing files are never
replaced. Parent directories are created when needed.

### `load_campaign_approval(path) -> CampaignApproval`

Reads a bounded UTF-8 JSON object and rejects duplicate/unknown fields, malformed identity hashes,
invalid timestamps, unsupported policies, controls, and overlong metadata.

### `verify_campaign_approval(bundle, approval) -> ApprovalCheck`

Requires both full source hash and campaign ID to match, then re-runs the policy stored in the
approval. `valid` is false with stable issue codes if source changed or quality no longer passes.

### `parse_approval_timestamp(value) -> datetime`

Parses an RFC 3339 timestamp with an explicit known offset and normalizes it to UTC. This is useful
for non-CLI callers that want the same timestamp contract as `approval create --at`.

### `load_campaign_schema() -> dict[str, Any]`

Loads a fresh dictionary from the JSON Schema bundled in the installed wheel. It performs no
network access and is useful for editor, form, or CI integration. The CLI exposes the same artifact
through `samsarix-campaign schema`.

### `load_campaign_plan(path) -> CampaignPlan`

Reads a bounded UTF-8 plan, resolves its campaign references beneath the plan directory, and loads
each campaign through the same validator as `load_campaign`. Plans contain 1–100 items. Campaign
paths are forward-slash relative `.json` paths without drive, root, empty, dot, or parent segments;
resolved symbolic-link escapes are rejected. `intendedAt` values require an explicit offset or `Z`
and normalize to UTC.

### `build_campaign_plan(plan) -> CampaignPlanBundle`

Builds every item in source order. The deterministic plan hash covers the normalized plan,
reference names, normalized UTC times, and every referenced normalized campaign configuration.

### `check_campaign_plan(bundle, *, warnings_as_errors=False) -> CampaignPlanCheck`

Runs every campaign check, fails on missing `requiredPlatforms`, and reports duplicate or
out-of-order intended times. Timing/order findings are warnings by default and errors when
`warnings_as_errors=True`.

### `diff_campaign_plans(before, after) -> CampaignPlanDiff`

Accepts two validated `CampaignPlan` values. It compares normalized `name`, required-platform
order, and every one-based sequence position. Item comparison covers the portable source path,
normalized intended time, and referenced campaign semantics. Reorders appear as modifications at
the affected positions. The function builds deterministic identities but performs no file or
network I/O; callers load plan files separately with `load_campaign_plan`.

### `create_campaign_plan_approval(bundle, *, approved_by, approved_at=None, warnings_as_errors=False, note=None) -> CampaignPlanApproval`

Re-runs the aggregate plan quality policy and refuses creation when it fails. The approval binds
the reviewer label, UTC time, policy, optional note, plan ID, and full plan source hash. That hash
covers order, schedule, required platforms, source references, and every normalized referenced
campaign. The reviewer label is not authenticated.

### `export_campaign_plan_approval(approval, path) -> Path`

Writes one UTF-8 plan approval JSON file with exclusive-create behavior. Existing evidence is
never replaced, and parent directories are created when needed.

### `load_campaign_plan_approval(path) -> CampaignPlanApproval`

Reads a bounded UTF-8 JSON object and validates the dedicated plan-approval v1 contract, including
artifact type, plan identity, timestamp, quality policy, and reviewer metadata.

### `verify_campaign_plan_approval(bundle, approval) -> PlanApprovalCheck`

Requires the full plan source hash and plan ID to match, then re-runs the stored quality policy.
Stable issue codes distinguish changed source, changed plan ID, and a current policy failure.

### `build_campaign_plan_handoff(bundle, approval, *, generated_at) -> CampaignPlanHandoff`

Re-verifies the approval and recorded aggregate quality policy, requires a timezone-aware handoff
time at or after approval, renders exact plan-export bytes, and returns deterministic unsigned
metadata for that input and timestamp. It performs no file or network I/O.

### `export_campaign_plan_handoff(bundle, approval, output_root="handoff-outbox", *, generated_at=None) -> Path`

Creates a private temporary directory, writes the embedded approval, handoff manifest, and exact
plan-export artifacts, then renames the complete directory into a generated `sch_*` path. It
refuses a symbolic-link/non-directory root and never replaces an existing packet.

### `load_campaign_plan_handoff(path) -> CampaignPlanHandoffPacket`

Loads bounded handoff and approval JSON from a non-symbolic-link directory and validates both
strict runtime contracts. Artifact content verification remains explicit.

### `verify_campaign_plan_handoff(bundle, packet) -> HandoffCheck`

Rechecks current source and approval quality, metadata identity and producer version, fixed packet
shape, on-disk metadata, and every regenerated artifact size and SHA-256. It rejects symbolic
links, non-regular files, missing/extra files, and files that change while read. `valid` does not
claim signer identity or authenticated provenance.

### `render_plan_calendar(bundle, *, generated_at) -> str`

Returns an RFC 5545 calendar using UTC date-times, CRLF lines, and UTF-8-safe 75-octet folding.
Scheduled items are transparent `VEVENT` components; unscheduled items are `VTODO` components.
`generated_at` must be timezone-aware because it supplies the required `DTSTAMP` values.

### `render_plan_adapter(bundle) -> str`

Returns deterministic UTF-8 JSON text for contract `samsarix.plan-drafts` schema version 2. It
contains plan/campaign identities, intended UTC times, normalized media references, and exact
generated `PlatformDraft` values, with no generation timestamp or external side effect.

### `export_campaign_plan(bundle, output_root="plan-outbox", *, overwrite=False, generated_at=None) -> Path`

Writes a plan manifest, deterministic `adapter.json`, `calendar.ics`, and one UTF-8 CSV per used
platform. CSV columns are stable
and publisher-neutral: plan/campaign identity, sequence, normalized intended UTC time, content,
counts, truncation, and warnings. The same generated-name, explicit-overwrite, symbolic-link, and
manifest-last safety model applies as campaign export.

### `load_plan_schema() -> dict[str, Any]`

Loads a fresh dictionary from the plan schema bundled in the wheel. The CLI equivalent is
`samsarix-campaign schema --kind plan`.

### `load_approval_schema() -> dict[str, Any]`

Loads a fresh dictionary from the approval schema bundled in the wheel. The CLI equivalent is
`samsarix-campaign schema --kind approval`.

### `load_plan_approval_schema() -> dict[str, Any]`

Loads a fresh dictionary from the separate campaign-plan approval schema bundled in the wheel.
The CLI equivalent is `samsarix-campaign schema --kind plan-approval`.

### `load_adapter_schema() -> dict[str, Any]`

Loads the versioned `samsarix.plan-drafts` adapter schema. The CLI equivalent is
`samsarix-campaign schema --kind adapter`; operational consumer rules are in `docs/ADAPTERS.md`.

### `load_handoff_schema() -> dict[str, Any]`

Loads the handoff v1 manifest schema. The CLI equivalent is
`samsarix-campaign schema --kind handoff`; packet and trust-boundary rules are in
`docs/HANDOFFS.md`.

## Example

```python
from samsarix_creative_spirals import (
    ConfigError,
    build_campaign,
    check_campaign,
    export_campaign,
    load_campaign,
)

try:
    config = load_campaign("campaign.json")
    bundle = build_campaign(config)
    report = check_campaign(bundle)
    if not report.publishable:
        raise ConfigError([issue.message for issue in report.issues])
    destination = export_campaign(bundle, "outbox")
except ConfigError as error:
    for issue in error.issues:
        print(issue)
except OSError as error:
    print(f"Export failed: {error}")
else:
    print(destination)
```

## Compatibility policy

The package is pre-1.0. The exported names, campaign/plan/approval/handoff JSON
`schemaVersion: 1`, adapter `schemaVersion: 2`, manifest shape, and documented CLI behavior are the
compatibility surface for 0.8.x. Internal helpers and exact prose in warning
messages may evolve. Breaking schema or public API changes require a minor-version increment while
the package remains pre-1.0.
