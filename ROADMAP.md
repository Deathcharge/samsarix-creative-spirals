# Samsarix Creative Spirals roadmap

Last updated: 2026-08-02

## Product position

Samsarix Creative Spirals is the credential-free, Git-native quality and packaging layer that sits
before a social publisher. It turns approved campaign source into deterministic, reviewable,
platform-bounded artifacts without hosting drafts, connecting accounts, or granting publish access.

It should remain independently installable and useful. Integrations with Samsarix or third-party
publishers must use versioned files or public APIs, never shared private source.

## Evidence-backed wedge

Current connected-account products validate that teams value multi-platform drafts, bulk campaign
work, approvals, and calendars:

- Buffer supports bulk CSV uploads with a review step and paid-team approval workflows:
  <https://support.buffer.com/article/926-how-to-upload-posts-in-bulk-to-buffer> and
  <https://support.buffer.com/article/665-managing-and-approving-draft-posts>.
- Typefully organizes drafts, calendars, teams, and analytics around connected “social sets,” and
  exposes authenticated create/schedule/publish APIs:
  <https://support.typefully.com/en/articles/8717684-social-sets-and-accounts> and
  <https://support.typefully.com/en/articles/8718287-typefully-api>.
- Postiz supports drafts, schedules, and many providers, but even its self-hosted path requires a
  server plus PostgreSQL, Redis, Temporal, storage, credentials, and outbound provider access:
  <https://docs.postiz.com/public-api/posts/create> and
  <https://docs.postiz.com/installation/system-requirements>.

Samsarix should not reproduce those operational systems. Its differentiated value is deterministic
pre-publication QA that works offline, fits code review, retains source provenance, and hands
portable artifacts to any approved publishing process.

## Priority use cases

1. **Developer and open-source release communications:** prepare one release message for X,
   LinkedIn, Bluesky, Mastodon, and Discord, then review every bounded variant before launch.
2. **Agency and team review in Git:** store campaign JSON beside product work, run quality checks in
   CI, review exact diffs in a pull request, and export only approved artifacts.
3. **Privacy-sensitive or regulated drafting:** keep unreleased announcements and customer context
   off third-party SaaS systems until a human chooses the publishing channel.
4. **Publisher-neutral content pipelines:** produce stable Markdown/JSON artifacts that can be
   copied manually or consumed later by separately permissioned Buffer, Typefully, Postiz, or
   custom adapters.

## Completed milestone — 0.3 federated quality gates

- Add Bluesky output using the official 300-grapheme/3,000-byte text constraints.
- Add Mastodon output with its documented 500-character default.
- Allow explicit per-platform limits, especially for Mastodon instances that advertise different
  `configuration.statuses.max_characters` values.
- Add a `check` command that fails predictably on truncation and can optionally treat review
  warnings as errors, with stable JSON output for CI.
- Preserve the zero-runtime-dependency, no-network, deterministic-output boundary.
- Document migration, supported platform semantics, real workflows, and exact hosted verification.

Official platform evidence:

- Bluesky's canonical `app.bsky.feed.post` Lexicon sets `maxGraphemes` to 300 and `maxLength` to
  3,000 bytes: <https://github.com/bluesky-social/atproto/blob/main/lexicons/app/bsky/feed/post.json>.
- Mastodon documents a 500-character default, 23-character URL accounting, and server-advertised
  status limits: <https://docs.joinmastodon.org/user/posting/> and
  <https://docs.joinmastodon.org/entities/Instance/>.

## Completed milestone — 0.4 campaign plans

- Define a bounded multi-campaign plan schema with optional intended publication times.
- Validate and preview a complete launch sequence in one command.
- Export per-platform CSV plus a portable calendar artifact without scheduling or publishing.
- Report duplicate times, missing channels, ordering mistakes, and per-item quality failures.

Implementation decisions:

- Plans reference reusable, standalone campaign files through portable paths confined beneath the
  plan directory; they do not embed or depend on another repository.
- Intended times require an explicit offset and normalize to UTC. They express human intent only;
  there is no clock, queue, scheduler, or publisher.
- CSV uses a stable Samsarix interchange contract rather than claiming universal publisher import
  compatibility. RFC 5545 calendar export uses transparent events for scheduled items and tasks for
  unscheduled items: <https://www.rfc-editor.org/rfc/rfc5545>.
