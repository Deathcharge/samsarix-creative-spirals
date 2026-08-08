# Plan review and approval

Campaign approval protects one piece of source copy. A launch can still change materially when a
campaign is added, removed, reordered, rescheduled, retargeted to different required platforms, or
edited through its referenced file. Plan review closes that gap without adding accounts, a hosted
workflow, or publishing authority.

## Review workflow

Compare the previously accepted plan to the proposed plan:

```bash
samsarix-campaign plan diff launch-plan-before.json launch-plan.json
samsarix-campaign plan diff launch-plan-before.json launch-plan.json --json --exit-code
```

The first form is informational. `--exit-code` returns `4` when semantic changes exist, which makes
an explicit review decision easy to require in CI. Equivalent normalized spelling, such as the
same RFC 3339 instant expressed with another offset, does not create noise.

If a reviewer has comments or cannot approve the current revision, create an immutable `plan-review`
record with `comment`, `request-changes`, or `reject`. Its findings bind to the exact plan/source
and can optionally bind exact image bytes. Positive authorization remains in the approval contract.
See [`PLAN_FEEDBACK.md`](PLAN_FEEDBACK.md).

After the aggregate quality gate and human review pass, create a new approval record:

```bash
samsarix-campaign plan check launch-plan.json
samsarix-campaign plan approval create launch-plan.json \
  --by "Launch reviewer" \
  --note "Schedule, channel coverage, and final copy reviewed"
samsarix-campaign plan approval verify \
  launch-plan.json launch-plan.json.approval.json
```

Pass `--warnings-as-errors` during creation when duplicate times, out-of-order scheduled items, or
campaign review warnings must block approval. The selected policy is stored and re-run during
every verification. Existing approval files are never overwritten.

When the review includes the exact referenced image bytes, add `--include-media` during creation.
The approval then binds a bounded content-addressed `scm_*` snapshot. Later approval verification
automatically re-collects the current files, and handoff creation packages them only if they still
match. See [`MEDIA.md`](MEDIA.md).

When the plan is governed by a portable content policy, pass the same `--policy POLICY` to plan
check, approval creation, and every later verification. Approval v1 then includes an optional
`contentPolicy` identity; omission or substitution after review is an explicit invalid result. See
[`POLICIES.md`](POLICIES.md).

## Multi-role review

For separate brand, legal, accessibility, regional, or release-owner review, each reviewer creates
an ordinary approval of the same plan. `plan approval collect` then assigns those records to a
bounded approval policy and emits one deterministic `plan-approval-set` document. The verifier
checks every embedded approval independently; collecting a set cannot turn stale or failed evidence
into valid evidence.

```bash
samsarix-campaign plan approval collect launch-plan.json \
  --approval-policy approval-policy.json \
  --approval brand=brand.approval.json \
  --approval release-owner=release-owner.approval.json \
  --output launch-plan.approval-set.json
```

The completed set is accepted by approval verification, handoff, readiness, and publication flows
without changing the legacy single-approval record. See
[`APPROVAL_POLICIES.md`](APPROVAL_POLICIES.md) for the policy/set schemas, exact-media and
content-policy rules, determinism, limits, and unauthenticated-label boundary.

## Semantic diff contract

JSON output uses `schemaVersion: 1` and includes both plan IDs, both full source hashes, ordered
plan-level `fields`, and ordered `items` changes.

- Plan fields cover `name` and `requiredPlatforms`.
- Items are compared by their one-based sequence position. A reorder is therefore visible as
  modifications at every affected position.
- Item fields cover `source`, normalized `intendedAt`, and `campaign`.
- A changed campaign includes the existing campaign semantic diff, including normalized source,
  generated draft, and media changes.
- Added and removed positions contain compact snapshots with source path, schedule, campaign ID,
  and full campaign source hash.

The output is deterministic and bounded by the plan and campaign input limits. It contains draft
content, so treat saved reports as potentially sensitive release material.

## Approval contract and invalidation

Plan approvals have their own bundled `plan-approval` JSON Schema. This leaves the existing
campaign approval v1 contract compatible and makes artifact type unambiguous.

Each record contains:

- `artifactType: "plan"` and `schemaVersion: 1`;
- the deterministic `scp_*` plan ID and full SHA-256 source hash;
- a normalized reviewer label and UTC review time;
- the `errors-only` or `warnings-as-errors` quality policy;
- an optional normalized external `contentPolicy` ID, full source hash, and name;
- an optional exact-media ID, full hash, reference count, and unique-byte total; and
- an optional review note.

The plan source hash covers normalized plan metadata, ordered source paths, normalized intended
times, and every normalized referenced campaign—including its media metadata. Changing any of
those values invalidates both the hash and plan ID. Verification also re-runs the recorded plan
quality policy, so a matching record cannot bypass a current quality failure.
An exact-media binding is additional to the plan source hash: metadata changes still change plan
identity, while pixel-byte changes invalidate the `scm_*` snapshot even when the path stays the same.

## Trust boundary

This record is review metadata, not a signature or authorization token. `approvedBy` is an
untrusted human-readable label, and anyone with write access can replace source or approval files.
Use repository permissions and protected pull-request review when reviewer identity matters, or
design a separately reviewed signing system.

This boundary follows a well-established workflow pattern while preserving Samsarix's local-first
position:

- [Buffer's official approval workflow](https://support.buffer.com/article/665-managing-and-approving-draft-posts)
  separates contributors who request approval from users who can edit, approve, reject, and
  schedule drafts.
- [Sprout Social's official approval documentation](https://support.sproutsocial.com/hc/en-us/articles/205974715-Message-Approval-Workflows)
  describes multi-step review, approval/rejection, activity, and notifications for outgoing posts.
- [GitHub's protected-branch documentation](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)
  supports required reviews and can dismiss approvals when the reviewed diff changes.

Samsarix implements the portable artifact, multi-role count policy, and stale-state checks. It
deliberately does not implement user accounts, notifications, authenticated role membership,
cryptographic identity, scheduling, or publishing.
