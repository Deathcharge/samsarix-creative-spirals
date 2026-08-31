# Productization record

Last updated: 2026-08-02

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

**Product:** Samsarix Creative Spirals, a dependency-free, local-first campaign and launch-plan
preview/export CLI and typed Python library.

**Target user:** a solo creator, developer advocate, or small content team with an approved source
draft who needs consistent platform variants and reviewable artifacts, but does not want to grant
account access or deploy a social-management service.

**Problem solved:** safely turn approved source drafts into bounded X, LinkedIn, Bluesky, Mastodon,
and Discord artifacts, then review a complete sequence with deterministic identities, explicit
quality findings, portable CSV/calendar handoff, and machine-readable manifests.

**Primary journey:** install locally → create standalone campaign JSON → optionally compose a plan
→ validate and preview every platform variant → run deterministic quality gates → compare campaign
or complete-plan semantic changes → record/verify source-bound local approval → create and verify
an exact approved handoff packet → hand it to an approved publishing process → reconcile each
operator-recorded platform outcome against that exact handoff.

**Independent reason to exist:** Buffer, Typefully, and Postiz center on connected-account
scheduling and publishing. This tool is a small, version-control-friendly preprocessing and review
boundary with no credentials, network calls, hosted state, or account risk. It can complement any
publisher without depending on another Samsarix repository or the flagship application.

**Deliberately out of scope:** automatic publishing; social authentication; background scheduling;
analytics; AI generation; media transformation or upload; hosted collaborative approvals; cryptographic signer
identity; account-specific capabilities; a web UI; database/cloud infrastructure; and private
Helix integrations. Versions 0.4–0.17 add bounded plans, canonical CSV-to-plan import, interchange, campaign and whole-plan
semantic diffs, source-bound local review metadata, portable image handoff, exact approved packet
verification, offline launch readiness, platform-native content, policy-as-code, and deterministic
link attribution, and optional approval-bound exact image packets without adding a scheduler,
account connection, analytics collector, or network publisher.

## Product and architecture decisions

1. Start from human-approved text. The old “generate” step could not work without an unreleased
   package and encouraged credential/cost expansion.
2. Export local drafts instead of simulating publication. Side effects remain visible and under
   user control.
3. Use strict, versioned JSON. The Python standard library handles it on every supported platform;
   rejecting unknown keys catches mistakes early.
4. Maintain a focused public API: validated campaign/plan models plus load, build, check, export,
   calendar, and packaged-schema functions.
5. Derive campaign and plan IDs from canonical normalized input. Equal inputs produce equal IDs and
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

### 0.8 approved-handoff follow-up

- Buffer documents approval as a transition toward its publishing queue or schedule and requires
  posting access to make that transition. This supports an explicit artifact boundary between
  review and a separately authorized publishing system:
  <https://support.buffer.com/article/665-managing-and-approving-draft-posts> and
  <https://support.buffer.com/article/656-saving-and-scheduling-draft-posts>.
- GitHub defines artifact attestations as cryptographically signed claims and warns verifiers to
  validate signatures, timestamps, and signer identity. A plain digest therefore must not be
  marketed as authenticated provenance:
  <https://docs.github.com/en/actions/concepts/security/artifact-attestations> and
  <https://docs.github.com/en/rest/repos/attestations>.

The resulting 0.8 slice is an exclusive offline-verifiable handoff packet: current plan source,
embedded approval, exact rendered files, sizes/checksums, and producer version are bound without
adding credentials, a scheduler, or a false signing claim.

### 0.9 launch-readiness follow-up

- Sprout Social's Publishing Calendar emphasizes one place to see planned messages, filters,
  notes, and sharable review, while its approval workflow exposes `Needs Approval` and requires
  rescheduling when approval misses the intended time:
  <https://support.sproutsocial.com/hc/en-us/articles/360000121343-How-do-I-use-the-Publishing-Calendar>
  and <https://support.sproutsocial.com/hc/en-us/articles/205974715-Message-Approval-Workflows>.
- Buffer exposes an `Awaiting Approval` list and its July 13, 2026 update explicitly addresses the
  friction of finding draft/pending-approval work from the calendar:
  <https://support.buffer.com/article/665-managing-and-approving-draft-posts> and
  <https://buffer.com/changelog/access-your-drafts-from-the-calendar>.

The resulting 0.9 slice is a point-in-time, offline readiness report: current quality, future or
complete schedule policy, approval, and handoff evidence become one stable stage plus an optional
self-contained HTML board. It adds no hosted calendar, account, notification, publisher action, or
  claim that intent equals publication.

### 0.13 publication-reconciliation follow-up

- Buffer retains a Sent history with authors, times, and metrics, but its notification publishing
  troubleshooting makes clear that an item can reach Sent before the operator completes native
  publication:
  <https://support.buffer.com/article/517-understanding-sent-post-metrics-within-buffer-publish>
  and <https://support.buffer.com/article/658-using-notification-publishing>.
- Sprout Social exposes Scheduled, Queued, and Sent calendar states and can ingest native or
  third-party published messages, while externally created activity may lack author metadata:
  <https://support.sproutsocial.com/hc/en-us/articles/360000121343-How-do-I-use-the-Publishing-Calendar>
  and <https://support.sproutsocial.com/hc/en-us/articles/38373940164877-Troubleshooting-Sprout-Social-Publishing-Calendar-Issues>.

The resulting slice is a handoff-bound local publication ledger. It closes the prior lifecycle gap
without pretending that operator-entered status or a URL is network-verified evidence. Exact
draft coverage, chronology, and state combinations are deterministic; provider acceptance and
continued remote visibility remain outside the product boundary.

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

1. [x] Add a semantic `diff` command for normalized source and deterministic campaign bundles.
2. [x] Add explicit source-bound local approval metadata and verification without claiming signer
   identity.
3. [x] Publish a versioned deterministic adapter contract, schema, and exact export fixture for
   separately permissioned draft importers.
4. [x] Add media-reference validation without reading or uploading media.
5. [x] Add whole-plan semantic review and quality-gated approval tied to schedule, order, required
   channels, source references, and every campaign.
6. [x] Add an exclusive approved handoff packet that binds current source, approval metadata, and
   exact regenerated artifacts without claiming authenticated provenance.
7. [x] Add consolidated point-in-time launch readiness and an offline HTML review board.
8. [x] Add exact handoff-bound publication reconciliation without provider credentials or proof
   claims.
9. Evaluate optional editor snippets that reference the bundled JSON Schema.
10. Evaluate an optional official `twitter-text` adapter for exact edge-case parity; keep the
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
- [x] Add deterministic semantic diffs for normalized source fields and generated drafts.
- [x] Add quality-gated approval metadata tied to the full campaign source hash.
- [x] Document that local approval labels are neither authenticated nor cryptographically signed.
- [x] Add deterministic exact-text adapter JSON, bundled schema, and consumer safety guidance.
- [x] Add portable, platform-targeted media metadata; include it in identity, review, manifests,
  and adapter v2 without reading or uploading referenced files.
- [x] Add complete-plan diffs and plan approvals without changing campaign approval v1 or adding
  hosted collaboration state.
- [x] Add offline-verifiable approved-plan handoff packets without credentials, signing claims, or
  automatic publishing.
- [x] Add time-aware launch-readiness stages, CI gates, JSON Schema, and an escaped offline HTML
  board without hosted workflow state.
- [x] Add strict operator publication outcomes bound to current plan, handoff, exact draft matrix,
  and chronology, with typed APIs, schema, CLI, readiness gate, and no URL access.

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
- Approval and handoff hashes are unsigned. A writer who controls all source/evidence files can
  replace them consistently; authenticated provenance requires protected external controls or a
  separately reviewed signing/attestation layer.
- Publication labels, status, notes, and URLs are also unsigned assertions. Verification proves
  only internal binding and chronology under the trusted local verifier; it cannot establish
  provider acceptance, authorship, visibility, unchanged content, or continued availability.

## Final verification results

Final local environment: Windows, Python 3.11.9. The complete quality suite was rerun in a fresh
virtual environment installed from the pinned `requirements-dev.txt`; wheel smoke checks were also
run in isolated Python 3.11 and 3.13 environments after the adversarial fix pass.

| Command | Exit | Actual result |
| --- | ---: | --- |
| `python -m black --check samsarix_creative_spirals tests examples` | 0 | 17 files unchanged. |
| `python -m flake8 samsarix_creative_spirals tests examples` | 0 | No findings. |
| `python -m mypy` | 0 | No issues in 16 source files. |
| `python -m pytest --cov=samsarix_creative_spirals --cov-report=term-missing` | 0 | 91 passed; 95.22% total coverage. |
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

## 0.4 campaign-plan release evidence

The 0.4 slice composes standalone campaign files into a bounded local launch sequence. A plan may
contain 1–100 items, declares optional required channels, and records optional RFC 3339 intended
times with explicit offsets. Paths remain relative to and confined beneath the plan directory;
canonical identity covers both plan metadata and every normalized referenced campaign.

The quality gate aggregates campaign truncation/warnings, fails missing required channels, and
reports duplicate or out-of-order times. Export writes one neutral UTF-8 CSV per used platform, a
manifest, and an RFC 5545 calendar. Scheduled entries are transparent events and unscheduled
entries are tasks, so the artifact records intent without claiming to schedule or publish.

Current local verification on Windows/Python 3.11:

| Command | Exit | Actual result |
| --- | ---: | --- |
| `python -m black --check samsarix_creative_spirals tests examples` | 0 | 19 files unchanged. |
| `python -m flake8 samsarix_creative_spirals tests examples` | 0 | No findings. |
| `python -m mypy` | 0 | No issues in 18 source files. |
| `python -m pytest --cov=samsarix_creative_spirals --cov-report=term-missing` | 0 | 134 passed; 93.75% total coverage. |
| Draft 2020-12 schema validation | 0 | The plan schema and included two-campaign example passed. |
| `python -m build --outdir <isolated-dir>/dist` | 0 | Built the `0.4.0` sdist and universal wheel with the patched setuptools floor. |
| Python 3.11 installed-wheel plan journey | 0 | Version, plan schema, validate, check, preview, export, metadata, artifacts, and `pip check` passed. |
| Python 3.13 installed-wheel plan journey | 0 | Version, plan schema, check, export, public API, and `pip check` passed. |
| GitHub Actions Python 3.10/3.13 | 0 | Hosted Linux quality, build, and installed-wheel plan journeys passed on both versions. |

Known 0.4 boundaries:

- CSV columns are stable Samsarix interchange fields, not a promise of direct import into every
  publisher. Buffer, for example, requires channel-specific templates and interprets posting times
  in configured channel context.
- CSV name, content, and warning fields are neutralized when they begin with a spreadsheet formula
  marker; explicit overwrite removes obsolete generated platform CSVs before replacing the
  manifest.
- iCalendar export follows RFC 5545 CRLF, escaping, required component fields, UTC times, and
  UTF-8-safe 75-octet folding. Importer behavior still varies, so the included file is an
  interchange artifact rather than a delivery guarantee.
- Intended times are metadata. There is no timer, daemon, retry loop, credential, or delivery side
  effect in this package.

**0.4 release candidate; all declared technical gates pass.** Initial automated review completed;
all nine comments were addressed and the follow-up status passed (the service reported its detailed
re-review was rate limited). Public package publication remains a separate owner-controlled action.

## 0.5 semantic-review release evidence