- Plans are capped at 100 items, matching the current paid Buffer bulk-upload ceiling while keeping
  local validation and review bounded.

## Active milestone — 0.5 review and interoperability

- [x] Add semantic campaign/config diff output for reviewers and automation.
- [x] Add explicit local approval metadata tied to a source hash, without claiming cryptographic
  identity until a signing model is designed and reviewed.
- [x] Publish a versioned deterministic adapter contract, schema, and exact export fixture for
  third-party draft importers.
- [x] Run an internal end-to-end scenario using the exact packaged wheel and record technical
  failures and fixes.
- [ ] Run an external user pilot and record adoption signals that cannot be inferred from tests.

## Completed milestone — 0.6 portable media handoff

- Add bounded JPEG/PNG path metadata and required alt text without reading or uploading media.
- Support campaign-wide and platform-targeted visuals while enforcing at most four images for any
  one platform.
- Include media changes in deterministic identity, semantic review, approval invalidation,
  manifests, and publisher-adapter handoff.
- Advance the exact adapter contract to v2 and document migration plus the filesystem/provider
  validation required when a separately permissioned adapter dereferences a path.

Official platform evidence and the conservative common-envelope decision are recorded in
[`docs/MEDIA.md`](docs/MEDIA.md). External pilot evidence remains the active product-validation
gap; it is not inferred from automated tests.

