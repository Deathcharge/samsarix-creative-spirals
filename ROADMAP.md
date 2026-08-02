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

## Implemented milestone — 0.9 launch readiness

- [x] Consolidate plan quality, time-aware schedule policy, current approval, and exact handoff
  verification into one stable stage and machine-readable report.
- [x] Distinguish informational status from explicit quality, approval, and handoff CI gates with
  documented exit codes.
- [x] Write an exclusive, self-contained, escaped, script-free offline HTML board with complete
  copy-ready drafts and no remote resources.
- [x] Publish typed readiness APIs and a bundled readiness v1 JSON Schema without adding runtime
  dependencies, credentials, or hosted state.
- [ ] Complete hosted release verification and record exact reviewed artifacts and rollback
  evidence.

Sprout Social and Buffer both make calendar visibility and awaiting-approval state first-class;
Buffer's July 2026 update specifically addresses the friction of locating drafts from the
calendar. Samsarix provides the corresponding local snapshot for credential-free and Git-native
workflows, while deliberately excluding notifications, shared mutable state, and provider actions.
Contract details and official sources are in [`docs/READINESS.md`](docs/READINESS.md).

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
