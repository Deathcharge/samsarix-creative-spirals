# Source-bound plan feedback

Samsarix Creative Spirals can preserve review feedback as an immutable local artifact before a
plan is approved. A `plan-review` record binds one reviewer label, one decision, and one to fifty
findings to the exact normalized plan revision and every referenced campaign. It can optionally
bind the exact referenced JPEG/PNG bytes too.

This is useful when an agency, brand, legal reviewer, or release owner needs to return actionable
feedback in Git, an archive, or another file-based workflow without opening publisher accounts or
sending draft content to a hosted review service.

## Why this is a product feature

Current connected products make the feedback loop a first-class part of approval:

- [Buffer lets an approver reject a draft back to the drafts list](https://support.buffer.com/article/665-managing-and-approving-draft-posts),
  where the author can revise it before another approval attempt.
- [Sprout Social keeps approval activity, internal comments, change history, and optional rejection notes](https://support.sproutsocial.com/hc/en-us/articles/205974715-Message-Approval-Workflows).
- [Planable places comments, text suggestions, and version history beside approval](https://planable.io/guides/content-approvals-in-planable/).

Those systems also supply hosted accounts, permissions, notifications, mutable discussion state,
and provider integrations. Samsarix does not reproduce that service layer. Its complementary
local-first contract is a deterministic, source-bound review record that is portable, diffable,
and independently verifiable offline.

## Record feedback

Use `comment` for non-blocking observations, `request-changes` when the exact revision needs work,
or `reject` when that exact revision should not advance:

```bash
samsarix-campaign plan review create examples/launch-plan.json \
  --decision request-changes \
  --by "Brand reviewer" \
  --finding "The launch claim needs supporting evidence." \
  --item 1 \
  --platform linkedin \
  --suggestion "Link the benchmark or narrow the claim." \
  --note "Resolve before release-owner approval."
```

The default filename includes the deterministic `scr_*` review ID, so independent feedback
records do not replace one another. `--output PATH` selects another new path. Export always uses
exclusive creation and refuses to overwrite an existing record.

Repeat `--finding` to add several messages. `--item` and `--platform` target every finding supplied
by that command; `--platform` requires an item number. `--suggestion` is available when exactly one
finding is supplied. Library callers or hand-authored records validated against the schema can use
different item/platform targets and suggestions for each finding.

If feedback covers actual image pixels, add `--include-media`. This invokes the same bounded exact
JPEG/PNG collection used by media-bound approval: each campaign-relative reference is confined,
read stably, structurally inspected, and represented by a content-addressed `scm_*` binding.

## Verify current relevance

```bash
samsarix-campaign plan review verify \
  examples/launch-plan.json \
  examples/launch-plan.json.scr_REVIEW_ID.review.json \
  --json
```

Verification returns `0` when the record still describes the current exact source and optional
media snapshot. Its JSON includes:

- `valid`: source, plan identity, and media binding are current;
- `blocking`: the record is current and its decision is `request-changes` or `reject`;
- the complete normalized `review` record; and
- stable `issues` when the record is stale or its media is missing/changed.

Exit `4` normally means the record no longer matches the current plan or bound-media state. Add
`--fail-on-blocking` to also return `4` for a current `request-changes` or `reject` decision, making
the record an explicit CI gate. A stale negative decision is not reported as blocking because it
describes a prior revision. Verification does not decide whether
all feedback was substantively addressed; the next reviewer examines the semantic diff and new
drafts.

Positive release authorization remains deliberately separate:

```bash
samsarix-campaign plan diff launch-plan-before.json examples/launch-plan.json
samsarix-campaign plan check examples/launch-plan.json
samsarix-campaign plan approval create examples/launch-plan.json --by "Release reviewer"
```

There is no `approve` value in a review record. The existing approval command re-runs quality,
binds policy/media choices, and can participate in an approval quorum. A comment or negative
decision therefore cannot be mistaken for authorization to create a handoff.

## JSON contract

`samsarix-campaign schema --kind plan-review` emits the bundled Draft 2020-12 schema. A normalized
record has this shape:

```json
{
  "schemaVersion": 1,
  "artifactType": "plan-review",
  "reviewId": "scr_0123456789ab",
  "reviewHash": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
  "planId": "scp_0123456789ab",
  "sourceHash": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
  "decision": "request-changes",
  "reviewedBy": "Brand reviewer",
  "reviewedAt": "2026-08-08T15:30:00Z",
  "findings": [
    {
      "message": "The launch claim needs supporting evidence.",
      "item": 1,
      "platform": "linkedin",
      "suggestion": "Link the benchmark or narrow the claim."
    }
  ],
  "note": "Resolve before release-owner approval."
}
```

The illustrative hashes above are shape examples, not a valid generated identity. Runtime loading
recomputes SHA-256 over canonical record content, requires `reviewHash` to match, and derives
`reviewId` from its first twelve hexadecimal characters. This detects accidental or uncoordinated
edits when the verifier and file are trusted; anyone able to rewrite the record can recompute both.

Bounds are part of the contract:

- reviewer labels: 1–120 characters, one line;
- findings: 1–50;
- finding messages and suggestions: 1–1,000 characters each;
- item numbers: 1–100, matching the plan collection bound; creation and verification also
  require the targeted item to exist in the exact plan;
- overall note: 1–500 characters;
- explicit RFC 3339 review time with a known offset; and
- only the five canonical supported platform names.

Unknown fields, unsupported control characters, empty text, malformed identity, hash/content
divergence, a platform without an item, and over-limit collections are rejected.

## Git workflow and retention

A practical repository workflow is:

1. commit the plan and referenced campaigns;
2. preview/check them and request review;
3. commit each generated `plan-review` file without replacing earlier records;
4. revise source in response to `request-changes` or `reject`;
5. use `plan diff` and `plan review verify` to show that old feedback is tied to the prior revision;
6. create fresh feedback or quality-gated approvals for the new revision; and
7. retain review records according to the campaign's confidentiality and audit policy.

Finding text, suggestions, reviewer labels, schedules, campaign links, and media hashes can disclose
private strategy or personal information. Protect review records like campaign source. Do not put
secrets, access tokens, private provider responses, or unnecessary personal data in them.

## Trust boundary and deliberate limits

`reviewedBy` is untrusted descriptive text. The record is not signed and does not authenticate a
person, account, organization, role, device, or time source. `blocking` is a deterministic
interpretation of a current local record, not an authorization policy or persistent workflow lock.
Use protected repository permissions, required pull-request reviews, CODEOWNERS, or a separately
reviewed signature/attestation system when authenticated identity or non-repudiation matters.

The core does not provide threaded discussions, mentions, notifications, deadlines, assignments,
hosted version storage, conflict resolution, automatic feedback resolution, or publisher access.
It does not decide whether a claim is true, a suggestion is good, legal review is sufficient, or a
human actually addressed a finding. Those require human judgment and, where appropriate, external
organizational controls.

The next onboarding milestone is canonical CSV/plan import. Official
[Buffer bulk upload](https://support.buffer.com/article/926-how-to-upload-posts-in-bulk-to-buffer)
and [Planable import](https://help.planable.io/hc/en-us/articles/21715324907804-Import-posts-in-Planable)
workflows confirm that spreadsheet authoring is a separate high-value workflow; it should not be
conflated with immutable feedback evidence or weaken the JSON source-of-truth contract.
