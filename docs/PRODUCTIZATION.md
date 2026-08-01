# Productization record

Last updated: 2026-08-01

## Repository assessment

The repository was repurposed in commit `53a32c0` from an extracted agent-coordination module into
an “AI-powered social media automation” package. At audit start, it contained roughly 430 lines of
workflow/template code, five advertised examples, a 1,443-line unrelated consensus extraction,
placeholder documentation, and contradictory packaging/dependency files.

The apparent original product intent was to generate content through a private Helix Narrative
Engine and publish it through Helix Spirals. That journey was not independently runnable:

- `helix-narrative-engine>=1.0.0` and `helix-spirals>=1.0.0` had no public PyPI releases;
- generation imported `helix_narrative_engine` only at runtime;
- publish/archive steps returned invented URLs without performing external operations;
- analytics always returned zero metrics;
- examples and documentation described API keys, integrations, files, classes, tests, CI, and
  “production ready” behavior that did not exist;
- the top-level `agent_consensus` package imported missing services, exported a missing class, was
  not part of the distribution, and was unrelated to the repurposed repository;
- `requirements.txt` listed a generic web/API/database/queue stack unused by the package, while
  `pyproject.toml` declared different unavailable runtime dependencies;
- no tests, CI workflow, CLI, changelog, or functional API documentation existed.

The worktree was clean on `main` and matched `origin/main` at `1c5c9f6` before changes. All changes
in this productization pass are therefore attributable to this work; no pre-existing dirty or
untracked user work was overwritten.

On the same date, the owner confirmed that the company and product family now use the Samsarix
brand, supplied `contact@samsarix.com` and `support@samsarix.com`, identified Samsarix LLC as the
company, and authorized further productization and publication of commits. A read-only portfolio
check confirmed that related repositories already use full Samsarix distribution/import rebrands,
MPL-2.0, and the same contact pattern. This repository follows that pattern without adding runtime
coupling. The GitHub repository was subsequently renamed to
`Deathcharge/samsarix-creative-spirals`; the old coordinate remains only in preserved history.

## Chosen product definition

**Product:** Samsarix Creative Spirals, a dependency-free, local-first campaign preview/export CLI
and typed Python library.

**Target user:** a solo creator, developer advocate, or small content team with an approved source
draft who needs consistent platform variants and reviewable artifacts, but does not want to grant
account access or deploy a social-management service.

**Problem solved:** safely turn one source draft into bounded X, LinkedIn, Bluesky, Mastodon, and
Discord files with a deterministic identity, explicit quality findings, and a machine-readable
manifest.

**Primary journey:** install locally → create or supply campaign JSON → validate → preview all
platform variants → run a deterministic quality gate → explicitly export an outbox bundle →
review/copy the files into an approved publishing process.

**Independent reason to exist:** Buffer, Typefully, and Postiz center on connected-account
scheduling and publishing. This tool is a small, version-control-friendly preprocessing and review
boundary with no credentials, network calls, hosted state, or account risk. It can complement any
publisher without depending on another Samsarix repository or the flagship application.

**Deliberately out of scope for 0.3:** automatic publishing; social authentication; background
scheduling; analytics; AI generation; media processing; collaborative approvals; account-specific
capabilities; a web UI; database/cloud infrastructure; and private Helix integrations.

## Product and architecture decisions

1. Start from human-approved text. The old “generate” step could not work without an unreleased
   package and encouraged credential/cost expansion.
2. Export local drafts instead of simulating publication. Side effects remain visible and under
   user control.
3. Use strict, versioned JSON. The Python standard library handles it on every supported platform;
   rejecting unknown keys catches mistakes early.
4. Maintain a minimal public API: validated models plus load, build, export, and packaged-schema
   functions.
5. Derive campaign IDs from canonical normalized input. Equal inputs produce equal preview IDs and
   changed inputs produce new bundle paths.
6. Default to no overwrite. Replacement requires `--overwrite`; bundle child paths are generated,
   not accepted from campaign input.
7. Keep zero runtime dependencies. This removes the original install blocker and minimizes supply
   chain, compatibility, operating-cost, and maintenance risk.
8. Use the full Samsarix product/distribution/import identity. The console command is
   `samsarix-campaign` because the separate workflow runner already owns `samsarix-spirals`.
9. Adopt the unmodified MPL-2.0 text. It provides file-level copyleft, notice preservation, and
   contributor patent grants while allowing the package in larger works under other terms.
10. Keep trademark permission separate from source-code permission and record product origin,
    copyright, support, security, and licensing contacts explicitly.

## Bounded current research

- X's current developer documentation specifies 280 weighted characters for standard posts,
  NFC normalization, special Unicode weights, and 23 characters for detected URLs. The formatter
  implements those published rules conservatively: <https://docs.x.com/fundamentals/counting-characters>.
