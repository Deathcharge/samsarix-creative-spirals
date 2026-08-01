# Samsarix Creative Spirals roadmap

Last updated: 2026-08-01

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

## Active milestone — 0.4 campaign plans

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

## Planned milestone — 0.5 review and interoperability

- Add semantic campaign/config diff output for reviewers and automation.
- Add explicit local approval metadata tied to a source hash, without claiming cryptographic
  identity until a signing model is designed and reviewed.
- Publish versioned adapter contracts and fixtures for third-party draft importers.
- Run a small pilot using the exact packaged wheel and record observed failures and adoption signals.

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
