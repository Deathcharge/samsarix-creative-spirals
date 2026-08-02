# Adapter contract v2

Samsarix Creative Spirals exports `adapter.json` as the stable, publisher-neutral input for a
separately permissioned importer. The core package never loads provider credentials or sends the
payload. An adapter is responsible for authentication, account selection, provider-specific
validation, rate limits, retries, idempotency, and making every external side effect visible.

## Contract identity

- JSON `schemaVersion`: `2`
- JSON `contract`: `samsarix.plan-drafts`
- Bundled schema: `samsarix-campaign schema --kind adapter`
- Encoding: UTF-8 with a trailing newline
- Ordering: plan item order, then canonical Samsarix platform order
- Conformance fixture: `tests/fixtures/plan-export-v2/`

The payload is deterministic: it contains no generation timestamp. `planId` and full `sourceHash`
cover the normalized plan and all referenced normalized campaigns. Each item repeats its campaign
ID and full source hash, optional intended UTC time, normalized campaign media, and complete
generated draft objects. Each draft carries only the `{path, altText}` pairs applicable to its
platform.

## Consumer rules

1. Read `manifest.json` as the export commit marker and require `adapter` to equal `adapter.json`.
2. Resolve only that exact sibling filename; do not accept an arbitrary path from an untrusted
   modified manifest.
3. Validate `adapter.json` against the bundled v2 schema and require its `planId` and `sourceHash`
   to match the manifest.
4. Treat `intendedAt` as human intent, never proof that a post was scheduled.
5. Revalidate content against the selected provider/account immediately before creating a draft.
6. Reject duplicate platform drafts and require canonical platform order.
7. Use `(planId, sequence, platform, sourceHash)` as an idempotency key where the provider permits.
8. Default to creating provider drafts. Publishing, scheduling, and destructive replacement need
   separate explicit operator authorization.
9. Treat media paths as untrusted campaign-relative metadata. Before opening one, resolve the
   campaign `source` beneath the trusted plan root, resolve the media path beneath that campaign's
   directory, follow symbolic links, and reject any result outside the campaign directory.
10. Bound every file read, verify ordinary-file status, actual MIME type, size, dimensions,
    animation, provider/account rules, and current attachment limits before upload. A safe suffix
    and valid schema are not proof that a referenced file is safe or supported.

Unlike the spreadsheet-oriented CSV files, `adapter.json` preserves exact draft text without a
formula-neutralizing prefix. Do not render its content as HTML or execute it as a template. Treat
the payload as potentially sensitive campaign data and avoid logging it. Image bytes are not
embedded or copied into the plan export; a media-aware consumer needs a separately trusted source
tree. See [MEDIA.md](MEDIA.md) for the complete resolution and revalidation boundary.

## Compatibility

Additive optional fields may appear within the v2 contract only after the schema permits them.
Removing or renaming fields, changing meaning, or changing identity rules requires a new contract
and schema version. Adapters should reject unknown `schemaVersion` or `contract` values instead of
guessing.

Version 2 replaces version 1 in package 0.6. It adds required `media` arrays to items and drafts;
the arrays are present and empty when a campaign has no media. Consumers written for v1 must load
the v2 schema, accept the new top-level version, and either implement the documented media safety
boundary or refuse items whose `media` array is non-empty. The `contract` string and identity rules
are unchanged. Package 0.5 remains the source for the retired v1 schema and exact fixture.

Provider-specific field mappings deliberately remain outside this repository until an adapter can
be tested against an official API and separately permissioned credentials. The generic contract is
not a claim that one payload can be uploaded directly to every publisher.