Technical completion evidence: implementation/review head `b5ecd0a`; 183 tests at 94.38%
coverage plus clean formatting, lint, strict typing, compilation, and schema validation; exact
0.6.0 wheel SHA-256 `8953dff532323837a6ddbb6a3d8fc963b947ed28f432fb0976507add93e1f541`;
[hosted Python 3.10/3.13 run 30729137546](https://github.com/Deathcharge/samsarix-creative-spirals/actions/runs/30729137546).
Rollback is a revert of the eventual PR merge or pinning pre-0.6 commit `8343c48`. Campaign/plan
schema v1 gains an optional field; adapter consumers must explicitly migrate from v1 to v2. Full
commands, artifact hashes, review disposition, and limitations are in
[`docs/PRODUCTIZATION.md`](docs/PRODUCTIZATION.md#06-portable-media-release-evidence).

## Completed milestone — 0.7 whole-plan review

- [x] Add deterministic plan diff output for metadata, required channels, ordered membership,
  schedules, source references, and nested campaign/draft changes.
- [x] Add aggregate-quality-gated plan approval metadata bound to the full normalized plan hash.
- [x] Re-run the stored plan quality policy during verification and invalidate approval when the
  plan or any referenced campaign changes.
- [x] Keep campaign approval v1 compatible by publishing a distinct plan-approval v1 schema.
- [x] Complete hosted release verification and record exact artifact and rollback evidence.

The workflow pattern is grounded in current official Buffer and Sprout Social approval
documentation and GitHub's stale-review/branch-protection controls. The product remains
credential-free: reviewer labels are untrusted metadata, while repository controls provide the
optional authenticated collaboration boundary. Contract details and sources are in
[`docs/PLAN_REVIEW.md`](docs/PLAN_REVIEW.md).

Technical completion evidence: implementation/review head `37b3898`; 199 tests at 94.66%
coverage plus clean formatting, lint, strict typing, compilation, and five-schema validation;
0.7.0 wheel SHA-256 `cc4a268b468d6a3bd037015a51160b275db4c32e1ce65323d395cc60b91aaa36`;
[hosted Python 3.10/3.13 run 30730784381](https://github.com/Deathcharge/samsarix-creative-spirals/actions/runs/30730784381).
Rollback is a revert of the eventual PR merge or pinning pre-0.7 commit `1df82d6`. Full commands,
artifact hashes, review disposition, compatibility notes, and limitations are in
[`docs/PRODUCTIZATION.md`](docs/PRODUCTIZATION.md#07-whole-plan-review-release-evidence).

## Completed milestone — 0.8 approved handoff packets

- [x] Require a current, quality-valid plan approval before handoff creation.
- [x] Package the approval with exact adapter JSON, calendar, plan manifest, and per-platform CSV
  bytes in a new non-overwriting directory.
- [x] Bind plan identity, generation time, producer version, fixed artifact paths, sizes, and
  SHA-256 values in a strict handoff v1 manifest and bundled schema.
- [x] Verify current source, approval policy, metadata hash/ID, directory shape, regular-file type,
  exact regenerated content, and stable reads without network or credentials.
- [x] Keep the trust claim precise: checksums are unsigned integrity metadata, not authenticated
  provenance, signatures, authorization, or non-repudiation.
- [x] Complete hosted release verification and record the exact reviewed artifact and rollback
  evidence.

Buffer's official workflow moves approved drafts toward the publishing queue, while GitHub's
artifact-attestation documentation makes clear that authenticated provenance requires signed
claims and identity-aware verification. Samsarix fills the local boundary between those concepts:
an approved packet that can be verified offline before a separately authorized downstream step.
Contract details and primary sources are in [`docs/HANDOFFS.md`](docs/HANDOFFS.md).

Technical completion evidence: implementation/review head `2bf35aa`; 224 tests at 94.86%
coverage plus clean formatting, lint, strict typing, compilation, and six-schema validation;
0.8.0 wheel SHA-256 `3b0391e2036790385f53dd1092211fda003014e4de0a1032d4f6bae1107a13bb`;
[hosted Python 3.10/3.13 run 30732657643](https://github.com/Deathcharge/samsarix-creative-spirals/actions/runs/30732657643).
Rollback is a revert of the eventual PR merge or pinning pre-0.8 commit `ba174ef`. Full commands,
artifact hashes, review disposition, compatibility notes, and limitations are in
[`docs/PRODUCTIZATION.md`](docs/PRODUCTIZATION.md#08-approved-handoff-release-evidence).

## Completed milestone — 0.9 launch readiness

- [x] Consolidate plan quality, time-aware schedule policy, current approval, and exact handoff
  verification into one stable stage and machine-readable report.
- [x] Distinguish informational status from explicit quality, approval, and handoff CI gates with
  documented exit codes.
- [x] Write an exclusive, self-contained, escaped, script-free offline HTML board with complete
  copy-ready drafts and no remote resources.
- [x] Publish typed readiness APIs and a bundled readiness v1 JSON Schema without adding runtime
  dependencies, credentials, or hosted state.
- [x] Complete hosted release verification and record exact reviewed artifacts and rollback
  evidence.

Sprout Social and Buffer both make calendar visibility and awaiting-approval state first-class;
Buffer's July 2026 update specifically addresses the friction of locating drafts from the
calendar. Samsarix provides the corresponding local snapshot for credential-free and Git-native
workflows, while deliberately excluding notifications, shared mutable state, and provider actions.
Contract details and official sources are in [`docs/READINESS.md`](docs/READINESS.md).

Technical completion evidence: implementation/review head `33647ba`; 235 tests at 95.18%
coverage plus clean formatting, lint, strict typing, compilation, and seven-schema validation;
0.9.0 wheel SHA-256 `b9aef0ede71ea6a7d90b92dc16ab955383bbf53917d30a88657f1a8a6299c5ac`;
[hosted Python 3.10/3.13 run 30734396322](https://github.com/Deathcharge/samsarix-creative-spirals/actions/runs/30734396322).
Rollback is a revert of PR #11 or pinning pre-0.9 commit `8a628e8`. Full commands, sdist digest,
review disposition, compatibility notes, and limitations are in
[`docs/PRODUCTIZATION.md`](docs/PRODUCTIZATION.md#09-launch-readiness-release-evidence).

## Completed milestone — 0.10 platform-native content variants

- [x] Add strict complete content overrides for any requested platform while retaining a reusable
  baseline for all other platforms.
- [x] Apply each platform's existing formatter, limit, truncation, hashtag, and warning behavior to
  the effective content block.
- [x] Bind variants into deterministic campaign and plan identity, semantic review, approval
  invalidation, adapters, handoffs, and readiness without changing downstream artifact schemas.
- [x] Document replacement semantics, current product evidence, privacy boundaries, migration, and
  a runnable five-platform example.
- [x] Complete clean artifact verification, hosted CI, automated review disposition, and exact
  release evidence.

Buffer's official composer starts with a base post and offers “Customize for each network”; Sprout
Social likewise makes the content in each network tab unique after customization. Samsarix now
supports that authoring need without adopting either product's connected-account, scheduling, or
hosted-state boundary. Contract details and primary sources are in
[`docs/VARIANTS.md`](docs/VARIANTS.md).

Technical completion evidence: implementation/review head `11d483c`; 271 tests at 95.37%
coverage plus clean formatting, lint, strict typing, compilation, campaign-schema metaschema
validation, and semantic five-platform wheel smoke; 0.10.0 wheel SHA-256
`1d6f8cdbf6c0152c086072534e0e48caac3746dda94ee95e2384a17c85f9d5b8`;
[hosted Python 3.10/3.13 run 30736526946](https://github.com/Deathcharge/samsarix-creative-spirals/actions/runs/30736526946).
Rollback is a revert of PR #12 or pinning pre-0.10 main commit `281d0e6`. Full sdist digest, review
disposition, compatibility notes, and limitations are in
[`docs/PRODUCTIZATION.md`](docs/PRODUCTIZATION.md#010-platform-native-variants-release-evidence).

## Completed milestone — 0.11 portable content policies

- [x] Add bounded, reusable literal blocked/required phrase rules with platform targeting,
  case-sensitive or case-folded matching, and warning/error severity.
- [x] Evaluate exact final rendered drafts and expose stable rule IDs in campaign, plan, readiness,
  human, and machine-readable results.
- [x] Bind normalized policy identity into campaign/plan approvals and embed normalized policy
  source in approved handoffs for standalone verification and readiness assessment.
- [x] Publish CLI/library APIs, a bundled Draft 2020-12 schema, runnable examples, adversarial
  tests, installed-wheel smoke, migration guidance, and a precise security boundary.
- [x] Complete clean artifact verification, hosted CI, review disposition, merge, and exact release
  evidence.

Sprout Social's current approval documentation and 2026 blocked-word integration show demand for
brand-specific content governance alongside review; Buffer likewise documents role-based draft
approval. Samsarix provides a portable, Git-native subset before the connected publishing boundary:
deterministic policy-as-code over rendered drafts, without accounts, remote state, or regex/AI
execution. Contract details and official sources are in
[`docs/POLICIES.md`](docs/POLICIES.md).

Technical completion evidence: implementation/review head `b2aa49e`; merge commit `77b3e4c`; 295
tests at 94.50% coverage plus clean formatting, lint, strict typing, compilation, eight installed
schema checks, and a self-contained installed-wheel handoff journey; 0.11.0 wheel SHA-256
`a2489f3b84c4157495c026cdc4153c9fb3ec37ffa1b1fe3abb9623d7f70b80a1`; and
[post-merge Python 3.10/3.13 run 30739761175](https://github.com/Deathcharge/samsarix-creative-spirals/actions/runs/30739761175).
Rollback is a revert of PR #13 or a pin to pre-0.11 main commit `3a5c0f5`. Full sdist digest,
review disposition, compatibility notes, and limitations are in
[`docs/PRODUCTIZATION.md`](docs/PRODUCTIZATION.md#011-portable-content-policy-release-evidence).

## Completed milestone — 0.12 deterministic link tracking

- [x] Add bounded common query parameters and explicit requested-platform overrides to campaign
  source without introducing templates, environment expansion, or remote state.
- [x] Apply stable UTF-8 percent encoding to the effective baseline/variant link while preserving
  existing queries and fragments and rejecting same-name collisions.
- [x] Propagate tracking through identity, semantic diff, approval invalidation, plans, adapters,
  exports, handoffs, and readiness without changing downstream artifact schemas.
- [x] Add schema, public API, realistic example, adversarial tests, installed-wheel CI smoke,
  migration guidance, and privacy/security boundaries.
- [x] Complete clean artifact verification, hosted CI, review disposition, merge, and exact release
  evidence.

Google Analytics recommends consistent manual campaign tags; Buffer and Sprout Social both expose
automated or reusable link-tracking parameters inside their connected publishing products.
Samsarix provides a deterministic Git-native attribution step before that boundary, without
opening URLs, shortening links, collecting clicks, or requiring an analytics account. Contract
details and official sources are in [`docs/TRACKING.md`](docs/TRACKING.md).

Technical completion evidence: implementation/review head `4f0c6b1`; merge commit `a052e12`; 322
tests at 94.54% coverage plus clean formatting, lint, Ruff, strict typing, compilation, eight
installed schema checks, and an isolated installed-wheel tracking-to-handoff journey; 0.12.0 wheel
SHA-256 `693b1ae0384d0bc6946dd298f42cc501ddc369dda9f0a46aa97ecf0a9d398810`; and
[post-merge Python 3.10/3.13 run 30741706143](https://github.com/Deathcharge/samsarix-creative-spirals/actions/runs/30741706143).
Rollback is a revert of PR #14 or a pin to pre-0.12 main commit `b701c04`. Full sdist digest, review
disposition, compatibility notes, and limitations are in
[`docs/PRODUCTIZATION.md`](docs/PRODUCTIZATION.md#012-deterministic-link-tracking-release-evidence).

## Release milestone — 0.13 publication reconciliation

- [x] Initialize one canonical pending record for every exact draft only after current handoff
  verification.
- [x] Validate bounded published, failed, skipped, and pending operator outcomes without opening
  URLs or claiming provider observation.
- [x] Verify plan/source/handoff bindings, exact draft coverage/order, outcome chronology, and
  terminal completion with stable JSON, CLI, and exit-code contracts.
- [x] Integrate optional invalid/in-progress/complete publication evidence into readiness and its
  explicit CI gate without changing no-ledger report behavior.
- [x] Add public typed APIs, a bundled schema, adversarial tests, installed-artifact planning, and
  documentation of the operator-assertion trust boundary.
- [x] Complete hosted CI, review, exact artifact hashes, and pre-merge rollback evidence.
- [x] Merge to main, pass post-merge CI, and record the final merge/rollback identity.

Buffer's Sent history and Sprout Social's Publishing Calendar demonstrate the operational value
of post-handoff state, while Buffer's notification workflow shows that “Sent” can precede manual
native publication. Samsarix therefore records an explicit local operator assertion rather than
fabricating provider verification. Contract details and official sources are in
[`docs/PUBLICATIONS.md`](docs/PUBLICATIONS.md).

Technical completion evidence: implementation/review head `63ea1ff`; merge commit `6462261`; 338
tests at 93.70% coverage plus clean formatting, lint, strict typing, compilation, nine schema
checks, and an isolated installed-wheel handoff-to-publication journey; 0.13.0 wheel SHA-256
`d40ed9d9551c0f6e2929f86fb9bc2345c83becfeb6a320cba31bcc3a02981e32`; and
[post-merge Python 3.10/3.13 run 30743994652](https://github.com/Deathcharge/samsarix-creative-spirals/actions/runs/30743994652).
Rollback is a revert of PR #15's merge or a pin to pre-0.13 main commit `452e466`. Full sdist
digest, review disposition, compatibility notes, and limitations are in
[`docs/PRODUCTIZATION.md`](docs/PRODUCTIZATION.md#013-publication-reconciliation-release-evidence).

## Release milestone — 0.14 approval-bound exact media

- [x] Keep media dereferencing explicitly opt-in while binding exact bytes to the human plan
  approval rather than adding unreviewed images after approval.
- [x] Enforce campaign-relative containment, no symbolic-link components, stable regular-file
  reads, conservative byte/pixel/reference/packet limits, and structural static JPEG/PNG checks.
- [x] Deduplicate image payloads by SHA-256 and embed a canonical `scm_*` media index plus exact
  content-addressed bytes in immutable handoff packets.
- [x] Verify media approval/source bindings, index identity, packet shape, file stability, sizes,
  and checksums through approval, handoff, readiness, publication, CLI, and public library paths.
- [x] Add a bundled media-package schema, adversarial and end-to-end tests, installed-wheel CI
  journey, current official provider evidence, and explicit structural-validation limitations.
- [x] Complete hosted CI and review, record exact distribution hashes, merge to main, and capture
  final rollback evidence.

The canonical Bluesky image Lexicon sets the strictest common byte ceiling at 2,000,000 bytes;
X and Discord currently allow larger files, LinkedIn requires fewer than 36,152,320 pixels, and
Mastodon exposes instance-specific limits. Samsarix therefore proves one conservative local packet
without claiming universal provider acceptance. Contract details and official sources are in
[`docs/MEDIA.md`](docs/MEDIA.md).

Reviewed technical evidence at `0cd4d57`: 372 tests at 93.57% coverage, clean formatting, lint,
strict typing, compilation, and ten schema checks; an external Python 3.11 installed-wheel journey
reached `publication-complete` with media package `scm_25320c1662b1`; wheel SHA-256
`d6425c5319dc1b823d708e6f51016272901ac048f7f7efdd7cc5ceb4148eb2ea`; sdist SHA-256
`7e5a146e11d2931d65eba770b5f11ba143e6196c4f88a2422239ec45c7c74d7b`; reviewed push/PR runs
`30746628682` and `30746629976`; merge commit `917a2b8`; and post-merge run `30746689501` all passed.
Rollback is a revert of PR #16's merge or a pin to pre-0.14 main commit `89b5f94`. Full review
disposition, sdist-derived journey identities, compatibility notes, and limitations are in
[`docs/PRODUCTIZATION.md`](docs/PRODUCTIZATION.md#014-approval-bound-exact-media-release-evidence).

## Release milestone — 0.15 policy-bound approval quorums

- [x] Add bounded reusable approval-policy v1 profiles with per-role and total minimums plus optional
  distinct reviewer-label enforcement.
- [x] Collect independently created, current plan approvals into deterministic `scas_*` evidence
  while rejecting duplicate records and mixed source, content-policy, or exact-media bindings.
- [x] Accept single or set evidence through verification, approved handoff, readiness, publication,
  public API, schemas, examples, and installed-wheel CI without changing the handoff manifest shape.
- [x] Document current Buffer, Planable, Sprout Social, and GitHub approval patterns and state the
  unsigned label/role boundary without implying authenticated separation of duties.
- [x] Complete hosted CI and review, record exact distribution hashes, merge to main, and capture
  final rollback evidence.

Connected products provide user accounts, permissions, comments, notifications, and approval
routing. Samsarix supplies a complementary credential-free artifact: a canonical quorum that can
be reviewed and protected in Git, verified offline, and handed to any separately permissioned
downstream process. Contract details and sources are in
[`docs/APPROVAL_POLICIES.md`](docs/APPROVAL_POLICIES.md).

Reviewed technical evidence at `6acf51e`: 424 tests at 93.77% coverage, clean formatting, lint,
strict typing, compilation, and twelve schema checks; an external Python 3.11 installed-wheel
journey reached `handoff-ready` with approval set `scas_d15bc114e02b`; wheel SHA-256
`2e97eb32c788ad36f19f5e4311e4b290413abafb91772ffe0a2367e5f12ebeb7`; sdist SHA-256
`3a8df4f3ce3ccc10812c62e21b643a45eb8d97f40d17a74f2a13b2f208c0b534`; reviewed push/PR
runs `31244227416` and `31244229167`; merge commit `acb21ce`; and post-merge run
`31244355550` all passed. Rollback is a revert of PR #17's merge or a pin to pre-0.15 main commit
`c25e6ca`. Full review disposition, artifact evidence, compatibility notes, and limitations are in
[`docs/PRODUCTIZATION.md`](docs/PRODUCTIZATION.md#015-policy-bound-approval-quorum-release-evidence).

## Release milestone — 0.16 source-bound plan feedback

- [x] Add immutable `comment`, `request-changes`, and `reject` records bound to one exact plan
  revision, while keeping positive release authorization in the quality-gated approval contract.
- [x] Add bounded structured findings, deterministic `scr_*` identity, tamper detection, optional
  exact-media binding, exclusive export, current/stale verification, and stable blocking semantics.
- [x] Expose CLI, typed API, bundled Draft 2020-12 schema, adversarial tests, and installed-wheel CI
  coverage without adding runtime dependencies, accounts, network access, or mutable service state.
- [x] Document current Buffer, Sprout Social, and Planable feedback workflows plus the unsigned
  reviewer-label, local blocking, confidentiality, and resolution boundaries.
- [x] Complete hosted CI and automated review, record exact distribution hashes, merge to main, and
  capture final rollback evidence.

Connected review services keep comments, rejection notes, suggestions, notifications, accounts,
and version activity beside a draft. Samsarix supplies the portable artifact portion: exact-revision
feedback that can live in Git or an archive, turns stale automatically when source changes, and can
bind reviewed image bytes without needing publisher credentials. Contract details and official
sources are in [`docs/PLAN_FEEDBACK.md`](docs/PLAN_FEEDBACK.md).

Reviewed technical evidence at `4803771`: 436 tests at 93.79% coverage, clean formatting, lint,
strict typing, compilation, and thirteen schema checks; an external Python 3.11 installed-wheel
journey produced current blocking review `scr_f56f16c874d9` and native CI exit 4; wheel SHA-256
`2b0ac61f84e3654ab70e20e1a5124c48608d44bae1d80865512022f38e255476`; sdist SHA-256
`cabb721a0a8b5563eb768134a76131271837153ed96748330a862a4663d27385`; reviewed push/PR
runs `31446907105` and `31446909057`; merge commit `d81da9a`; and post-merge run
`31447348731` all passed. Rollback is a revert of PR #18's merge or a pin to pre-0.16 main commit
`d4b9afb`. Full review disposition, artifact evidence, compatibility notes, and limitations are in
[`docs/PRODUCTIZATION.md`](docs/PRODUCTIZATION.md#016-source-bound-plan-feedback-release-evidence).

## Completed milestone — 0.17 canonical CSV and plan import

- [x] Define one provider-neutral UTF-8 authoring header with bounded spreadsheet-friendly list,
  explicit-offset time, and optional single-image metadata fields.
- [x] Inspect every accepted row through the existing campaign contract and emit stable
  schema-backed row/field diagnostics without partial writes.
- [x] Export normalized campaign JSON and a complete plan through a private staged directory,
  authoritative reload, atomic destination reservation, no-replace file creation, and a final
  `plan.json` completeness marker.
- [x] Add CLI, typed public API, bundled schema, realistic template, adversarial tests, installed
  wheel CI journey, current official workflow evidence, and explicit spreadsheet/media boundaries.
- [x] Complete hosted CI and automated review, record exact distribution hashes, merge to main, and
  capture final rollback evidence.

Official Buffer, Planable, and Hootsuite workflows confirm that spreadsheet bulk authoring is a
separate high-frequency use case. Samsarix imports its documented CSV contract into normalized
campaign files and a plan, reports bounded row errors without partial writes, preserves explicit
UTC/timezone semantics, and round-trips through existing preview/check/diff/review/export gates.
Provider-specific templates and direct upload remain separate adapters. Contract details and
official sources are in [`docs/PLAN_IMPORT.md`](docs/PLAN_IMPORT.md).

Reviewed technical evidence at `ec316fb`: 453 tests at 93.60% coverage, clean formatting, lint,
strict typing, and compilation; an external Python 3.11 exact-wheel journey imported two rows as
publishable plan `scp_c4d28898fe27`; wheel SHA-256
`ae1db9ce4e1add829383f349bb1409ac14752654ea55f1cccc5b873f52f93f15`; sdist SHA-256
`c6372731cfca3e67c3ccbb8f14e4022ae5a12f937020a4f3f8c1d250268e7aa1`; reviewed push/PR runs
`31451449749` and `31451452730`; merge commit `db15096`; and post-merge run `31451729185` all
passed. Rollback is a revert of PR #19's merge or a pin to pre-0.17 main commit `bc9270f`. Full
review disposition, artifact evidence, compatibility notes, and limitations are in
[`docs/PRODUCTIZATION.md`](docs/PRODUCTIZATION.md#017-canonical-csv-and-plan-import-release-evidence).

## Deliberate exclusions

- No automatic publishing, OAuth token storage, analytics scraping, hosted draft database, or
  background scheduler in the core package.
- No AI generation requirement; human- or tool-authored source text enters through the same schema.
- No hidden dependency on Samsarix Unified or another private repository.
- No telemetry until a specific, privacy-preserving product question justifies it.

## Completion evidence

A milestone is complete only when its exact commit, commands and results, packaged artifact,
hosted CI, rollback path, and compatibility impact are recorded. README claims must not exceed that
evidence. Publication to PyPI and flagship adoption remain separate owner-controlled decisions.
