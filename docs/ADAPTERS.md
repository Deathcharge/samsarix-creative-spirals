# Adapter contract v1

Samsarix Creative Spirals exports `adapter.json` as the stable, publisher-neutral input for a
separately permissioned importer. The core package never loads provider credentials or sends the
payload. An adapter is responsible for authentication, account selection, provider-specific
validation, rate limits, retries, idempotency, and making every external side effect visible.

## Contract identity

- JSON `schemaVersion`: `1`
- JSON `contract`: `samsarix.plan-drafts`
- Bundled schema: `samsarix-campaign schema --kind adapter`
- Encoding: UTF-8 with a trailing newline
- Ordering: plan item order, then canonical Samsarix platform order
- Conformance fixture: `tests/fixtures/plan-export-v1/`

The payload is deterministic: it contains no generation timestamp. `planId` and full `sourceHash`
cover the normalized plan and all referenced normalized campaigns. Each item repeats its campaign
ID and full source hash, optional intended UTC time, and complete generated draft objects.

## Consumer rules

1. Read `manifest.json` as the export commit marker and require `adapter` to equal `adapter.json`.
2. Resolve only that exact sibling filename; do not accept an arbitrary path from an untrusted
   modified manifest.
3. Validate `adapter.json` against the bundled v1 schema and require its `planId` and `sourceHash`
   to match the manifest.
4. Treat `intendedAt` as human intent, never proof that a post was scheduled.
5. Revalidate content against the selected provider/account immediately before creating a draft.
6. Use `(planId, sequence, platform, sourceHash)` as an idempotency key where the provider permits.
7. Default to creating provider drafts. Publishing, scheduling, and destructive replacement need
   separate explicit operator authorization.

Unlike the spreadsheet-oriented CSV files, `adapter.json` preserves exact draft text without a
formula-neutralizing prefix. Do not render its content as HTML or execute it as a template. Treat
the payload as potentially sensitive campaign data and avoid logging it.

## Compatibility

Additive optional fields may appear within the v1 contract only after the schema permits them.
Removing or renaming fields, changing meaning, or changing identity rules requires a new contract
and schema version. Adapters should reject unknown `schemaVersion` or `contract` values instead of
guessing.

Provider-specific field mappings deliberately remain outside this repository until an adapter can
be tested against an official API and separately permissioned credentials. The generic contract is
not a claim that one payload can be uploaded directly to every publisher.