The first 0.5 slice closes the Git-review loop. `diff` compares normalized campaign fields and
every generated platform draft in stable order. Its JSON result includes before/after full hashes,
IDs, field values, generated drafts, and changed draft properties. Formatting-only input changes
that normalize away do not produce review noise; `--exit-code` opts automation into exit `4` when
real changes exist.

`approval create` records the exact campaign ID, full source SHA-256, UTC review time, reviewer
label, quality policy, and optional note only after that policy passes. `approval verify` compares
current source and re-runs the recorded policy. Existing records are not overwritten. The approval
schema and every user-facing document state that the label is not authenticated and the file is
not a signature.

Plan export also writes deterministic `samsarix.plan-drafts` adapter JSON with full plan/campaign
identity and exact platform drafts. A bundled schema and `docs/ADAPTERS.md` define compatibility,
safe path resolution, idempotency input, provider revalidation, draft-first behavior, and the
separate authorization boundary. A committed v1 plan-export fixture is regenerated byte-for-byte
in the test suite.

Current local verification on Windows/Python 3.11:

| Command | Exit | Actual result |
| --- | ---: | --- |
| `python -m black --check samsarix_creative_spirals tests examples` | 0 | 21 files unchanged. |
| `python -m flake8 samsarix_creative_spirals tests examples` | 0 | No findings. |
| `python -m mypy` | 0 | No issues in 20 source files. |
| `python -m pytest --cov=samsarix_creative_spirals --cov-report=term-missing` | 0 | 155 passed; 94.29% total coverage. |
| Draft 2020-12 schema validation | 0 | Campaign, plan, approval, and adapter schemas plus representative payloads passed. |
| `python -m build --outdir <isolated-dir>/dist` | 0 | Built the `0.5.0` sdist and universal wheel with all four schemas and legal files. |
| Python 3.11 installed-wheel review journey | 0 | Version, schemas, diff, approval create/verify, plan export, adapter artifact, and public API passed outside the repository. |
| GitHub Actions Python 3.10/3.13 | 0 | Hosted Linux quality, build, and installed-wheel journeys passed on both versions for implementation head `9b42e2b`. |

Known 0.5 boundaries:

- Approval records provide tamper-evident source matching only when the record itself is protected
  by the surrounding repository workflow. They provide no signer authentication, authorization,
  non-repudiation, or defense against a writer replacing both files.
- Semantic JSON diff includes complete campaign and generated-draft content. Treat its output as
  sensitive wherever the source is sensitive; the command neither logs nor transmits it itself.
- The first hosted run exposed Git line-ending normalization in the exact RFC 5545 fixture; the
  fixture is now explicitly binary in `.gitattributes`, preserving required CRLF bytes on Linux and
  Windows. The repeated hosted matrix passed.
- The exact wheel completed an internal review/export scenario without a runtime failure after that
  fixture fix. External-user adoption signals remain unknown; no live provider credential was used
  and no generic artifact is represented as a direct provider import contract.

**0.5 release candidate; declared local, package, fixture, and hosted-CI gates pass.** The automated
review status passed but reported a service rate limit and posted no detailed comments; the local
adversarial pass found and fixed the stale calendar product version. A real external-user pilot and
PyPI publication remain owner-controlled follow-ups rather than claims made from tests.

## 0.6 portable-media release evidence

Implementation and review fixes converge at exact commit
`b5ecd0aa39753c674bca005a4f88223070bd130c`. The release adds metadata-only JPEG/PNG references,
platform applicability, alt text, identity/review propagation, and adapter schema v2. Core never
resolves or opens a referenced file.

Current local verification on Windows/Python 3.11:

| Command | Exit | Actual result |
| --- | ---: | --- |
| `python -m black --check samsarix_creative_spirals tests examples` | 0 | 21 files unchanged. |
| `python -m flake8 samsarix_creative_spirals tests examples` | 0 | No findings. |
| `python -m mypy samsarix_creative_spirals tests` | 0 | No issues in 20 source files. |
| `python -m pytest --cov=samsarix_creative_spirals --cov-report=term-missing -q` | 0 | 183 passed; 94.38% total coverage. |
| `python -m compileall -q samsarix_creative_spirals` | 0 | All package modules compiled. |
| Draft 2020-12 validation | 0 | All four bundled schemas plus campaign, plan, approval, adapter v2, media path, and four-applicable-image cases passed. |
| `python -m build --outdir <isolated-dir>/dist` | 0 | Built the 0.6.0 sdist and universal wheel from the sdist. |
| Installed-wheel media journey | 0 | Version/schema, platform selection, missing-file non-dereference, and manifest export passed outside the checkout. |
| `git diff --check` | 0 | No whitespace errors. |

Exact locally built artifact digests:

- `samsarix_creative_spirals-0.6.0-py3-none-any.whl` — SHA-256
  `8953dff532323837a6ddbb6a3d8fc963b947ed28f432fb0976507add93e1f541`
- `samsarix_creative_spirals-0.6.0.tar.gz` — SHA-256
  `f9dabd7c7f30cbaf6cf7d6a316e8f0960c5eca8027f37fab7a2bf3eee2e99fde`

