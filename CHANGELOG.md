# Changelog

All notable changes to this project are documented here.

## 0.14.0 - 2026-08-02

- Added opt-in `--include-media` plan approvals that bind exact campaign-relative static JPEG/PNG
  bytes, while preserving the existing metadata-only default.
- Added bounded stable reads, no-symlink containment, structural image/type/dimension checks,
  SHA-256 content addressing, duplicate-byte elimination, and explicit per-file, pixel, reference,
  and packet limits with no network or third-party runtime dependency.
- Added self-contained exact-media handoffs with normalized `media-index.json`, deduplicated
  `media/` payloads, approval binding, packet-shape enforcement, and byte-level tamper detection.
- Added immutable media index/binding/asset/collection APIs, a bundled Draft 2020-12 media-package
  schema, CLI schema output, readiness integration, adversarial coverage, and installed-wheel CI
  planning.
- Documented current first-party X, LinkedIn, Bluesky, Mastodon, and Discord constraints plus the
  limits of structural validation, unsigned hashes, local content rights, and provider acceptance.

## 0.13.0 - 2026-08-02

- Added exclusive initialization and offline verification of handoff-bound publication ledgers
  with one canonical record for every generated plan/platform draft.
- Added strict pending, published, failed, and skipped outcome contracts with bounded operator
  labels, timestamps, notes, credential-free HTTP(S) URLs, exact coverage, and chronology checks.
- Added derived `scpub_*` identity, immutable public models/functions, a bundled Draft 2020-12
  schema, CLI init/verify commands, stable counts/findings, and completion exit code `4`.
- Extended readiness with optional invalid/in-progress/complete publication stages and an explicit
  `publication` gate while preserving report shape and behavior when no ledger is supplied.
- Documented current Buffer and Sprout sent-history behavior and the precise boundary between an
  operator assertion and provider-verified proof, with no accounts, URL opens, or runtime dependency.

## 0.12.0 - 2026-08-02

- Added optional source-level `linkTracking` with bounded common query parameters and explicit
  per-platform overrides.
- Applied deterministic UTF-8 percent encoding to the effective baseline or platform-variant link,
  preserving existing query strings and fragments while rejecting parameter-name collisions.
- Included tracking configuration and exact rendered URLs in campaign/plan identity, semantic
  review, approval invalidation, adapters, exports, handoffs, and readiness without changing those
  downstream schemas.
- Added the public immutable `LinkTracking` model, campaign-schema constraints, adversarial and
  end-to-end handoff coverage, an installed-wheel CI journey, and a runnable five-platform example.
- Documented current Google Analytics, Buffer, and Sprout workflow evidence, migration, privacy,
  redirect/shortener limits, and the no-network/no-click-collection boundary.

## 0.11.0 - 2026-08-02

- Added portable content-policy v1 JSON with bounded literal `blockedPhrase` and `requiredPhrase`
  rules, per-platform targeting, casing controls, warning/error severity, and deterministic identity.
- Applied policies to exact final rendered platform content, including platform variants and
  truncation, with stable finding codes and rule IDs in campaign, plan, and readiness results.
- Added optional policy bindings to campaign and plan approval v1; verification, approved handoff,
  and readiness now reject an omitted, newly introduced, or changed policy relative to approval.
- Made policy-bound handoffs self-contained by embedding normalized, checksummed policy source;
  handoff verification and readiness use it automatically and can cross-check an external copy.
- Added public immutable policy types/loaders/evaluator, `policy validate`, `--policy` across all
  relevant CLI gates, a packaged Draft 2020-12 schema, offline readiness display, and a runnable
  example.
- Documented current approval/blocked-word workflow evidence, literal matching limits, additive
  compatibility, policy confidentiality, unsigned identity, and the no-network/no-regex boundary.

## 0.10.0 - 2026-08-02

- Added optional complete `platformVariants` content overrides for X, LinkedIn, Bluesky, Mastodon,
  and Discord, with baseline fallback for platforms that have no override.
