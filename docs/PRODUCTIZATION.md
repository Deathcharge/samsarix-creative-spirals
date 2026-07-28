# Productization record

Last updated: 2026-07-28

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

## Chosen product definition

**Product:** a dependency-free, local-first campaign preview/export CLI and Python library.

**Target user:** a solo creator, developer advocate, or small content team with an approved source
draft who needs consistent platform variants and reviewable artifacts, but does not want to grant
account access or deploy a social-management service.

**Problem solved:** safely turn one source draft into bounded X, LinkedIn, and Discord files with a
deterministic identity, explicit warnings, and a machine-readable manifest.

**Primary journey:** install locally → create or supply campaign JSON → validate → preview all
platform variants → explicitly export an outbox bundle → review/copy the files into an approved
publishing process.

**Independent reason to exist:** Buffer, Typefully, and Postiz center on connected-account
scheduling and publishing. This tool is a small, version-control-friendly preprocessing and review
boundary with no credentials, network calls, hosted state, or account risk. It can complement any
publisher without depending on Helix Unified.

**Deliberately out of scope for 0.1:** automatic publishing; social authentication; background
scheduling; analytics; AI generation; media processing; collaborative approvals; account-specific
capabilities; a web UI; database/cloud infrastructure; and private Helix integrations.

## Product and architecture decisions

1. Start from human-approved text. The old “generate” step could not work without an unreleased
   package and encouraged credential/cost expansion.
2. Export local drafts instead of simulating publication. Side effects remain visible and under
   user control.
3. Use strict, versioned JSON. The Python standard library handles it on every supported platform;
   rejecting unknown keys catches mistakes early.
4. Maintain a minimal public API: validated models plus load, build, and export functions.
5. Derive campaign IDs from canonical normalized input. Equal inputs produce equal preview IDs and
   changed inputs produce new bundle paths.
6. Default to no overwrite. Replacement requires `--overwrite`; bundle child paths are generated,
   not accepted from campaign input.
7. Keep zero runtime dependencies. This removes the original install blocker and minimizes supply
   chain, compatibility, operating-cost, and maintenance risk.
8. Keep the existing license text unchanged. Metadata no longer makes the false Apache/MIT/OSI
   claims that appeared in prior packaging and documentation.

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
- [ ] Owner/legal confirmation of license identity and distribution rights (external gate).
- [ ] Exercise the committed GitHub Actions workflow on GitHub-hosted Linux/Python 3.10 and 3.13
  (external gate; local Windows verification cannot substitute for a hosted run).

### P2 — valuable post-release work

1. Add an optional JSON Schema artifact and editor integration for campaign authoring.
2. Add Bluesky/Mastodon formatters only after sourcing and testing their current official limits.
3. Add a `diff` command for comparing two deterministic campaign bundles.
4. Add media-reference validation without reading or uploading media.
5. Evaluate an optional official `twitter-text` adapter for exact edge-case parity; keep the
   dependency optional and retain conservative zero-dependency behavior.

## Implementation checklist and completed work

- [x] Preserve and audit the initial worktree/history.
- [x] Record real baseline commands and outcomes.
- [x] Define a narrow independent product and out-of-scope boundary.
- [x] Implement immutable config/result models.
- [x] Implement strict normalization and validation.
- [x] Implement X, LinkedIn, and Discord formatting with warnings.
- [x] Implement deterministic, side-effect-free preview.
- [x] Implement safe, explicit outbox persistence and overwrite recovery behavior.
- [x] Implement `--help`, `--version`, `init`, `validate`, `preview`, and `export`.
- [x] Add representative unit, integration, command-level, and security regression tests.
- [x] Add current packaging, build metadata, changelog, and CI.
- [x] Replace all user and contributor documentation with verified behavior.
- [x] Complete final clean-environment install/build/wheel smoke verification.
- [x] Complete adversarial final review and update final disposition.

## Release acceptance criteria

- [x] Product identity, target user, primary journey, and exclusions are explicit.
- [x] Runtime installation has no unavailable or third-party dependencies.
- [x] Validate, preview, export, existing-output failure, and explicit overwrite work end to end.
- [x] Empty/malformed/oversized/unsafe inputs fail with actionable messages.
- [x] Drafts stay within configured platform limits and modifications are visible.
- [x] Build, format, lint, strict type checking, and tests pass locally.
- [x] CI protects the meaningful checks and smoke-tests the installed wheel.
- [x] No credentials, telemetry, production endpoints, or imaginary Helix services are required.
- [x] README examples and commands match implemented scripts.
- [ ] License identity/distribution terms are confirmed by the owner/legal reviewer.
- [ ] Hosted CI completes successfully on the declared Python matrix.