- Discord's message resource specifies up to 2,000 content characters and warns integrations to
  control mentions: <https://docs.discord.com/developers/resources/message>.
- LinkedIn's current Posts API documents text commentary and restricted write permissions. Direct
  API integration would add approval, authorization, and versioning requirements outside this
  release: <https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/posts-api>.
- Buffer emphasizes drafts, multi-channel scheduling, and approval; Typefully emphasizes calendar
  scheduling and its API; Postiz provides a connected-account CLI/service. These support a narrow
  credential-free export wedge rather than another scheduler:
  <https://support.buffer.com/article/656-saving-and-scheduling-draft-posts>,
  <https://support.typefully.com/en/articles/9210135-scheduling-and-calendar>, and
  <https://docs.postiz.com/cli/introduction>.
- The Python Packaging User Guide recommends `[project.scripts]` for console commands and a modern
  `pyproject.toml`: <https://packaging.python.org/en/latest/guides/writing-pyproject-toml/>.
- Mozilla describes MPL-2.0 as a file-level copyleft license; its terms preserve source notices,
  cover distributed modifications to covered files, permit larger works under other terms, include
  contributor patent grants, and do not grant trademark rights:
  <https://www.mozilla.org/en-US/MPL/2.0/>.
- The Open Source Initiative lists MPL-2.0 as an approved license with SPDX identifier `MPL-2.0`:
  <https://opensource.org/license/mpl-2-0>.
- MariaDB's Business Source License guidance states that BSL is not an open-source license and is
  designed around time-delayed conversion plus additional-use terms. That did not fit a small,
  adoption-oriented local library—especially when the inherited custom text named a different
  product and organization: <https://mariadb.com/bsl11/>.

### 0.3 competitive follow-up

- Buffer's bulk upload flow requires a preview/confirmation step and its team plans add draft
  approvals, validating demand for batch preparation and explicit review boundaries:
  <https://support.buffer.com/article/926-how-to-upload-posts-in-bulk-to-buffer> and
  <https://support.buffer.com/article/665-managing-and-approving-draft-posts>.
- Typefully groups drafts, schedules, analytics, and collaboration around connected social sets;
  its API creates, schedules, and publishes with API keys. That reinforces the opportunity for a
  credential-free upstream quality layer rather than a competing account hub:
  <https://support.typefully.com/en/articles/8717684-social-sets-and-accounts> and
  <https://support.typefully.com/en/articles/8718287-typefully-api>.
- Postiz supports broad provider drafts and schedules, while its self-hosted path requires a server,
  PostgreSQL, Redis, Temporal, storage, credentials, and provider network access. Samsarix remains
  deliberately smaller and operationally inert:
  <https://docs.postiz.com/public-api/posts/create> and
  <https://docs.postiz.com/installation/system-requirements>.
- Bluesky's canonical Lexicon limits post text to 300 graphemes and 3,000 UTF-8 bytes:
  <https://github.com/bluesky-social/atproto/blob/main/lexicons/app/bsky/feed/post.json>.
- Mastodon documents a 500-character default and 23-character URL accounting, while each instance
  can advertise another `configuration.statuses.max_characters` value:
  <https://docs.joinmastodon.org/user/posting/> and
  <https://docs.joinmastodon.org/entities/Instance/>.

The resulting wedge is **Git-native, publisher-neutral campaign QA** for release communications,
agency review, and privacy-sensitive drafting. The 0.3 slice adds federated platforms, explicit
instance limits, and a CI-safe quality report without adding credentials, hosted state, or runtime
dependencies.

## Untouched baseline results

Environment: Windows, Python 3.11.9, pip 26.1.1.

| Command | Exit | Actual result before changes |
| --- | ---: | --- |
| `git status --short --branch` | 0 | Clean `main...origin/main`. |
| `python -m pip install --dry-run -e .` | 1 | No distribution found for `helix-narrative-engine>=1.0.0`. |
| `python -m pytest -q` | 1 | No test files; pytest warned that `testpaths` was empty. |
| `python -m compileall -q helix_creative_spirals agent_consensus examples` | 0 | Syntax compilation succeeded. |
| `python examples/01_quick_tweet.py` | 1 | `ModuleNotFoundError: helix_creative_spirals` from the documented checkout command. |
| `python -m flake8 helix_creative_spirals agent_consensus examples` | 1 | Extensive line-length, whitespace, unused import, and f-string failures. |
| `python -m black --check helix_creative_spirals agent_consensus examples` | 1 | Eight files required formatting. |
| `python -m mypy helix_creative_spirals agent_consensus` | 1 | Unsupported Python 3.8 target plus 32 errors, including missing private modules. |
| `python -m build` | 0 | Built artifacts, but warned about deprecated/false Apache license metadata; runtime dependencies were not resolved. |

## Findings and disposition

