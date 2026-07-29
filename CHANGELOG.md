# Changelog

All notable changes to this project are documented here.

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
