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
analytics; AI generation; media processing; hosted collaborative approvals; cryptographic signer
identity; account-specific capabilities; a web UI; database/cloud infrastructure; and private
Helix integrations. Versions 0.4–0.13 add bounded plans, interchange, campaign and whole-plan
semantic diffs, source-bound local review metadata, portable image handoff, exact approved packet
verification, offline launch readiness, platform-native content, policy-as-code, and deterministic
link attribution without adding a scheduler, account connection, analytics collector, or network
publisher.

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

Local implementation tests are passing. Exact clean-suite results, artifact hashes, hosted CI,
review disposition, merge commit, rollback point, and final release disposition will be recorded
here after the reviewed artifact converges. Public PyPI publication and external-user adoption
evidence remain owner-controlled gates and are not inferred from automated tests.