## Known risks

- Platform rules can change after release. Current defaults are conservative, warnings are visible,
  and final review in each platform composer remains required.
- X's complete `twitter-text` parser contains edge cases beyond this dependency-free implementation.
  The current algorithm follows documented weights and keeps detected URLs atomic, but does not
  claim conformance certification.
- The full quality suite has been verified locally on Windows/Python 3.11; Python 3.13 passed
  compile/import/validate/build smoke checks. Hosted CI is configured for Linux and full Python
  3.10/3.13 quality runs but remains an external execution gate.
- `--overwrite` updates draft files then writes the manifest last. A process/filesystem failure
  during explicit overwrite can leave files newer than the old manifest; rerunning the same command
  recovers the bundle.
- The existing license files use different contact domains and the main license names “Helix
  Licensing System” rather than this package. This is a legal/distribution ambiguity, not a local
  engineering defect that should be guessed at.

## Final verification results

Final local environment: Windows, Python 3.11.9. All commands below were run after the adversarial
fix pass.

| Command | Exit | Actual result |
| --- | ---: | --- |
| `python -m black --check helix_creative_spirals tests examples` | 0 | 14 files unchanged. |
| `python -m flake8 helix_creative_spirals tests examples` | 0 | No findings. |
| `python -m mypy` | 0 | No issues in 13 source files. |
| `python -m pytest --cov=helix_creative_spirals --cov-report=term-missing` | 0 | 65 passed; 93.68% total coverage. |
| `python -m compileall -q helix_creative_spirals tests examples` | 0 | All files compiled. |
| `python -m build --outdir <isolated-temp-dir>/dist` | 0 | Built `0.1.0` sdist and universal wheel from an isolated build environment. |
| isolated `python -m pip install --no-deps <wheel>` | 0 | Installed `0.1.0`; metadata has zero default runtime and six optional dev dependencies. |
| isolated `helix-spirals --version` | 0 | Reported `helix-spirals 0.1.0`. |
| isolated validate → preview → export | 0 | Example produced three drafts and a valid manifest outside the source checkout. |
| isolated `python -m pip check` | 0 | No broken requirements. |
| isolated `python examples/library_usage.py` | 0 | Exported all three drafts through the installed public API. |
| `py -3.13 -m compileall ...` plus validate/build smoke | 0 | Python 3.13.14 compiled and exercised the stdlib-only core successfully. |

Artifact inspection found 14 wheel entries containing the intended public package and no tests or
orphan consensus package. The 43-entry sdist contains the package, documentation, examples, and
complete test suite (including `tests/conftest.py`). `git diff --check` is part of the final
worktree review.

The hosted GitHub Actions matrix, public package index resolution, and real platform publishing
were not run. The local Python 3.13 installation did not include pytest, and a bounded isolated
development-tool installation was stopped after it failed to complete; only its dependency-free
smoke path is claimed. Hosted CI and public distribution require external repository/owner action;
platform publishing is deliberately absent from the product and therefore is not an untested claim.

## External and owner-controlled blockers

1. **License confirmation:** the owner/legal reviewer must confirm the licensor, Licensed Work,
   initial/change dates, additional-use/production-call terms, contact domain, and relationship
   between `LICENSE` and `LICENSE.PROPRIETARY`. Verification: update approved license files and
   ensure package metadata/README exactly match them.
2. **Hosted CI:** enable GitHub Actions for the repository and obtain a green run for `.github/workflows/ci.yml`.
3. **Public distribution:** if desired, the owner must confirm the PyPI name, create/configure the
   trusted publisher, and publish the locally verified artifacts. No account or package was created
   during this pass.

## Distribution and sustainability model

For validation, distribute as a Git checkout or wheel and install with `pipx`/`pip`. Public PyPI
publication is appropriate only after the license and hosted-CI gates. The core tool has no
operating cost and can remain a free local utility. If commercial sustainability is desired later,
paid, separately permissioned publishing connectors or team workflow integrations are plausible;
the local preview/export core should remain useful without them and must never silently send draft
content.

## Release disposition

**Release candidate with two named external gates:** owner/legal confirmation of the license files
and a green hosted GitHub Actions run on the declared Python matrix. The local product journey,
package artifacts, tests, and documentation meet the 0.1 acceptance criteria, and no locally
actionable P0 is known. Public publication should wait for both gates.