GitHub Actions run
[`30729137546`](https://github.com/Deathcharge/samsarix-creative-spirals/actions/runs/30729137546)
passed the complete Linux Python 3.10/3.13 matrix for the exact implementation/review head. That
matrix installs development dependencies, formats, lints, type-checks, tests with coverage, builds
the distributions, reinstalls the wheel, and exercises the CLI including the media-bearing example.

The full automated base review posted nine comments. Eight produced code or documentation fixes;
the request to raise adapter draft media from four to twenty was intentionally not applied because
runtime validation rejects more than four applicable images for a platform. Instead, the campaign
schema now enforces that same applicability limit, while the adapter retains the safer exact
`maxItems: 4` invariant. The final incremental automated review was rate limited; it did not post
additional findings.

Compatibility and rollback:

- Campaign and plan authoring remain schema version 1. `media` is optional, and existing files
  retain their prior deterministic identity and output text.
- Public immutable models gain defaulted media fields and the package adds `MediaReference`.
- `samsarix.plan-drafts` advances from schema version 1 to 2 because item and draft `media` arrays
  are required, including explicit empty arrays. V1 consumers must migrate or reject v2.
- No runtime dependency, credential, network call, media read, upload, scheduler, or publisher was
  added.
- Before publication, rollback is `git revert` of the PR merge. Consumers can pin commit
  `8343c480b42f9361acfe191e7ebe0c589872bea0` to retain package 0.5 and adapter v1. After an owner
  publication, normal version pinning and a corrective release are required; published artifacts
  should not be silently replaced.

Known limits remain explicit: no real provider credential was used, media bytes are not inspected,
an external adapter must implement the race-safe containment and provider checks in `docs/MEDIA.md`,
and external-user adoption evidence is still unavailable. PyPI publication remains an
owner-controlled action.

## 0.7 whole-plan-review release evidence

Implementation and review fixes converge at exact commit
`37b3898d5de078f389b7b4d1d77d4d4e053a9316`. The release adds deterministic review of complete
launch state and quality-gated plan approvals bound to metadata, required platforms, ordered
membership, intended times, source references, media metadata, and every normalized referenced
campaign. It does not add an account, hosted workflow, scheduler, publisher, or authenticated
identity claim.

Current local verification on Windows/Python 3.11:

| Command | Exit | Actual result |
| --- | ---: | --- |
| `python -m black --check samsarix_creative_spirals tests examples` | 0 | 23 files unchanged. |
| `python -m flake8 samsarix_creative_spirals tests examples` | 0 | No findings. |
| `python -m mypy samsarix_creative_spirals tests` | 0 | No issues in 22 source files. |
| `python -m pytest --cov=samsarix_creative_spirals --cov-report=term-missing -q` | 0 | 199 passed; 94.66% total coverage. |
| `python -m compileall -q samsarix_creative_spirals` | 0 | All package modules compiled. |
| Draft 2020-12 validation | 0 | All five bundled schemas and representative campaign, plan, campaign-approval, plan-approval, and adapter payloads passed. |
| `python -m build --outdir <isolated-dir>/dist` | 0 | Built the 0.7.0 sdist and universal wheel from the exact reviewed commit's sdist. |
| Installed-wheel plan-review journey | 0 | Version, schema resource, self-diff, approval create/verify, plan export, public API, and `pip check` passed outside the checkout. |
| `git diff --check` | 0 | No whitespace errors. |

Exact locally built artifact digests from the clean detached implementation/review head:

- `samsarix_creative_spirals-0.7.0-py3-none-any.whl` — SHA-256
  `cc4a268b468d6a3bd037015a51160b275db4c32e1ce65323d395cc60b91aaa36`
- `samsarix_creative_spirals-0.7.0.tar.gz` — SHA-256
  `80aa1e445478b480b607c2952c4708f018f77019e70c8b7c41cb2e00932330bb`

GitHub Actions pull-request run
[`30730784381`](https://github.com/Deathcharge/samsarix-creative-spirals/actions/runs/30730784381)
passed the complete Linux Python 3.10/3.13 matrix on that exact head. The matrix installs the
pinned development tools, formats, lints, type-checks, runs tests with coverage, builds from the
sdist, reinstalls the wheel, and exercises both existing journeys and the new plan-approval schema,
self-diff, approval creation, and verification commands.

The automated base review posted two actionable comments. Both were validated and fixed: campaign
and plan approval loaders now reject explicit null notes to match their schemas; their schemas
reject whitespace-only reviewer labels; generated approval records pass Draft 2020-12 validation
and runtime round-trip tests; and strict quality failures assert actionable item detail. Both review
threads are resolved. The incremental follow-up review was service-rate-limited after the fixes;
hosted CI and the complete local checks passed on the resulting head.

Compatibility and rollback:

- Campaign and plan authoring remain schema version 1; adapter schema version 2 is unchanged.
- Campaign approval remains schema version 1. Runtime now rejects explicit `note: null` and its
  schema rejects whitespace-only `approvedBy`; these values were never emitted by the package and
  were already invalid under the other half of the documented contract.
- Plan approval is a new, distinct schema version 1 rather than a breaking union in campaign
  approval v1. The public API only gains typed names.
- `jsonschema` and its type stubs are pinned development/test dependencies only. Runtime remains
  standard-library-only with no network, credential, scheduler, database, or publisher behavior.
- Before publication, rollback is `git revert` of the PR merge. Consumers can pin commit
  `1df82d6814ee4cb01a090915deda64d7933c079f` to retain package 0.6 behavior. After an owner
  publication, normal version pinning and a corrective release are required; published artifacts
  should not be silently replaced.

Known limits remain explicit: approvals are source-bound metadata rather than digital signatures;
Git or another external control must authenticate reviewers; position-based plan diff represents
reorders as modifications at affected positions; no provider credential or real publication was
used; and external-user adoption evidence is still unavailable. PyPI publication remains an
owner-controlled action.

## 0.8 approved-handoff release evidence

Implementation and review fixes converge at exact commit
`2bf35aa079bd983873cdfd1a5db7c904f7499b81`. The release adds exclusive approved-plan handoff
packets that embed the approval and exact rendered plan artifacts, then verify current source,
recorded quality policy, generation ordering, producer version, metadata identity, fixed directory
shape, sizes, SHA-256 values, exact regenerated bytes, regular-file types, and stable reads. It
does not add signing, authenticated provenance, credentials, scheduling, or publishing.

Current local verification on Windows/Python 3.11:

| Command | Exit | Actual result |
| --- | ---: | --- |
| `python -m black --check samsarix_creative_spirals tests examples` | 0 | 26 files unchanged. |
| `python -m flake8 samsarix_creative_spirals tests examples` | 0 | No findings. |
| `python -m mypy` | 0 | No issues in 25 source files. |
| `python -m pytest --cov=samsarix_creative_spirals --cov-report=term-missing -q` | 0 | 224 passed; 94.86% total coverage and 96% handoff-module coverage. |
| `python -m compileall -q samsarix_creative_spirals` | 0 | All package modules compiled. |
| Draft 2020-12 validation | 0 | All six bundled schemas, handoff metaschema validity, generated handoff payload, and runtime round trip passed. |
| `python -m build --outdir <clean-detached-worktree>/dist` | 0 | Built the 0.8.0 sdist and universal wheel from the exact reviewed commit's sdist. |
| Python 3.11 installed-wheel handoff journey | 0 | Version/metadata, public schema, `pip check`, plan approval create/verify, handoff create/verify, and ten-file packet inspection passed outside the checkout. |
| `git diff --check` | 0 | No whitespace errors. |

Exact locally built artifact digests from the clean detached implementation/review head:

- `samsarix_creative_spirals-0.8.0-py3-none-any.whl` — SHA-256
  `3b0391e2036790385f53dd1092211fda003014e4de0a1032d4f6bae1107a13bb`
- `samsarix_creative_spirals-0.8.0.tar.gz` — SHA-256
  `da762fc439d05b4d1f1b7b9014c2c4ee19a939f9db281a6d4336a52b909878de`

GitHub Actions pull-request run
[`30732657643`](https://github.com/Deathcharge/samsarix-creative-spirals/actions/runs/30732657643)
passed the complete Linux Python 3.10/3.13 matrix on that exact head. The matrix installs pinned
development tools, formats, lints, type-checks, runs tests with coverage, builds and reinstalls the
wheel, and exercises schema output plus approval-to-handoff creation and verification.

The automated base review posted ten actionable comments. All were validated and fixed: package
version metadata now reads the sole `_version.py` literal; dense parser and verifier paths are
decomposed into focused helpers; artifact bounds derive from path constants; malformed descriptor
tests run independently; size mismatches, invalid-result state, literal regex matching, and
handoff-schema metaschema validity have direct assertions; and an unused fixture was removed. All
threads are resolved. The incremental follow-up review was service-rate-limited after the fixes;
the complete hosted matrix and local gates passed on the resulting head.

Compatibility and rollback:

- Campaign and plan authoring, campaign approval, and plan approval remain schema version 1;
  adapter schema version 2 is unchanged. Handoff schema version 1 is a new additive contract.
- Public API and CLI surfaces only gain typed names and nested commands. Existing plan export bytes
  remain covered by and pass the exact adapter v2 fixture.
- Packaging now reads version dynamically from the sole `_version.py` literal; built distribution
  metadata and runtime `__version__` both report 0.8.0.
- Runtime remains standard-library-only with no network, credential, signing, scheduler, database,
  or publisher behavior.
- Before publication, rollback is `git revert` of the PR merge. Consumers can pin commit
  `ba174ef1af74276da49afe626f703cd9b40f1efa` to retain package 0.7 behavior. After an owner
  publication, normal version pinning and a corrective release are required; published artifacts
  should not be silently replaced.

Known limits remain explicit: handoff and approval hashes are unsigned; anyone controlling all
source/evidence files can replace them consistently; old packets intentionally require the
producing package version for byte-exact verification; verification is point-in-time and should
immediately precede use of the same directory; media remains metadata only; no provider credential
or real publication was used; and external-user adoption evidence is still unavailable. PyPI
publication remains an owner-controlled action.

## 0.9 launch-readiness release evidence

Implementation and review fixes converge at exact commit
`33647ba87cd5e50bb8de7e333963dddd5f3efe06`. The release adds point-in-time quality, schedule,
approval, and handoff stages; explicit CI gates; readiness v1 JSON; and an exclusive offline HTML
board. Evidence documentation is a subsequent docs-only commit, so the artifact hashes below
identify the exact reviewed code tree rather than a self-referential source archive.

| Verification | Exit | Result |
| --- | ---: | --- |
| `python -m black --check samsarix_creative_spirals tests examples` | 0 | Formatting clean. |
| `python -m flake8 samsarix_creative_spirals tests examples` | 0 | Lint clean. |
| `python -m mypy` | 0 | Strict typing clean across 27 source files. |
| `python -m pytest --cov=samsarix_creative_spirals --cov-report=term-missing` | 0 | 235 passed; 95.18% total coverage and 99% readiness-module coverage. |
| `python -m compileall -q samsarix_creative_spirals tests examples` | 0 | Compilation clean. |
| Draft 2020-12 validation | 0 | Readiness metaschema, ready-for-approval, approved, handoff-ready, and synchronized embedded approval contracts passed. |
| `python -m build --outdir <clean-detached-worktree>/dist <clean-detached-worktree>` | 0 | Built the 0.9.0 sdist and universal wheel from exact commit `33647ba`. |
| Python 3.11 installed-wheel journey | 0 | Package/version/schema and `pip check` passed outside the checkout; approval → handoff → `handoff-ready` JSON plus 6,569-byte script-free HTML passed. |
| Hosted GitHub Actions | 0 | [Run 30734396322](https://github.com/Deathcharge/samsarix-creative-spirals/actions/runs/30734396322) passed full Python 3.10 and 3.13 matrices, builds, and installed-wheel status/HTML smoke. |
| Dependabot | 0 | GitHub reported zero open alerts at review head. |

Clean-tree artifact digests from exact commit `33647ba`:

- `samsarix_creative_spirals-0.9.0-py3-none-any.whl` — SHA-256
  `b9aef0ede71ea6a7d90b92dc16ab955383bbf53917d30a88657f1a8a6299c5ac`.
- `samsarix_creative_spirals-0.9.0.tar.gz` — SHA-256
  `d7bbb9dd7ca4e27c580ab89b1747bf3e3d4ee69f92e739da6690b10504ad9dbd`.

[PR #11](https://github.com/Deathcharge/samsarix-creative-spirals/pull/11) received ten
CodeRabbit comments. All were dispositioned: deterministic examples, schema coverage and
portability, concrete test types, approval-only CLI coverage, bounded issue-code normalization,
orchestrator decomposition, and this evidence record were implemented. The suggested external
approval `$ref` was not used because readiness v1 must validate offline as a standalone document;
instead its embedded approval structure is byte-for-structure synchronized with plan-approval v1
by a direct regression test. All original threads are resolved; the incremental re-review was
rate-limited after the fixes, while the complete local and hosted gates passed on the resulting
code head.

Compatibility is additive for 0.9.x: existing campaign, plan, approval, handoff, manifest, and
adapter contracts do not change. New public names, `plan status`, schema kind `readiness`, and
readiness schema v1 join the pre-1.0 compatibility surface. HTML is a human artifact rather than a
machine compatibility contract. Roll back by reverting the PR merge or pinning pre-0.9 main commit
`8a628e8fdc768196cca7b32845379554389edd43`; existing 0.8 approval and handoff evidence remains
valid under its documented producer-version rules, while consumers should stop requiring or
exchanging readiness v1 artifacts.

## 0.10 platform-native variants release evidence

### Evidence and product decision

The 0.9 formatter accepted one baseline title/body/link/hashtag set and applied only structural
platform formatting. That made the product deterministic, but forced materially different channel
copy into separate campaigns and obscured their relationship as one reviewed announcement. Current
official Buffer and Sprout Social composer documentation both treat per-network customization as a
normal multi-channel workflow:

- <https://support.buffer.com/article/642-scheduling-posts>
- <https://support.sproutsocial.com/hc/en-us/articles/36494895896589-How-do-I-use-Customize-Post-per-Network-in-Compose>

The smallest defensible response is an optional source-level mapping of complete content overrides.
It retains one baseline, deterministic offline builds, and existing artifact contracts. It does not
add provider accounts, mutable drafts, scheduling, AI generation, or network access.

Complete replacement was selected over partial inheritance. A variant requires `body`; omitted
`title`, `link`, and `hashtags` are intentionally absent. This avoids an ambiguous distinction
between “inherit,” “remove,” and “forgot to specify,” and mirrors Sprout's documented unique-content
split. Removing the variant restores baseline behavior.

### Findings and implementation checklist

- P0: none discovered; existing campaigns remain valid and retain identical output.
- P1: platform-specific copy previously required duplicated campaign files, producing unrelated
  identities and making whole-announcement review harder. The implemented variant contract closes
  this gap within one campaign identity.
- P1: any override must participate in source hashing, semantic review, approval invalidation, plan
  identity, adapters, handoffs, and readiness. These paths consume normalized campaign source and
  rendered drafts; direct regression tests cover campaign/plan propagation.
- P1: variant input is untrusted. Runtime and schema enforce canonical requested keys, strict
  object fields, required bounded bodies, normalized single-line titles, HTTP(S) links without
  credentials or whitespace, and bounded unique hashtags.
- P2: account-resolved mentions, network-specific media/caption overrides, and provider capability
  discovery remain deferred because they require credentials, volatile external state, or a larger
  contract. Media targeting remains a separate reviewed concern.
- P2: external user validation remains required; competitor workflow documentation demonstrates a
  category need, not demand for this particular local-first implementation.

Implemented locally: `PlatformContentVariant`, strict parsing and schema rules, formatter selection,
semantic diff coverage, identity and approval propagation, public API/version update, realistic
example, installed-wheel CI smoke, and author/security/migration documentation. Release acceptance
requires clean formatting, lint, strict typing, full tests with at least 90% coverage, compilation,
schema validation, clean sdist-to-wheel build, an installed-wheel variants journey, hosted Python
3.10/3.13 CI, review disposition, exact artifact hashes, and a documented rollback point. Exact
release evidence will replace this working status after those gates pass.

Compatibility is intentionally additive: campaign schema remains v1, adapter v2 and all generated
artifact schemas are unchanged, and campaigns without `platformVariants` normalize exactly as
before. Package version advances to 0.10.0 because a new public model and authoring capability join
the supported pre-1.0 surface. Runtime remains dependency-free and its operating cost remains local
compute and storage only. Handoff v1's existing producer-version rule still applies: use 0.9 to
verify a 0.9-produced packet byte-for-byte, or regenerate approval-dependent evidence with 0.10.

### Release verification and disposition

Implementation and all review fixes converge at exact commit
`11d483c4c4484850130222b86e4650c11d6bde55`. This evidence section is a subsequent docs-only
change, so the artifact hashes identify that exact reviewed code tree rather than a
self-referential source archive.

| Verification | Exit | Actual result |
| --- | ---: | --- |
| `python -m black --check samsarix_creative_spirals tests examples` | 0 | All 28 files unchanged. |
| `python -m flake8 samsarix_creative_spirals tests examples` | 0 | No findings. |
| `python -m mypy` | 0 | Strict typing passed across 27 source files. |
| `python -m pytest --cov=samsarix_creative_spirals --cov-report=term-missing -q` | 0 | 271 passed; 95.37% total coverage and 99% model-module coverage. |
| `python -m compileall -q samsarix_creative_spirals tests examples` | 0 | Package, tests, and examples compiled. |
| Campaign Draft 2020-12 metaschema validation | 0 | The bundled campaign schema, including variant definitions and requested-platform conditions, is valid. |
| `python -m build` | 0 | Built the 0.10.0 sdist and universal wheel from the reviewed head's sdist. |
| Python 3.11 isolated installed-wheel journey | 0 | Runtime and distribution metadata reported 0.10.0 from outside the checkout; the public variant model and packaged schema loaded; validate/check/preview produced five drafts; X, LinkedIn, and Discord used overrides; Bluesky and Mastodon used baseline content; the quality report was publishable. |
| Hosted GitHub Actions | 0 | [Run 30736526946](https://github.com/Deathcharge/samsarix-creative-spirals/actions/runs/30736526946) passed full Python 3.10 and 3.13 matrices, builds, wheel installation, and semantic variant assertions at exact head `11d483c`. |
| `git diff --check` | 0 | No whitespace errors. |

Clean-tree artifact digests from exact commit `11d483c`:

- `samsarix_creative_spirals-0.10.0-py3-none-any.whl` — SHA-256
  `1d6f8cdbf6c0152c086072534e0e48caac3746dda94ee95e2384a17c85f9d5b8`.
- `samsarix_creative_spirals-0.10.0.tar.gz` — SHA-256
  `a83451385937c042099d0cb7e5191de4170b0e0db63417d44e812716039b5e1e`.

[PR #12](https://github.com/Deathcharge/samsarix-creative-spirals/pull/12) received six
CodeRabbit inline comments. All were validated and fixed: installed-wheel CI now asserts effective
content instead of only exit codes; release metadata is backed by this exact record; public API
ordering is canonical; campaign diff v1 explicitly documents the additive field-name vocabulary;
the new CLI fixture annotation is concrete; and whole-plan approval invalidation has direct variant
coverage. New validation helpers also gained docstrings. The incremental automated review after
the fixes was rate-limited; the complete local gates and both hosted matrices passed on the
resulting head. All original threads were then resolved.

Release disposition: **release candidate with one owner-controlled distribution gate**. The source
checkout and locally built wheel support the complete declared journey with no known locally
actionable P0 or P1 defect. Public PyPI publication has not been performed and remains an explicit
owner action. External-user adoption evidence also remains unavailable; competitor workflow
evidence demonstrates the problem category, not product-market fit.

Compatibility and rollback:

- Campaign schema remains v1 and gains one optional field. Sources without `platformVariants`
  normalize and render exactly as before.
- Campaign diff v1 can emit the additive `platformVariants` source field; strict field-enum
  consumers must update, while the envelope and generated-draft field contract remain unchanged.
- Adapter v2 and campaign, plan, approval, handoff, and readiness artifact schemas do not change;
  changed variant content naturally changes identities and exact rendered bytes.
- Handoff v1's existing `producerVersion` rule requires 0.9 to verify 0.9-produced packets or fresh
  approval-dependent evidence under 0.10.
- Runtime remains standard-library-only with no accounts, credentials, network calls, scheduler,
  database, publisher, telemetry, or external operating cost.
- Before publication, roll back by reverting PR #12 or pinning main commit
  `281d0e6996ccf72f5dd760814122dcca6e301ec7`. After owner publication, use normal version pinning
  and a corrective release; do not replace published artifacts silently.

## 0.11 portable content-policy release evidence

### Evidence and product decision

Current Sprout Social and Buffer documentation demonstrates two related operating needs: review
before publishing and organization-specific language guardrails. The bounded Samsarix response is
a repository-owned literal phrase policy evaluated against exact final platform drafts. It stays
useful without accounts, hosted roles, provider credentials, regex execution, or model-based
moderation. The official sources and deliberately narrower contract are recorded in
[`POLICIES.md`](POLICIES.md).

Version 1 supports blocked and required literal phrases, platform targeting, case-sensitive or
Unicode case-folded matching, and warning/error severity. The normalized policy receives a full
SHA-256 identity and a short `scpol_*` display ID. Campaign and plan approvals bind that identity;
policy-bound handoffs additionally embed normalized `content-policy.json` as a size- and
checksum-covered artifact so later handoff verification and readiness assessment remain
self-contained. Supplying an external policy at that boundary is an optional equality check.

### Release verification and disposition

Implementation and all review fixes converge at exact commit
`b2aa49e0851f89912ff02be81fa13a5a4b8d9341`; PR #13 merged that head to `main` as
`77b3e4ca9ba466c10eb6ef1746b990a319522f87`. This evidence section is a subsequent docs-only
change, so the artifact hashes identify the exact reviewed code tree rather than a
self-referential source archive.

| Verification | Exit | Actual result |
| --- | ---: | --- |
| `python -m black --check samsarix_creative_spirals tests examples` | 0 | All 30 files unchanged. |
| `python -m flake8 samsarix_creative_spirals tests examples` | 0 | No findings. |
| `python -m mypy` | 0 | Strict typing passed across 29 source files. |
| `python -m pytest --cov=samsarix_creative_spirals --cov-report=term-missing` | 0 | 295 passed; 94.50% total coverage, 96% handoff coverage, and 99% readiness coverage. |
| `python -m compileall -q samsarix_creative_spirals tests examples` | 0 | Package, tests, and examples compiled. |
| Installed-wheel Draft 2020-12 metaschema validation | 0 | All eight packaged schemas validated outside the checkout. |
| `python -m build --outdir <isolated-directory>` | 0 | Built the 0.11.0 sdist and universal wheel from the reviewed head's sdist. |
| Python 3.11 isolated installed-wheel journey | 0 | Distribution/runtime version 0.11.0, policy schema output, policy ID `scpol_e8d14e4edbfa`, policy-bound plan approval, embedded-policy handoff `sch_262c3f70762e`, handoff verification without an external policy, and `handoff-ready` status all passed outside the checkout. |
| Hosted GitHub Actions | 0 | [Push run 30739570520](https://github.com/Deathcharge/samsarix-creative-spirals/actions/runs/30739570520) and [PR run 30739572808](https://github.com/Deathcharge/samsarix-creative-spirals/actions/runs/30739572808) each passed the full Python 3.10/3.13 matrix at exact head `b2aa49e`. |
| Post-merge GitHub Actions | 0 | [Main run 30739761175](https://github.com/Deathcharge/samsarix-creative-spirals/actions/runs/30739761175) passed both complete matrices at merge commit `77b3e4c`. |
| `git diff --check` | 0 | No whitespace errors. |

Isolated artifact digests from exact commit `b2aa49e`:

- `samsarix_creative_spirals-0.11.0-py3-none-any.whl` — SHA-256
  `a2489f3b84c4157495c026cdc4153c9fb3ec37ffa1b1fe3abb9623d7f70b80a1`.
- `samsarix_creative_spirals-0.11.0.tar.gz` — SHA-256
  `7a66d4681c22945ceac0208e8b7827e803abd82df6e17b0375edf0e31c0e420e`.

[PR #13](https://github.com/Deathcharge/samsarix-creative-spirals/pull/13) received ten
CodeRabbit inline comments. All were validated and addressed: approval-binding documentation and
the architecture flow were corrected; milestone status and human readiness output were aligned;
standalone schema copies gained a synchronization regression test; policy parsing was decomposed;
message formatting, HTML escaping, and exception-test structure were cleaned up; and policy-bound
handoffs became self-contained with direct tamper and mismatch coverage. All ten threads are
resolved. The incremental automated re-review was rate-limited, while both hosted matrices and the
complete local gates passed on the resulting head.

Release disposition: **release candidate with one owner-controlled distribution gate**. The merged
source and isolated wheel support the complete declared journey with no known locally actionable
P0 or P1 defect. Public PyPI publication has not been performed and remains an explicit owner
action. External-user adoption evidence likewise remains unavailable; competitor workflow
evidence demonstrates the problem category, not product-market fit.

Compatibility and rollback:

- Content-policy schema v1 is new. Campaign, plan, manifest, and adapter source/artifact contracts
  remain unchanged.
- Campaign-approval and plan-approval v1 gain only optional `contentPolicy` bindings. Readiness v1
  gains optional policy identity and rule context. Existing files behave as before when no policy
  is supplied.
- Handoff v1 gains one optional `content-policy.json` artifact and permits ten rather than nine
  declared artifacts. Policy-free packets retain their prior shape; the producer-version rule
  continues to require the producing package for exact byte verification.
- Runtime remains standard-library-only with no accounts, credentials, network calls, regex
  execution, model moderation, scheduler, database, publisher, telemetry, or external operating
  cost.
- Before publication, roll back by reverting merge commit `77b3e4c` or pinning pre-0.11 main commit
  `3a5c0f5278ffea4a81ca6ab0bae3479318df0da1`. After owner publication, use normal version pinning
  and a corrective release; do not replace published artifacts silently.

## 0.12 deterministic link-tracking release evidence

### Research and product decision

Campaign attribution is a concrete pre-publish workflow rather than an analytics-dashboard
expansion:

- Google Analytics documents manual `utm_*` tagging and recommends consistent case-sensitive
  source, medium, and campaign values:
  <https://support.google.com/analytics/answer/10917952?hl=en>.
- Buffer automatically adds campaign parameters for supported channels and reserves customized
  values for paid plans:
  <https://support.buffer.com/article/518-understanding-utm-parameters-and-google-analytics>.
- Sprout Social provides administrator-configured parameter sets, per-network values, URL
  matching, custom parameters, and a link preview:
  <https://support.sproutsocial.com/hc/en-us/articles/202703663-How-do-I-use-Link-Tracking>.

The defensible local-first slice is deterministic URL construction before connected publishing.
The configuration lives inside campaign source because it changes rendered output: this lets
existing canonical identity, semantic diff, approvals, plans, adapters, exports, handoffs, and
readiness bind it automatically instead of creating another side-loaded evidence dependency.

### Bounded contract and implementation

Campaign schema v1 gains optional `linkTracking` with common literal parameters and per-platform
overrides. Names are lowercase bounded ASCII; normalized values, maps, merged maps, and final URLs
are bounded. The formatter applies parameters only to the effective structured baseline or
complete-variant link, sorts names, percent-encodes UTF-8, preserves an existing query and
fragment, and rejects existing-name collisions instead of guessing whether to keep or replace a
value. Body/title URL-looking text is intentionally untouched.

Implemented and merged: immutable `LinkTracking`, strict runtime and Draft 2020-12 schema
validation, source hashing and semantic-field coverage, exact rendered propagation, public
API/version update, a five-platform example, direct campaign/approval/plan/adapter/handoff tests,
installed-wheel CI assertions, and author/security/migration documentation.

### Release verification and disposition

Implementation and all review fixes converge at exact commit
`4f0c6b129ea781b6adb52fa9e1f9bdeee9ed38ff`; PR #14 merged that head to `main` as
`a052e123a78c2021fe48692fdb5644d6426a6dad`. This evidence section is a subsequent docs-only
change, so the artifact hashes identify the exact reviewed code tree rather than a
self-referential source archive.

| Verification | Exit | Actual result |
| --- | ---: | --- |
| `python -m black --check samsarix_creative_spirals tests examples` | 0 | All 31 files unchanged. |
| `python -m flake8 samsarix_creative_spirals tests examples` | 0 | No findings. |
| `python -m ruff check samsarix_creative_spirals/models.py tests/test_tracking.py` | 0 | No findings in the review-targeted parser paths. |
| `python -m mypy` | 0 | Strict typing passed across 30 source files. |
| `python -m pytest --cov=samsarix_creative_spirals --cov-report=term-missing` | 0 | 322 passed; 94.54% total coverage and 98% model coverage. |
| `python -m compileall -q samsarix_creative_spirals tests` | 0 | Package and tests compiled. |
| Installed-wheel Draft 2020-12 metaschema validation | 0 | All eight packaged schemas validated outside the checkout. |
| Sdist-derived universal-wheel build | 0 | Built the 0.12.0 sdist, then built the wheel from that exact reviewed-head sdist. |
| Python 3.11 external installed-wheel journey | 0 | Distribution/runtime version 0.12.0, tracked campaign `scs_8ba65d16afb3`, plan `scp_cfcb3547bed2`, adapter URL assertions, plan approval, handoff `sch_758147844753`, and offline handoff verification all passed outside the checkout. |
| Hosted GitHub Actions | 0 | [Push run 30741545437](https://github.com/Deathcharge/samsarix-creative-spirals/actions/runs/30741545437) and [PR run 30741547091](https://github.com/Deathcharge/samsarix-creative-spirals/actions/runs/30741547091) each passed the full Python 3.10/3.13 matrix at exact head `4f0c6b1`. |
| Post-merge GitHub Actions | 0 | [Main run 30741706143](https://github.com/Deathcharge/samsarix-creative-spirals/actions/runs/30741706143) passed both complete matrices at merge commit `a052e12`. |
| `git diff --check` | 0 | No whitespace errors. |

Isolated artifact digests from exact commit `4f0c6b1`:

- `samsarix_creative_spirals-0.12.0-py3-none-any.whl` — SHA-256
  `693b1ae0384d0bc6946dd298f42cc501ddc369dda9f0a46aa97ecf0a9d398810`.
- `samsarix_creative_spirals-0.12.0.tar.gz` — SHA-256
  `e4de6d6ed9c72db1d336d2cf351e0bbf1c3224ac463092177d7d03219c35eb49`.

[PR #14](https://github.com/Deathcharge/samsarix-creative-spirals/pull/14) received five
CodeRabbit inline comments. All were validated and addressed: release-state and API prose were
aligned; the effective per-platform limit and override contract were clarified; platform-map
parsing was decomposed; and a platform-specific override without an effective link became a
validation error with regression coverage. All five threads are resolved. The incremental
automated re-review was rate-limited, while both hosted matrices and the complete local gates
passed on the resulting head.

Release disposition: **release candidate with one owner-controlled distribution gate**. The
merged source and isolated wheel support the declared deterministic attribution journey with no
known locally actionable P0 or P1 defect. Public PyPI publication has not been performed and
remains an explicit owner action. External-user adoption evidence likewise remains unavailable;
competitor workflow evidence demonstrates the problem category, not product-market fit.

Compatibility and rollback:

- Campaign schema remains v1 and gains only optional `linkTracking`; sources that omit it retain
  their prior normalized source, identity, and generated output.
- Adapter v2 plus plan, approval, handoff, readiness, manifest, and content-policy schemas remain
  unchanged. Tracking is carried by existing normalized source identity and exact rendered text.
- Runtime remains standard-library-only with no URL open, redirect, shortener, analytics,
  credential, publisher, scheduler, database, telemetry, or external operating cost.
- Before publication, roll back by reverting merge commit `a052e12` or pinning pre-0.12 main commit
  `b701c04c8ce1c48241449a5a1fb8caf6d04524c6`. After owner publication, use normal version
  pinning and a corrective release; do not replace published artifacts silently.

## 0.13 publication-reconciliation release evidence

### Research and product decision

Buffer and Sprout both retain post-handoff calendar/history state, but Buffer's notification flow
demonstrates that a connected product's “Sent” state may still precede native publication. The
honest local-first wedge is therefore an explicit operator assertion, not an inferred receipt.
Primary sources and exact product implications are recorded in
[`PUBLICATIONS.md`](PUBLICATIONS.md).

Publication data is a sidecar rather than campaign source: it describes events after approved
handoff and must not change the reviewed plan or rendered draft identity. It binds the full current
plan/source and exact handoff ID/hash, covers every canonical `(sequence, platform)` draft, and
derives its own identity from canonical content. Published/skipped are terminal; pending/failed
remain actionable.

### Bounded contract and implementation

Implemented: immutable publication/record/check/issue models; strict runtime and Draft 2020-12
validation; exclusive verified-handoff initialization; exact matrix/order, binding, chronology,
and completion verification; bounded credential-free URLs that are never opened; human and JSON
CLI output; stable exit code `4`; optional readiness fields/stages/gate; public schema and API;
adversarial tests; and author, architecture, security, compatibility, and workflow documentation.

The ledger is capped at 500 records (the existing 100-plan-item by five-platform envelope), notes
at 500 characters, operator labels at 120, and URLs at 2,000. Terminal outcome times must fall at
or after handoff generation and no later than assessment. Federated URLs are not host-allowlisted.
No runtime dependency, credential, network request, provider account, database, queue, telemetry,
or recurring operating cost was added.

### Release verification and disposition

Implementation and all review fixes converge at exact commit
`63ea1ff85df5d3bc33fcb599dd585c44016bd458`; PR #15 merged the evidence-bearing branch to `main`
as `6462261953ddf2d3ad8fb3fdfbe4c488e5a6e960`. This section's final merge record is a subsequent
documentation change, so artifact hashes identify the exact reviewed code tree rather than a
self-referential source archive.

| Verification | Exit | Actual result |
| --- | ---: | --- |
| `python -m black --check samsarix_creative_spirals tests examples` | 0 | All 33 files unchanged. |
| `python -m flake8 samsarix_creative_spirals tests examples` | 0 | No findings. |
| `python -m mypy` | 0 | Strict typing passed across 32 source files. |
| `python -m pytest --cov=samsarix_creative_spirals --cov-report=term-missing` | 0 | 338 passed; 93.70% total coverage and 89% publication-module coverage. |
| `python -m compileall -q samsarix_creative_spirals tests examples` | 0 | Package, tests, and example compiled. |
| Draft 2020-12 metaschema validation | 0 | All nine bundled schemas validated. |
| Sdist-derived universal-wheel build | 0 | Built the 0.13.0 sdist and then its universal wheel from exact head `63ea1ff`. |
| Python 3.11 external installed-wheel journey | 0 | Distribution/runtime 0.13.0, plan `scp_d8a68cdb1054`, handoff `sch_13f6dc1ec82b`, ten published outcomes, publication `scpub_740156792fc2`, `publication-complete`, and both publication/quality gates passed outside the checkout after intended times. |
| Hosted GitHub Actions | 0 | [Push run 30743663983](https://github.com/Deathcharge/samsarix-creative-spirals/actions/runs/30743663983) and [PR run 30743665258](https://github.com/Deathcharge/samsarix-creative-spirals/actions/runs/30743665258) each passed the complete Python 3.10/3.13 matrix at exact head `63ea1ff`. |
| Post-merge GitHub Actions | 0 | [Main run 30743994652](https://github.com/Deathcharge/samsarix-creative-spirals/actions/runs/30743994652) passed both complete matrices at merge commit `6462261`. |
| `git diff --check` | 0 | No whitespace errors; reviewed-head worktree was clean. |

Isolated artifact digests from exact commit `63ea1ff`:

- `samsarix_creative_spirals-0.13.0-py3-none-any.whl` — SHA-256
  `d40ed9d9551c0f6e2929f86fb9bc2345c83becfeb6a320cba31bcc3a02981e32`.
- `samsarix_creative_spirals-0.13.0.tar.gz` — SHA-256
  `a391c11f3aeb9e885dc7ce5e6f9c90ce4973fb99333e548226454d5da9eca37d`.

[PR #15](https://github.com/Deathcharge/samsarix-creative-spirals/pull/15) received three
CodeRabbit inline findings. All were validated and addressed: the exact Buffer source was
corrected; post-publication readiness gates became monotonic without bypassing content quality;
and malformed URL/state/container branches gained direct regression coverage. All three threads
are resolved. Incremental automated re-review was rate-limited, while complete local and hosted
gates passed on the resulting head.

Release disposition: **release candidate with one owner-controlled distribution gate**. The
merged source and isolated wheel support the declared reconciliation journey with no known
locally actionable P0 or P1 defect. Public PyPI publication has not been performed and remains an
explicit owner action. External-user adoption evidence likewise remains unavailable; competitor
workflow evidence demonstrates the problem category, not product-market fit.

Compatibility and rollback:

- Publication schema v1 is a new optional sidecar; campaign, plan, approval, handoff, adapter,
  manifest, and content-policy contracts are unchanged.
- Readiness v1 gains three stage values and optional publication fields only when a ledger is
  supplied. Existing no-ledger calls retain their previous shape, stages, and gate behavior.
- Runtime remains standard-library-only with no URL open, credential, publisher, scheduler,
  database, telemetry, provider query, or external operating cost.
- Before public package publication, roll back by reverting merge commit
  `6462261953ddf2d3ad8fb3fdfbe4c488e5a6e960` or pinning pre-0.13 main commit
  `452e466a0dce87dc7b38d41997a30d7599b145f1`. After publication, use normal version pinning and a
  corrective release; do not replace published artifacts silently.

## 0.14 approval-bound exact-media release evidence

### Research and product decision

The existing media contract made paths and alt text reviewable but left actual images outside the
approval and handoff boundary. That is a material operational gap: a downstream operator could not
prove that the image bytes being uploaded were the ones reviewed with the copy.

Current first-party contracts support one conservative local envelope. X documents a 5 MB image
upload limit; Discord's default is 10 MiB per file; the canonical Bluesky Lexicon caps an image blob
at 2,000,000 bytes; LinkedIn supports JPG/PNG below 36,152,320 pixels; and Mastodon exposes current
MIME, byte, pixel, count, and description limits per instance. The product therefore uses
Bluesky's byte ceiling and LinkedIn's strict pixel inequality, while explicitly requiring
provider/account/instance revalidation downstream. Exact links and implications are in
[`MEDIA.md`](MEDIA.md).

The opt-in belongs at approval creation, not handoff creation. This prevents an operator from
adding different unreviewed pixels after the human review record exists. Metadata-only workflows
retain their byte-for-byte approval and handoff shape.

Priority disposition: P1 “approved media workflows cannot carry or verify the reviewed bytes” is
closed by this slice. P2 full image decoding/metadata stripping and provider-specific upload
adapters remain deferred because they would add decoder supply-chain surface, credentials, live
capability state, and materially different authorization boundaries.

### Bounded contract and implementation

Implemented locally: immutable media binding/asset/index/collection types; deterministic `scm_*`
identity; campaign-relative collection beneath a trusted plan root; rejection of symbolic-link
components, non-regular files, unstable identity/size/mtime, malformed or animated images, and
out-of-envelope resources; structural PNG CRC/chunk and JPEG frame/scan inspection; SHA-256
content-addressed deduplication; opt-in CLI approval binding; automatic approval verification and
handoff collection; normalized `media-index.json`; exact `media/` packet bytes; packet-shape and
checksum verification; readiness/publication compatibility; public APIs; and a bundled Draft
2020-12 schema.

Bounds are 2,000,000 bytes per file, fewer than 36,152,320 pixels, 400 plan references, 100 MB of
unique packet bytes, and the existing 1 MB JSON index loader. Runtime remains standard-library-only
and credential-free. Collection performs local reads only; it does not fully decode pixels,
antivirus-scan, remove metadata, establish rights/consent, query providers, upload, resize, or
transform. Packet hashes remain unsigned.

### Verification and release disposition

Implementation, accepted review fixes, and packaged evidence converge at exact code commit
`0cd4d57a06b4498e288f8d51033a58d89ece95a6`. Evidence-bearing PR head
`145ca5deea209db3741088d6e2277aa3708c107b` merged to `main` as
`917a2b816c02cae241505b0af53d97a006fc46d4`. This section's final merge record is a subsequent
documentation change, so artifact hashes identify the exact reviewed code tree rather than a
self-referential source archive.

| Verification | Exit | Actual result |
| --- | ---: | --- |
| `python -m black --check samsarix_creative_spirals tests examples` | 0 | All 35 files unchanged. |
| `python -m flake8 samsarix_creative_spirals tests examples` | 0 | No findings. |
| `python -m mypy` | 0 | Strict typing passed across 35 source files. |
| `python -m pytest --cov=samsarix_creative_spirals --cov-report=term-missing` | 0 | 372 passed; 93.57% total coverage and 93% media-package coverage. |
| `python -m compileall -q samsarix_creative_spirals tests examples` | 0 | Package, tests, and examples compiled. |
| Draft 2020-12 metaschema validation | 0 | All ten bundled schemas validated. |
| Sdist-derived universal-wheel build | 0 | Built the 0.14.0 sdist and then its universal wheel from exact code head `0cd4d57`. |
| Python 3.11 external installed-wheel journey | 0 | Distribution/runtime 0.14.0, all ten schemas, plan `scp_9ae2b6c67094`, media package `scm_25320c1662b1`, one exact image, ten handoff artifacts, handoff `sch_2bf154434450`, five published outcomes, publication `scpub_87e41e3247eb`, `publication-complete`, and `pip check` passed outside the checkout. |
| Hosted GitHub Actions before review fixes | 0 | [Push run 30746032018](https://github.com/Deathcharge/samsarix-creative-spirals/actions/runs/30746032018) and [PR run 30746043402](https://github.com/Deathcharge/samsarix-creative-spirals/actions/runs/30746043402) each passed the complete Python 3.10/3.13 matrix at pre-review branch head `1e60339`. |
| Hosted GitHub Actions after review fixes | 0 | [Push run 30746628682](https://github.com/Deathcharge/samsarix-creative-spirals/actions/runs/30746628682) and [PR run 30746629976](https://github.com/Deathcharge/samsarix-creative-spirals/actions/runs/30746629976) each passed the complete Python 3.10/3.13 matrix at reviewed branch head `145ca5d`. |
| Post-merge GitHub Actions | 0 | [Main run 30746689501](https://github.com/Deathcharge/samsarix-creative-spirals/actions/runs/30746689501) passed both complete matrices at merge commit `917a2b8`. |
| `git diff --check` | 0 | No whitespace errors at the reviewed code commit. |

Isolated artifact digests from exact code commit `0cd4d57`:

- `samsarix_creative_spirals-0.14.0-py3-none-any.whl` — SHA-256
  `d6425c5319dc1b823d708e6f51016272901ac048f7f7efdd7cc5ceb4148eb2ea`.
- `samsarix_creative_spirals-0.14.0.tar.gz` — SHA-256
  `7e5a146e11d2931d65eba770b5f11ba143e6196c4f88a2422239ec45c7c74d7b`.

[PR #16](https://github.com/Deathcharge/samsarix-creative-spirals/pull/16) received four inline
comments. Three were validated and addressed: the handoff question count and legacy lowercase
`csv` diagnostic were corrected, and duplicate PNG test construction moved to one parameterized
helper. The claimed public `__all__` mismatch was rejected because the complete exact-list
assertion in `tests/test_public_api.py` already matches runtime and passes. The three valid threads
auto-resolved. Incremental automated re-review was rate-limited, while complete local gates and
both reviewed-head hosted matrices passed.

Release disposition: **merged release candidate with one owner-controlled distribution gate**. The exact local source and sdist-derived
wheel support the declared approval-to-publication journey with no known locally actionable P0 or
P1 defect. Public PyPI publication has not been performed and remains an explicit owner action. External-user
adoption evidence likewise remains unavailable; provider workflow evidence demonstrates the
operational gap and conservative envelope, not product-market fit.

Compatibility is additive: campaign and adapter contracts are unchanged; plan-approval v1 gains
optional `media`; handoff v1 permits optional `media-index.json`; readiness's embedded approval
copy stays synchronized; and metadata-only calls emit their prior shapes. The new media-package v1
schema and public names join the pre-1.0 surface. PyPI publication and external adoption validation
remain owner-controlled gates.

Before public package publication, roll back by reverting merge commit
`917a2b816c02cae241505b0af53d97a006fc46d4` or pinning pre-0.14 main commit
`89b5f94f97e859097f68ac7559a2a254c940cae2`. After publication, use normal version pinning and a
corrective release; do not replace published artifacts silently.


## 0.15 policy-bound approval-quorum release evidence

### Research and product decision

A single source-bound plan approval is useful for solo work, but it cannot express a real small-team
release rule such as “one brand reviewer and one release owner.” Current official workflows show
that approval routing, role separation, external stakeholders, and required review counts are
ordinary operational needs: Buffer routes drafts between posting roles; Planable advertises
dedicated approval flows and external approvers; Sprout Social documents message and external
approver workflows; and GitHub supports required approving-review counts plus code-owner review.
Exact official links and the bounded comparison are in
[`APPROVAL_POLICIES.md`](APPROVAL_POLICIES.md).

The local-first product decision is to reuse independent source-bound plan approvals rather than
invent hosted identities. A reusable JSON policy declares roles and counts; a canonical set embeds
that policy, assigns exact approvals to roles, and independently reverifies every member. The set
then travels through the existing handoff/readiness/publication boundary. This fills a defensible
Git-native workflow gap without credentials, accounts, notification state, or a dependency on
another Samsarix repository.

Priority disposition: P1 “a team cannot require evidence from more than one review discipline” is
closed by this slice. Authenticated membership, comments, notifications, e-signatures, and provider
publishing remain deferred because each would introduce persistent identity, authorization,
network, or regulated-signature boundaries.

### Bounded contract and implementation

Implemented locally: immutable approval policy/requirement/assignment/set/check models; deterministic
`scap_*` policy and `scas_*` set identities; 20-role and 50-approval bounds; strict lowercase role
grammar; per-role and total minima; optional case-folded distinct reviewer-label checks; duplicate
approval rejection; normalization independent of CLI input order; exact plan/source/content-policy/
media binding consistency; independent member re-verification; generic single-or-set loaders and
verifiers; exclusive set export; two bundled Draft 2020-12 schemas; public typed APIs; `plan
approval collect`; unchanged single-approval behavior; handoff/readiness/publication integration;
offline HTML set summaries; a realistic policy example; adversarial tests; and an installed-wheel
CI journey.

Reviewer labels and roles are unsigned metadata. A valid set proves only that a trusted verifier
observed structurally valid evidence satisfying the declared local artifact contract. It does not
prove separate humans, accounts, organizations, authorization, separation of duties, or
non-repudiation. Repository protection or a separately reviewed signature/attestation layer remains
necessary when those properties matter.

### Verification and release disposition

Implementation and accepted review fixes converge at exact code commit
`6acf51e3897dd145e00af96660844d2940b376f8`. [PR #17](https://github.com/Deathcharge/samsarix-creative-spirals/pull/17)
merged that head to `main` as
`acb21ce6873d16d4a5fc9221397e1375ceef06b0`. This evidence section is a subsequent
documentation-only main commit, so the artifact hashes identify the exact reviewed code tree rather
than a self-referential source archive.

| Verification | Exit | Actual result |
| --- | ---: | --- |
| `python -m black --check samsarix_creative_spirals tests examples` | 0 | All 38 files unchanged. |
| `python -m flake8 samsarix_creative_spirals tests examples` | 0 | No findings. |
| `python -m mypy` | 0 | Strict typing passed across 37 source files. |
| `python -m pytest --cov=samsarix_creative_spirals --cov-report=term-missing` | 0 | 424 passed; 93.77% total coverage and 97% approval-policy coverage. |
| `python -m compileall -q samsarix_creative_spirals tests examples` | 0 | Package, tests, and examples compiled. |
| Draft 2020-12 metaschema validation | 0 | All twelve bundled schemas validated. |
| Sdist-derived universal-wheel build | 0 | Built the 0.15.0 sdist and then its universal wheel from exact reviewed code head `6acf51e`. |
| Python 3.11 external installed-wheel journey | 0 | Distribution/runtime 0.15.0, all twelve schemas, two approvals, set `scas_d15bc114e02b`, handoff `sch_d14845e57d95`, `handoff-ready`, publication `scpub_d6d25feea12e`, ten records, and `pip check` passed outside the checkout. |
| Hosted GitHub Actions before review fixes | 0 | [Runs 31243101577](https://github.com/Deathcharge/samsarix-creative-spirals/actions/runs/31243101577) and [31243139939](https://github.com/Deathcharge/samsarix-creative-spirals/actions/runs/31243139939) each passed the complete Python 3.10/3.13 matrix at initial head `6d0592f`. |
| Hosted GitHub Actions after review fixes | 0 | [Runs 31244227416](https://github.com/Deathcharge/samsarix-creative-spirals/actions/runs/31244227416) and [31244229167](https://github.com/Deathcharge/samsarix-creative-spirals/actions/runs/31244229167) each passed the complete Python 3.10/3.13 matrix at reviewed head `6acf51e`. |
| Post-merge GitHub Actions | 0 | [Main run 31244355550](https://github.com/Deathcharge/samsarix-creative-spirals/actions/runs/31244355550) passed both complete matrices at merge commit `acb21ce`. |
| `git diff --check` | 0 | No whitespace errors at the reviewed code commit. |

Isolated artifact digests from exact reviewed code commit `6acf51e`:

- `samsarix_creative_spirals-0.15.0-py3-none-any.whl` — SHA-256
  `2e97eb32c788ad36f19f5e4311e4b290413abafb91772ffe0a2367e5f12ebeb7`.
- `samsarix_creative_spirals-0.15.0.tar.gz` — SHA-256
  `3a8df4f3ce3ccc10812c62e21b643a45eb8d97f40d17a74f2a13b2f208c0b534`.

CodeRabbit posted eight inline findings. All were validated and addressed: approval sets now require
one warning policy; direct construction enforces a non-empty set; parsing preserves aggregated
errors; evidence/check aliases are public; runnable documentation creates its inputs; tamper tests
use valid-shaped identities; and the packaged self-contained schema has both synchronized bound
assertions and generated-instance validation. Seven threads auto-resolved. The schema anchor stayed
open because its source schema already had the correct bounds and the fix lived in its sibling test;
incremental automated re-review was rate-limited. Both complete reviewed-head hosted matrices and
all local gates passed after the changes.

Release disposition: **merged release candidate with one owner-controlled distribution gate**.
The exact local source and sdist-derived wheel support the declared independent-approval-to-handoff
journey with no known locally actionable P0 or P1 defect. Public PyPI publication has not been
performed and remains an explicit owner action. External-user adoption evidence likewise remains
unavailable; competitor workflow evidence demonstrates the operational need, not product-market
fit.

Compatibility is additive: campaign, plan, adapter, campaign-approval, and single plan-approval
contracts are unchanged. Approval-policy v1 and plan-approval-set v1 are new; generic plan evidence
paths accept either form. Handoff v1 retains its fixed `approval.json` path and manifest shape,
while readiness v1 extends its existing approval field to the new set alternative. Consumers that
parse only `artifactType: "plan"` should continue using single evidence or upgrade before receiving
a set. PyPI publication and external adoption validation remain owner-controlled gates.

Before public package publication, roll back by reverting merge commit
`acb21ce6873d16d4a5fc9221397e1375ceef06b0` or pinning pre-0.15 main commit
`c25e6ca1f9de6d7d5f8372eeddf66d67fcf1c7d8`. After publication, use normal version pinning and a
corrective release; do not replace published artifacts silently.


## 0.16 source-bound plan-feedback release evidence

### Research and product decision

Connected review products keep draft comments, rejection reasons, suggestions, notifications,
accounts, and version activity together. Official Buffer, Sprout Social, and Planable workflows
confirm that review feedback and change requests are routine campaign-operations needs. Exact
official links and the bounded comparison are in [`PLAN_FEEDBACK.md`](PLAN_FEEDBACK.md).

The local-first product decision is to make the portable evidence independently useful without
imitating a hosted collaboration service. An immutable record binds feedback to one exact plan
revision and optional exact-media snapshot; any source or bound-media change makes it stale.
Current `request-changes` and `reject` decisions can fail CI, while `comment` remains informative.
Positive release authorization deliberately remains in the separately quality-gated approval
contract.

Priority disposition: P1 “review findings cannot travel with the exact draft revision they
describe” is closed by this slice. Authenticated identity, conversations, notifications, semantic
resolution, and provider publishing remain deferred because they require hosted state, credentials,
or a materially different trust boundary.

### Bounded contract and implementation

Implemented locally: immutable review/finding/check models; deterministic `scr_*` identity and
full SHA-256 content hash; `comment`, `request-changes`, and `reject` decisions; one-to-fifty
structured findings; optional plan-item, platform, and suggested-edit fields; strict item-target
validation; optional exact `scm_*` media binding; tamper and staleness detection; stable `valid` and
`blocking` semantics; exclusive non-overwriting export; a bundled Draft 2020-12 schema; typed public
APIs; `plan review create` and `plan review verify`; and an opt-in `--fail-on-blocking` CI gate.

Reviewer labels and review records are unsigned local metadata. Verification establishes canonical
structure, exact source/media binding, and current decision state; it does not prove reviewer
identity or authority, confidentiality, delivery, substantive resolution, or non-repudiation.
Repository permissions or another trusted control remain necessary when those properties matter.

### Verification and release disposition

Implementation and accepted review fixes converge at exact code commit
`4803771a9dfaf9b437ce4e22fb550011420de251`. [PR #18](https://github.com/Deathcharge/samsarix-creative-spirals/pull/18)
merged that head to `main` as
`d81da9ac2a601045048dc3f41a2a6c03edabd0c6`. This evidence section is a subsequent
documentation-only main commit, so the artifact hashes identify the exact reviewed code tree rather
than a self-referential source archive.

| Verification | Exit | Actual result |
| --- | ---: | --- |
| `python -m black --check samsarix_creative_spirals tests examples` | 0 | All 40 files unchanged. |
| `python -m flake8 samsarix_creative_spirals tests examples` | 0 | No findings. |
| `python -m mypy` | 0 | Strict typing passed across 39 source files. |
| `python -m pytest --cov --cov-report=term-missing` | 0 | 436 passed; 93.79% total coverage and 97% plan-feedback coverage. |
| `python -m compileall -q samsarix_creative_spirals tests examples` | 0 | Package, tests, and examples compiled. |
| Draft 2020-12 metaschema validation | 0 | All thirteen bundled schemas validated. |
| Sdist-derived universal-wheel build | 0 | Built the 0.16.0 sdist and then its universal wheel from exact reviewed code head `4803771`. |
| Python 3.11 external installed-wheel journey | 0 | Distribution/runtime 0.16.0, plan `scp_d8a68cdb1054`, review `scr_f56f16c874d9`, current blocking verification, native `--fail-on-blocking` exit 4, and `pip check` passed outside the checkout. |
| Hosted GitHub Actions after review fixes | 0 | [Push run 31446907105](https://github.com/Deathcharge/samsarix-creative-spirals/actions/runs/31446907105) and [PR run 31446909057](https://github.com/Deathcharge/samsarix-creative-spirals/actions/runs/31446909057) each passed the complete Python 3.10/3.13 matrix at reviewed head `4803771`. |
| Post-merge GitHub Actions | 0 | [Main run 31447348731](https://github.com/Deathcharge/samsarix-creative-spirals/actions/runs/31447348731) passed both complete matrices at merge commit `d81da9a`. |
| `git diff --check` | 0 | No whitespace errors at the reviewed code commit. |

Isolated artifact digests from exact reviewed code commit `4803771`:

- `samsarix_creative_spirals-0.16.0-py3-none-any.whl` — SHA-256
  `2b0ac61f84e3654ab70e20e1a5124c48608d44bae1d80865512022f38e255476`.
- `samsarix_creative_spirals-0.16.0.tar.gz` — SHA-256
  `cabb721a0a8b5563eb768134a76131271837153ed96748330a862a4663d27385`.

CodeRabbit posted four inline findings. All were validated and addressed: media-binding
documentation now covers both approval and review records; invalid review timestamps report the
review field; non-iterable finding containers enter aggregated `ConfigError` validation in both
public paths; and exit-code documentation includes bound-media staleness. All four threads resolved,
and the reviewed-head local and hosted gates passed after the fixes.

Release disposition: **merged release candidate with one owner-controlled distribution gate**.
The exact local source and sdist-derived wheel support the declared plan-feedback journey with no
known locally actionable P0 or P1 defect. Public PyPI publication has not been performed and remains
an explicit owner action. External-user adoption evidence likewise remains unavailable; competitor
workflow evidence demonstrates the operational need, not product-market fit.

Compatibility is additive: campaign, plan, adapter, approval, handoff, readiness, and publication
contracts are unchanged. Plan-review v1, its schema, typed values, timestamp parser, and CLI commands
join the pre-1.0 surface. Existing positive authorization continues to require plan approval.

Before public package publication, roll back by reverting merge commit
`d81da9ac2a601045048dc3f41a2a6c03edabd0c6` or pinning pre-0.16 main commit
`d4b9afbc741d0471f62c1d6ab810e43aa6157d79`. After publication, use normal version pinning and a
corrective release; do not replace published artifacts silently.


## 0.17 canonical CSV and plan import release evidence

### Research and product decision

Official Buffer, Planable, and Hootsuite workflows confirm that spreadsheet bulk authoring remains
a common campaign-operations entry point. Buffer documents a case-sensitive UTF-8 bulk template,
review/error handling, and a 100-post paid-plan bound; Planable documents a predefined CSV below 1
MB with workspace-timezone interpretation; Hootsuite documents bulk composition for hundreds of
calendar posts. Exact official links and the bounded comparison are in
[`PLAN_IMPORT.md`](PLAN_IMPORT.md).

The local-first product decision is to accept one provider-neutral, explicit-offset authoring
contract and produce normal Samsarix sources rather than schedule remote posts. The import is
independently useful with a spreadsheet, Git, and local files: it does not require an account,
credentials, another Samsarix repository, provider APIs, or mutable service state. Provider-specific
templates and direct upload remain separate adapter concerns.

Priority disposition: P1 “a team must hand-author every campaign JSON file before using the plan
workflow” is closed by this slice. Template autodetection, implicit workspace timezones, multiple
images, direct provider scheduling, and hosted collaboration remain deferred because they weaken
the canonical boundary or introduce a materially different account/network trust model.

### Bounded contract and implementation

Implemented locally: one exact ten-field UTF-8 CSV header with optional BOM; 1,000,000-byte and
100-row ceilings; pipe-separated lists; strict RFC 3339 intended times with known offsets; optional
single-image metadata without dereferencing bytes; complete campaign-model validation; stable,
bounded row/field diagnostics; Unicode-name fallback slugs plus defensive derived-path validation;
immutable typed import/check values; one bundled Draft 2020-12 diagnostic schema; public APIs;
`plan import`; a realistic template; and installed-wheel CI coverage.

Inspection has no filesystem side effects. Export first writes and authoritatively reloads a private
staged source package, then atomically reserves the absent destination, creates each final file with
no-replace semantics, and publishes `plan.json` last as the completeness marker. A destination that
exists or appears concurrently is preserved. Publication failures clean only the expected shape
owned by the current call; the exporter never merges with or deletes a competing destination.

CSV cells remain untrusted literal content. The importer never evaluates spreadsheet formulas,
opens links, loads credentials, contacts providers, reads or copies media bytes, or claims provider
acceptance. Formula-prefix neutralization remains the responsibility of later Samsarix CSV exports.

### Verification and release disposition

Implementation and accepted review fixes converge at exact code commit
`ec316fbffd02fa7091a3baa893958ed634f802da`. [PR #19](https://github.com/Deathcharge/samsarix-creative-spirals/pull/19)
merged that head to `main` as
`db15096212a2644d1621b7e0c2fb3f61524f0e41`. This evidence section is a subsequent
documentation-only main commit, so the artifact hashes identify the exact reviewed code tree rather
than a self-referential source archive.

| Verification | Exit | Actual result |
| --- | ---: | --- |
| `python -m black --check samsarix_creative_spirals tests` | 0 | All 41 files unchanged. |
| `python -m flake8 samsarix_creative_spirals tests` | 0 | No findings. |
| `python -m mypy samsarix_creative_spirals tests` | 0 | Strict typing passed across 41 source files. |
| `python -m pytest --cov=samsarix_creative_spirals --cov-report=term-missing -q` | 0 | 453 passed; 93.60% total coverage and 94% plan-import coverage. |
| `python -m compileall -q samsarix_creative_spirals` | 0 | Package compiled. |
| Sdist-derived universal-wheel build | 0 | Built the 0.17.0 sdist and then its universal wheel from exact reviewed code head `ec316fb`. |
| Python 3.11 external installed-wheel journey | 0 | Distribution/runtime 0.17.0, bundled plan-import schema, two-row import, publishable plan `scp_c4d28898fe27`, and `pip check` passed outside the checkout. |
| Hosted GitHub Actions after review fixes | 0 | [Push run 31451449749](https://github.com/Deathcharge/samsarix-creative-spirals/actions/runs/31451449749) and [PR run 31451452730](https://github.com/Deathcharge/samsarix-creative-spirals/actions/runs/31451452730) each passed the complete Python 3.10/3.13 matrix at reviewed head `ec316fb`. |
| Post-merge GitHub Actions | 0 | [Main run 31451729185](https://github.com/Deathcharge/samsarix-creative-spirals/actions/runs/31451729185) passed both complete matrices at merge commit `db15096`. |
| `git diff --check` | 0 | No whitespace errors at the reviewed code commit. |

Isolated artifact digests from exact reviewed code commit `ec316fb`:

- `samsarix_creative_spirals-0.17.0-py3-none-any.whl` — 125,121 bytes; SHA-256
  `ae1db9ce4e1add829383f349bb1409ac14752654ea55f1cccc5b873f52f93f15`.
- `samsarix_creative_spirals-0.17.0.tar.gz` — 265,105 bytes; SHA-256
  `c6372731cfca3e67c3ccbb8f14e4022ae5a12f937020a4f3f8c1d250268e7aa1`.

CodeRabbit posted five inline findings after the first hardening pass. All were validated and
addressed: Markdown table delimiters are unambiguous; final-destination reservation is race-safe;
publication uses no-replace file creation and failure cleanup; upstream campaign diagnostics are
control-free and bounded; and derived source filenames cannot escape structured row diagnostics.
Regression tests cover a competing writer, publish failure, oversized/control-bearing upstream
messages, Unicode fallback names, and an invalid derived slug. Incremental automated re-review was
rate-limited after the fix commit, but its status completed successfully and both final hosted
matrices plus all local gates passed on that exact head.

Release disposition: **merged release candidate with one owner-controlled distribution gate**.
The exact local source and sdist-derived wheel support the declared spreadsheet-to-plan journey with
no known locally actionable P0 or P1 defect. Public PyPI publication has not been performed and
remains an explicit owner action. External-user adoption evidence likewise remains unavailable;
competitor workflow evidence demonstrates the operational need, not product-market fit.

Compatibility is additive: campaign, plan, adapter, review, approval, handoff, readiness, and
publication contracts are unchanged. Plan-import-check v1, its schema, typed values, CSV contract,
and CLI command join the pre-1.0 surface. Generated campaign and plan JSON use existing v1 schemas,
so downstream consumers can treat imported sources exactly like hand-authored sources.

Before public package publication, roll back by reverting merge commit
`db15096212a2644d1621b7e0c2fb3f61524f0e41` or pinning pre-0.17 main commit
`bc9270f951944adacbbc4bc746021a054da5f72b`. After publication, use normal version pinning and a
corrective release; do not replace published artifacts silently.


## 0.17.1 pre-release security hardening

A standard repository-wide Codex Security scan reviewed all 21 production Python files at
`ce4abb6ec604a090e8bd748edc1e6ea528f22198` and classified all 108 tracked paths. The sealed scan
`fe636c60-28b1-4d25-8799-e508759840ec` reported seven source-backed findings: one high-severity
Windows junction output-redirection path, three medium publication/terminal/media-integrity gaps,
and three low bounded-resource or local race paths.

The 0.17.1 patch treats Windows junctions and any reparse point as link-like, rechecks stable
directory identities around mutations and cleanup, checks the final opened exact-media handle
against its allowed campaign root on Windows, revalidates direct publication objects through the
serialized contract, escapes terminal-control diagnostics, bounds campaign validation work, and
stops CSV parsing once one excess row proves the row-limit failure. The earlier 0.17.0 artifacts
were not tagged, released, or uploaded to PyPI.

Local verification after remediation: clean Black, Flake8, and strict mypy checks across 43 source
files; 456 tests passed at 92.93% branch coverage on Python 3.11, including an actual Windows
directory-junction regression; and package/tests/examples compiled successfully. Distribution
metadata passed `twine check`. Reviewed head `515b782` merged through
[PR #20](https://github.com/Deathcharge/samsarix-creative-spirals/pull/20) as exact release tree
`11707dd288f4b4c8392d5d6c69599b6caa57b693`. Both final PR matrices passed in runs
`31460139483` and `31460142314`; CodeRabbit completed with a rate-limit disposition and no posted
finding. [Post-merge run 31460298842](https://github.com/Deathcharge/samsarix-creative-spirals/actions/runs/31460298842)
passed the complete Python 3.10/3.13 quality, build, and installed-wheel matrices.

Exact distributions built from merge tree `11707dd`:

- `samsarix_creative_spirals-0.17.1-py3-none-any.whl` — 128,362 bytes; SHA-256
  `e9184ba147d933c76e0383e13faabb3284e41e9ec844107437e6e5a30bddd5b5`.
- `samsarix_creative_spirals-0.17.1.tar.gz` — 270,618 bytes; SHA-256
  `47ce6a05c643609515b3f8f39b3f3dca973468e90621389ccfb162835ec98732`.

An isolated Python 3.11 installation of that exact wheel reported version 0.17.1, emitted the
bundled plan-import schema, imported the two-row example as publishable plan
`scp_668860e86792`, and passed `pip check`. This evidence-only documentation commit is intentionally
outside the tagged source tree so the published artifact digests remain self-consistent. Roll back
before distribution by reverting merge `11707dd` or pinning `ce4abb6`; after distribution, publish
a higher corrective version rather than replacing artifacts.

## 0.18 validated publication-outcome recording

### Product decision and baseline

The 2026-08-31 continuation began from clean, synchronized main `1949985`, following the public
0.17.1 prerelease. The local Python 3.11 baseline passed 456 tests with 92.91% coverage. Existing
publication ledgers could be initialized and verified, but the documented operator journey
required editing structured JSON by hand. This was an actionable P1 usability/reliability gap:
ordinary post-handoff outcome updates were easier to mis-key than campaign preparation itself.

Current official Buffer failure/retry documentation and Postiz's post-list contract support the
need for reconciliation and deliberate retries; links and bounded conclusions are in
[`PUBLICATIONS.md`](PUBLICATIONS.md#current-workflow-evidence-2026-08-31). These are workflow signals,
not user-demand or adoption evidence for Samsarix. The product remains a credential-free local CLI
and library for creators, release operators, and small Git-native content teams.

### Implementation and acceptance

- [x] Add a typed immutable `record_campaign_plan_publication` operation and CLI `plan publication
  record`, selecting an exact existing one-based item/platform pair.
- [x] Reuse publication v1 validation and exact handoff verification before and after recording.
- [x] Support pending outcomes, failed retries, idempotent exact repeats, and explicit
  published/skipped corrections without backdating or inheriting stale metadata.
- [x] Save new snapshots with exclusive-create semantics; preserve the input and existing outputs.
- [x] Cover malformed arguments, stale/altered evidence, chronology, terminal replacement,
  metadata clearing, schema conformance, CLI diagnostics, and overwrite protection in tests.
- [x] Replace manual ledger edits in installed-wheel CI with the actual CLI recording journey.
- [x] Update README, API contract, workflow guide, roadmap, changelog, version, and citation.
- [x] Verify implementation commit `672e7d5` locally, in an isolated installation, and on hosted CI.
- [x] Inspect review feedback, merge, publish versioned GitHub artifacts, and record exact evidence.

No new runtime dependencies, network calls, credentials, telemetry, schema versions, or provider
actions are introduced. `record` success means a valid snapshot was saved, not that publishing
succeeded or all outcomes are complete. `verify` and readiness retain their separate completion
gates. Old v1 ledgers remain readable; previous hashes and schema semantics are unchanged.

### Risks, deferrals, and distribution

Snapshots preserve earlier files but are not linked or authenticated history. Concurrent operators
can branch from the same input; no automatic latest-file selection or merge is claimed. Git review
remains the collaboration boundary. URL validation does not establish delivery; operators must
check native platforms before retrying ambiguous provider failures. The command has zero provider
cost and retains no additional data outside requested local files.

Highest-value next work is external pilot feedback on the full import/review/handoff/reconciliation
journey. Automatic synchronization, batch provider adapters, and signed append-only history are P2
expansions requiring separate contracts, not necessary parts of this local slice. PyPI still needs
owner-configured credentials or trusted publishing; GitHub wheel/sdist distribution is available.
No external accounts, paid services, legal-license changes, or cross-repository edits are required.

### Implementation verification at `672e7d5`

- `py -3.11 -m black --check samsarix_creative_spirals tests examples`: 44 files unchanged.
- `py -3.11 -m flake8 samsarix_creative_spirals tests examples`: no findings.
- `py -3.11 -m mypy`: strict checks passed across 43 source files.
- `py -3.11 -m pytest -q --cov=samsarix_creative_spirals --cov-report=term`: 485 passed,
  93.13% coverage, including 42 publication tests.
- `py -3.11 -m compileall -q samsarix_creative_spirals tests examples`: passed.
- `py -3.11 -m build --outdir <isolated-artifact-directory>`: built sdist and its universal wheel;
  `py -3.11 -m twine check <wheel> <sdist>` passed; all 14 packaged schemas passed Draft 2020-12
  metaschema validation.
- A separate Python 3.11 virtual environment installed the exact wheel with no dependencies and
  ran the CLI outside the checkout: approval, handoff, pending ledger, failed attempt, retry,
  ten published outcomes, preserved prior files, publication-complete readiness, and `pip check`
  all passed. The final ledger ID was `scpub_5a37f9f02fff`.
- [Push run 33379073250](https://github.com/Deathcharge/samsarix-creative-spirals/actions/runs/33379073250)
  and [PR run 33379137402](https://github.com/Deathcharge/samsarix-creative-spirals/actions/runs/33379137402)
  passed the complete Python 3.10/3.13 quality, build, and installed-wheel matrices.

The security-policy maintenance uses the root `SECURITY.md` chain only. It updates release-version
wording and the outcome-recording boundary; no exclusions, severity criteria, or accepted risks
change. The release artifact was built after the documentation/review checkpoint and its exact
digest is recorded separately below, rather than claiming the earlier candidate includes later edits.

### 0.18 published release evidence

CodeRabbit reviewed implementation `672e7d5` and posted one actionable finding: the future release
wheel URL was not yet live. No code finding was posted. The final documentation checkpoint
`0864fe65809748ffe50825e53ecabf2b0ce30202` changed only `SECURITY.md` and this verification record;
application code, tests, and CI remained identical. Both final-head matrices passed in
[push run 33379649424](https://github.com/Deathcharge/samsarix-creative-spirals/actions/runs/33379649424)
and [PR run 33379653485](https://github.com/Deathcharge/samsarix-creative-spirals/actions/runs/33379653485).

Final distributions were built from that exact head, including a wheel built from its sdist:

- `samsarix_creative_spirals-0.18.0-py3-none-any.whl`: 130,195 bytes; SHA-256
  `db84278a7b82c97461efc21ae762e7b982ffe881618c33e461b42a9a62922b52`.
- `samsarix_creative_spirals-0.18.0.tar.gz`: 280,265 bytes; SHA-256
  `1fe4d084ed3db11c7e59fccb4291587d1ad2dd7bb9fdfa5518bccb32b4907467`.

Both passed `twine check`, all 14 final wheel schemas validated, and a new isolated Python 3.11
environment reran the entire ten-outcome CLI journey from the exact final wheel. The failed retry,
preserved snapshots, publication-complete gate, version check, and `pip check` passed again, with
ledger ID `scpub_5a37f9f02fff`.

Annotated tag `v0.18.0` points to `0864fe6`. The [GitHub alpha release](https://github.com/Deathcharge/samsarix-creative-spirals/releases/tag/v0.18.0)
was published with both distributions and `SHA256SUMS.txt` before merging the README link.
Independent downloads matched both hashes; the exact README wheel URL returned HTTP 200. This
resolved the sole review finding with evidence, and the review thread was marked resolved.
[PR #22](https://github.com/Deathcharge/samsarix-creative-spirals/pull/22) then merged as
`d9c5cde241cffe053917b8e9790d6679252a78b8`. Its tree is identical to the tag, and
[post-merge CI 33380272863](https://github.com/Deathcharge/samsarix-creative-spirals/actions/runs/33380272863)
passed all quality, test, build, and installed-wheel steps on Python 3.10 and 3.13.

Release disposition: **published, verified alpha**. No locally actionable P0 or P1 defect is known
in this feature slice. External pilot/adoption evidence and PyPI credentials/trusted-publisher
configuration remain separate external gates; they are not inferred from automated checks. There
was no new repository-wide security scan for this slice; targeted regression tests, source review,
and CodeRabbit review are the evidence described here.

Compatibility is additive: publication v1 and every existing schema are unchanged. Retain earlier
snapshot files when using the new command; no automatic merge, signing, or provider verification
is introduced. For rollback, pin the earlier `v0.17.1` distribution or revert merge `d9c5cde` on a
new reviewed branch. Published tags/assets must not be overwritten; ship a higher corrective
version for any future defect. This evidence-only update is intentionally outside the release tag.