- Applied existing normalization, bounds, URL/credential, hashtag, control-character, platform
  limit, truncation, and warning behavior to every variant.
- Included normalized variants in deterministic campaign/plan identity, semantic diffs, approval
  invalidation, adapters, handoffs, readiness, and exports without changing their output schemas.
- Added the public immutable `PlatformContentVariant` model, campaign-schema constraints,
  adversarial tests, installed-wheel CI smoke, a realistic example, and full contract/security
  documentation.
- Kept campaign schema version 1 as an additive change and retained the no-network,
  no-credentials, standard-library-only runtime boundary.

## 0.9.0 - 2026-08-02

- Added consolidated point-in-time plan readiness across quality, future/complete schedule policy,
  source-bound approval, and exact approved handoff verification.
- Added stable readiness stages, issue codes, automation gates, and exit codes through
  `plan status`, including explicit assessment times and optional schedule completeness.
- Added an exclusive, self-contained offline HTML status board with escaped campaign-controlled
  content, copy-ready drafts, restrictive CSP/no-referrer metadata, and no scripts or remote
  resources.
- Added typed readiness models and functions plus a bundled Draft 2020-12 plan-readiness v1 JSON
  Schema available through the public API and `schema --kind readiness`.
- Documented current calendar/approval workflow evidence, exact semantics, CI use, sensitive-report
  handling, compatibility, and the boundary between readiness intent and actual publication.

## 0.8.0 - 2026-08-02

- Added exclusive approved-plan handoff packets containing the embedded approval and exact plan
  manifest, adapter JSON, calendar, and per-platform CSV artifacts.
- Added offline verification of current plan/approval identity, recorded quality policy, producer
  version, generation ordering, canonical handoff metadata, fixed directory shape, exact
  regenerated bytes, declared sizes/checksums, regular-file types, and read stability.
- Added typed handoff models/functions, `plan handoff create/verify` CLI commands, stable invalid
  exit code `4`, and a dedicated bundled handoff v1 JSON Schema.
- Refactored plan artifact rendering through shared byte-level helpers while retaining the exact
  adapter v2 export fixture.
- Documented downstream-adapter use, immutable packet operation, retention, current approval-to-
  queue workflow evidence, and the explicit distinction between unsigned hashes and authenticated
  artifact attestations.

## 0.7.0 - 2026-08-02

- Added deterministic whole-plan semantic diffs covering plan metadata, required channels,
  ordered membership, schedules, source references, and nested campaign/draft changes.
- Added aggregate-quality-gated plan approval creation and verification bound to the normalized
  plan plus every referenced campaign.
- Added typed plan-review models/functions, nested CLI commands, and a dedicated bundled
  plan-approval v1 JSON Schema while preserving campaign approval v1 compatibility.
- Aligned campaign and plan approval runtime validation with their schemas for whitespace-only
  reviewers and explicit null notes, with generated-record Draft 2020-12 conformance tests.
- Documented positional reorder semantics, CI exit behavior, stale-state invalidation, current
  competitive workflow evidence, and the non-cryptographic trust boundary.

## 0.6.0 - 2026-08-02

- Added portable, platform-targeted JPEG/PNG references with required alt text, strict path rules,
  bounded collections, and a conservative four-images-per-platform envelope.
- Kept media paths as metadata only: core does not resolve, read, inspect, copy, or upload files.
- Included media in deterministic campaign/plan identity, semantic diffs, approval invalidation,
  campaign manifests, plan manifests, and exact per-platform draft output.
- Advanced `samsarix.plan-drafts` to schema version 2 with normalized item media and applicable
  draft attachments, a v2 conformance fixture, and explicit adapter migration/safety guidance.
- Added platform-evidence documentation and adversarial coverage for path traversal, Windows
  reserved names, duplicate paths, invalid targets, alt text, and per-platform limits.

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