### P0 — release/core journey blockers

- [x] Remove unavailable private runtime dependencies and generic unused dependency stack.
- [x] Replace fake generation, publishing, archiving, and analytics with an honest local journey.
- [x] Add strict input validation, working CLI entry point, preview, and persistent export.
- [x] Add tests and make documented examples runnable.
- [x] Replace false product identity, production-readiness, CI, license, and integration claims.
- [x] Add CI for format, lint, type, test, build, and installed-wheel smoke checks.

No locally actionable P0 remains.

### P1 — serious quality/reliability/security issues

- [x] Remove the unreachable, unpackaged consensus extraction and its missing-service imports.
- [x] Consolidate package metadata in `pyproject.toml`; remove conflicting `setup.py` metadata.
- [x] Add meaningful CLI exit codes and stdout/stderr separation.
- [x] Bound config size and fields; reject unknown keys, unsafe URLs, credentials, and controls.
- [x] Prevent path traversal through generated bundle names and refuse accidental overwrite.
- [x] Preserve URLs/metadata during platform truncation and surface every modification.
- [x] Add a pinned direct development toolchain and 90% coverage gate.
- [x] Document trust boundaries, privacy, cost, recovery, and limitations.
- [x] Replace the contradictory customized BSL/proprietary files with owner-selected MPL-2.0,
  consistent Samsarix LLC metadata, origin notices, contacts, and trademark guidance.
- [x] Exercise the committed GitHub Actions workflow on GitHub-hosted Linux/Python 3.10 and 3.13;
  both jobs passed in run `30418387807`.

### P2 — valuable post-release work

1. Add bounded multi-campaign plans with portable CSV/calendar export.
2. Add a `diff` command for comparing two deterministic campaign bundles.
3. Add media-reference validation without reading or uploading media.
4. Evaluate optional editor snippets that reference the bundled JSON Schema.
5. Evaluate an optional official `twitter-text` adapter for exact edge-case parity; keep the
   dependency optional and retain conservative zero-dependency behavior.

## Implementation checklist and completed work

- [x] Preserve and audit the initial worktree/history.
- [x] Record real baseline commands and outcomes.
- [x] Define a narrow independent product and out-of-scope boundary.
- [x] Implement immutable config/result models.
- [x] Implement strict normalization and validation.
- [x] Implement X, LinkedIn, Bluesky, Mastodon, and Discord formatting with warnings.
- [x] Implement deterministic, side-effect-free preview.
- [x] Implement safe, explicit outbox persistence and overwrite recovery behavior.
- [x] Implement `--help`, `--version`, `init`, `validate`, `preview`, `check`, `export`, and
  `schema`.
- [x] Add representative unit, integration, command-level, and security regression tests.
- [x] Add current packaging, build metadata, changelog, and CI.
- [x] Replace all user and contributor documentation with verified behavior.
- [x] Rebrand distribution/import/CLI surfaces for Samsarix LLC without a conflicting legacy alias.
- [x] Package a JSON Schema and `py.typed` marker in both wheel and source distribution.
- [x] Replace conflicting license files with MPL-2.0 and add licensing, notice, trademark, security,
  and current contact documentation.
- [x] Add a typed, side-effect-free quality API and distinct CLI exit code for valid campaigns that
  require intervention.
- [x] Add validated per-platform limits without allowing hard service ceilings to be raised; permit
  Mastodon instance-specific limits explicitly.
- [x] Complete final clean-environment install/build/wheel smoke verification.
- [x] Complete adversarial final review and update final disposition.

## Release acceptance criteria

- [x] Product identity, target user, primary journey, and exclusions are explicit.
- [x] Runtime installation has no unavailable or third-party dependencies.
- [x] Validate, preview, export, existing-output failure, and explicit overwrite work end to end.
- [x] Empty/malformed/oversized/unsafe inputs fail with actionable messages.
- [x] Drafts stay within configured platform limits and modifications are visible.
- [x] Quality checks distinguish malformed input, truncation failures, optional warning failures,
  and successful output for CI.
- [x] Build, format, lint, strict type checking, and tests pass locally.
- [x] CI protects the meaningful checks and smoke-tests the installed wheel.
- [x] No credentials, telemetry, production endpoints, or imaginary Helix services are required.
- [x] README examples and commands match implemented scripts.
- [x] License identity, company, contacts, package metadata, and documentation are consistent.
- [x] Hosted CI completes successfully on the declared Python matrix.

## Known risks

- Platform rules can change after release. Current defaults are conservative, warnings are visible,
  and final review in each platform composer remains required.
- X's complete `twitter-text` parser contains edge cases beyond this dependency-free implementation.
  The current algorithm follows documented weights and keeps detected URLs atomic, but does not
  claim conformance certification.
