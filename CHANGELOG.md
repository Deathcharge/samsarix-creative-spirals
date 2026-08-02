# Changelog

All notable changes to this project are documented here.

## 0.5.0 - 2026-08-02

- Added deterministic semantic campaign diffs covering normalized source fields and generated
  platform drafts, with JSON output and opt-in exit code `4` for automation.
- Added quality-gated, source-hash-bound local approval records plus current-source verification.
- Added an approval JSON Schema and typed diff/approval models and functions to the public API.
- Added deterministic `samsarix.plan-drafts` adapter JSON, a bundled v1 schema, and explicit
  consumer/idempotency/authorization guidance for separately permissioned importers.
- Made the iCalendar product identifier version-neutral so unchanged calendar semantics do not
  carry a stale package version.
- Kept approval identity explicitly non-cryptographic and preserved the offline, zero-runtime-
  dependency boundary.

## 0.4.0 - 2026-08-01

- Require setuptools 83 or newer for isolated builds and pin development to 83.0.0, closing
  GHSA-h35f-9h28-mq5c in the source-distribution toolchain.
- Added bounded campaign plans with confined relative campaign references and explicit-offset
  intended publication times normalized to UTC.
- Added aggregate plan validation, preview, and quality checks for missing channels, duplicate or
  out-of-order times, and every underlying campaign finding.
- Added safe plan export with a manifest, one publisher-neutral CSV per platform, and an RFC 5545
  calendar containing scheduled events and unscheduled tasks.
- Hardened CSV export against spreadsheet formulas, removed stale platform files during explicit
  overwrite, and normalized RFC 3339 fractional seconds consistently across supported runtimes.
- Added the packaged plan JSON Schema and typed plan models/functions to the public Python API.
- Fixed output-root symbolic-link detection by preserving the selected path before inspection.

## 0.3.0 - 2026-08-01

- Added bounded Bluesky and Mastodon drafts alongside X, LinkedIn, and Discord.
- Added conservative Bluesky grapheme and UTF-8 byte enforcement plus Mastodon's documented
  23-character URL accounting.
- Added validated `platformLimits` overrides for stricter policies and instance-specific Mastodon
  limits without network discovery.
- Added typed `QualityIssue` and `CampaignCheck` results plus the pure `check_campaign()` API.
- Added `samsarix-campaign check`, with exit code `3` for valid campaigns that fail the quality gate
  and optional `--warnings-as-errors` behavior.
- Rejected duplicate JSON fields, normalized duplicate platform-limit keys, and excessive JSON
  nesting instead of allowing ambiguous or interpreter-dependent input.
- Expanded the product roadmap around Git-native release communications, review, and portable
  publisher-neutral artifacts.

## 0.2.0 - 2026-07-28

- Rebranded the product, distribution, import namespace, and metadata for Samsarix LLC.
- Renamed the collision-free console command to `samsarix-campaign` and campaign IDs to `scs_*`.
- Adopted MPL-2.0 with explicit origin, support, security, licensing, and trademark documentation.
- Added a packaged JSON Schema, typed `load_campaign_schema()` API, and `schema` CLI command.
- Added the `py.typed` marker so type checkers recognize the installed package as typed.
- Kept the package dependency-free and standalone from other Samsarix repositories.

## 0.1.0 - 2026-07-28

- Reframed the unpublished prototype as a local-first campaign preview and export tool.
- Added strict JSON configuration validation and bounded input handling.
- Added platform-aware X, LinkedIn, and Discord formatting with visible truncation warnings.
- Added deterministic campaign IDs and safe, reviewable outbox bundles.
- Added the legacy `helix-spirals` CLI and a minimal typed Python API.
- Removed simulated publishing, analytics, archiving, private Helix dependencies, and orphaned
  consensus code.
- Added unit, command-level, packaging, lint, type, coverage, and CI checks.