- Bluesky enforcement covers its canonical grapheme and UTF-8 byte ceilings with a conservative
  standard-library cluster iterator. It handles combining marks, modifiers, ZWJ emoji, regional
  pairs, and emoji tags, but does not claim full Unicode grapheme-break conformance.
- Mastodon servers can advertise custom status and URL accounting values. The configuration accepts
  an explicit instance character maximum and uses Mastodon's documented 23-character URL default;
  it does not contact an instance or infer remote-mention accounting.
- The full quality suite has been verified locally on Windows/Python 3.11, with isolated wheel
  smoke checks on Python 3.11 and 3.13. GitHub-hosted Linux quality/build/wheel jobs passed on
  Python 3.10 and 3.13 after the cross-version nesting guard fix.
- `--overwrite` updates draft files then writes the manifest last. A process/filesystem failure
  during explicit overwrite can leave files newer than the old manifest; rerunning the same command
  recovers the bundle.
- The owner selected MPL-2.0, but formal legal advice and ownership-chain review remain prudent,
  especially for any contribution created before Samsarix LLC owned the project. This is not a
  blocker created by conflicting repository terms anymore.

## Final verification results

Final local environment: Windows, Python 3.11.9. The complete quality suite was rerun in a fresh
virtual environment installed from the pinned `requirements-dev.txt`; wheel smoke checks were also
run in isolated Python 3.11 and 3.13 environments after the adversarial fix pass.

| Command | Exit | Actual result |
| --- | ---: | --- |
| `python -m black --check samsarix_creative_spirals tests examples` | 0 | 17 files unchanged. |
| `python -m flake8 samsarix_creative_spirals tests examples` | 0 | No findings. |
| `python -m mypy` | 0 | No issues in 16 source files. |
| `python -m pytest --cov=samsarix_creative_spirals --cov-report=term-missing` | 0 | 90 passed; 95.22% total coverage. |
| `python -m compileall -q samsarix_creative_spirals tests examples` | 0 | All files compiled. |
| `git diff --check` | 0 | No whitespace errors. |
| `python -m build --outdir <isolated-dir>/dist` | 0 | Built warning-free `0.3.0` sdist and universal wheel from an isolated build environment. |
| isolated `python -m pip install --no-deps <wheel>` | 0 | Installed `samsarix-creative-spirals 0.3.0` with zero default dependencies. |
| isolated `samsarix-campaign --version` | 0 | Reported `samsarix-campaign 0.3.0`. |
| isolated schema → validate → check → preview → export | 0 | Loaded the wheel-bundled schema, passed the quality gate, and produced five drafts plus a valid local manifest. |
| isolated `python -m pip check` | 0 | No broken requirements. |
| isolated metadata/API inspection | 0 | Name, version, `MPL-2.0` license expression, package version, and schema resource matched. |
| Python 3.13 isolated wheel smoke | 0 | Installed the wheel and exercised version, schema, quality check, preview, and public import successfully. |
| GitHub Actions `quality (3.10)` | 0 | Hosted Linux format, lint, type, test, build, and installed-wheel checks passed. |
| GitHub Actions `quality (3.13)` | 0 | Hosted Linux format, lint, type, test, build, and installed-wheel checks passed. |

Artifact inspection found only the intended Samsarix package plus distribution metadata in the
wheel. It includes the JSON Schema, `py.typed`, unmodified MPL-2.0 text, and NOTICE; it includes no
tests, legacy Helix package, or orphan consensus package. The sdist contains the package,
documentation, legal/support files, examples, and complete test suite.

The public package index and real platform publishing were not used. Public publication remains an
explicit owner action; platform publishing is deliberately absent from the product and therefore
is not an untested claim.

## External and owner-controlled follow-ups

1. **Public distribution:** if desired, the owner must confirm the PyPI name, create/configure the
   trusted publisher, and publish the locally verified artifacts. No account or package was created
   during this pass.
2. **Optional legal review:** MPL-2.0 and the owner-supplied company/contact identity are now
   internally consistent. Counsel may still confirm the ownership chain, trademarks, and any future
   contributor or alternative commercial-license process; this is prudent governance rather than a
   contradictory-license release blocker.

## Distribution and sustainability model

For validation, distribute as a Git checkout or wheel and install with `pipx`/`pip`. Public PyPI
publication is appropriate after hosted CI is green and the owner configures a trusted publisher.
The core tool has no operating cost and can remain a free local utility. Paid support, warranties,
or separately permissioned publishing/team integrations are plausible sustainability paths; the
local preview/export core should remain useful without them and must never silently send draft
content.

## Release disposition

**0.3 release candidate; all declared technical acceptance gates pass.** The product journey,
package artifacts, tests, hosted CI, branding, licensing, and documentation meet the 0.3 acceptance
criteria, and no locally actionable P0 is known. Public package publication remains a separate
owner-controlled release action.
