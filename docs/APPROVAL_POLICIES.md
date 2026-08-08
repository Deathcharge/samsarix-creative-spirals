# Approval policies and quorum evidence

Samsarix Creative Spirals 0.15 can require several independently created plan approvals before a
handoff is accepted. A reusable approval policy names the required review roles and minimums; a
deterministic approval set assigns existing source-bound approvals to those roles.

This is useful when one release needs separate brand, legal, accessibility, regional, or release
owner review without introducing a hosted account system. It remains a local, Git-native evidence
workflow: the roles and reviewer labels are descriptive text, not authenticated identities.

## Why this workflow exists

Current collaboration products make approval routing a first-class operation:

- [Buffer's official approval workflow](https://support.buffer.com/article/665-managing-and-approving-draft-posts)
  separates posting roles and routes drafts to an approver before scheduling.
- [Planable](https://planable.io/product/) advertises dedicated approval workflows,
  approval-only permissions, stakeholders, comments, and external approvers.
- Sprout Social documents both
  [message approval workflows](https://support.sproutsocial.com/hc/en-us/articles/205974715-Message-Approval-Workflows)
  and an
  [external approvers workflow](https://support.sproutsocial.com/hc/en-us/articles/9385327882125-How-do-I-enable-the-External-Approvers-workflow).
- GitHub supports a
  [required number of approving reviews](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)
  and optional
  [code-owner review](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners).

Those systems can authenticate users and maintain shared server state. Samsarix implements the
portable artifact portion: every reviewer approves the same exact local plan separately, and the
resulting set proves that a declared role/count policy is satisfied when checked with a trusted
copy of this package and protected repository history.

## Policy format

[`examples/approval-policy.json`](../examples/approval-policy.json) requires one brand review and
one release-owner review:

```json
{
  "schemaVersion": 1,
  "name": "Launch approval quorum",
  "minimumTotal": 2,
  "distinctReviewers": true,
  "requirements": [
    {"role": "brand", "minimum": 1},
    {"role": "release-owner", "minimum": 1}
  ]
}
```

Roles use lowercase kebab case. A policy contains 1–20 unique roles, each minimum is 1–50, the
sum of role minimums cannot exceed 50, and a completed set contains 1–50 approvals. `minimumTotal`
can require additional review beyond the per-role minimums. With `distinctReviewers: true`, the
case-insensitive `approvedBy` labels must differ across the complete set.

The normalized policy has a full SHA-256 `source_hash` and derived `scap_*` `policy_id` in the
Python API. The complete normalized policy is embedded in an approval set and therefore covered by
the set hash; substituting policy rules changes the set identity.

Print the bundled authoring schema with:

```bash
samsarix-campaign schema --kind approval-policy
```

## Complete CLI workflow

Each reviewer creates an ordinary plan approval. The approvals must bind the same exact plan,
source hash, warning policy, content policy, and optional exact-media snapshot:

```bash
samsarix-campaign plan approval create examples/launch-plan.json \
  --by "Brand reviewer" \
  --policy examples/content-policy.json \
  --output brand.approval.json

samsarix-campaign plan approval create examples/launch-plan.json \
  --by "Release owner" \
  --policy examples/content-policy.json \
  --output release-owner.approval.json
```

Assign each approval to one declared role and collect the quorum:

```bash
samsarix-campaign plan approval collect examples/launch-plan.json \
  --approval-policy examples/approval-policy.json \
  --approval brand=brand.approval.json \
  --approval release-owner=release-owner.approval.json \
  --policy examples/content-policy.json \
  --output launch-plan.approval-set.json
```

Collection refuses an undeclared role, a missing role/count, a duplicate approval record, reused
reviewer labels when distinct labels are required, stale source, failed quality policy, or mixed
content-policy/media bindings. Input order does not affect the canonical set.

Verify and hand off the set through the same commands used for legacy single approval evidence:

```bash
samsarix-campaign plan approval verify \
  examples/launch-plan.json launch-plan.approval-set.json \
  --policy examples/content-policy.json

samsarix-campaign plan handoff create \
  examples/launch-plan.json launch-plan.approval-set.json \
  --policy examples/content-policy.json \
  --output handoff-outbox
```

`plan status --approval launch-plan.approval-set.json` also verifies the set. A handoff continues
to use the fixed `approval.json` packet path; that file may contain either a legacy single plan
approval or the new `artifactType: "plan-approval-set"` document. Publication initialization and
verification work unchanged against a handoff containing either form.

For exact image review, every reviewer must create their approval with `--include-media`. The
collector re-collects and checks the same snapshot, and the handoff packages those exact bytes as
described in [MEDIA.md](MEDIA.md).

Print the completed-evidence schema with:

```bash
samsarix-campaign schema --kind plan-approval-set
```

## Determinism and invalidation

The `scas_*` approval-set identity covers the normalized policy, exact role assignments, and every
embedded approval. Assignments are normalized by role, approval time, and case-insensitive reviewer
label. Every embedded approval is still independently verified against current plan source and the
selected aggregate quality policy.

The set becomes invalid when, among other things:

- the plan, ordering, schedule, required platforms, or any referenced campaign changes;
- a bound content policy changes or is omitted;
- exact media changes, disappears, or is not supplied for verification;
- an embedded approval or role assignment is edited;
- the policy, its minimums, or its distinct-reviewer rule is edited; or
- the set identity does not match its canonical content.

Create new approvals and a new set after a material change. Do not edit approval evidence in
place.

## Trust and security boundary

`approvedBy` and role names are unsigned, unauthenticated labels. `distinctReviewers` compares
those labels after Unicode normalization and case folding; it does not prove that two humans,
accounts, organizations, or devices participated. Anyone who can replace the source, policy,
approvals, set, and expected verifier can construct a different internally consistent history.

Use repository permissions, protected branches, required pull-request reviews, and CODEOWNERS when
authenticated organizational enforcement is needed. For higher assurance, add a separately
reviewed signature or attestation over the complete source and evidence. Samsarix itself does not
load credentials, query Git history, contact reviewers, send notifications, or claim authorization
or non-repudiation.

Approval files can contain reviewer labels, notes, exact draft identity, policy names, and media
metadata. Treat them as sensitive campaign records. The workflow performs bounded local JSON and
optional image reads only; it makes no network request.

## Compatibility

This is additive before 1.0. Existing single plan approvals retain their schema and behavior.
`plan approval verify`, handoff creation/verification, readiness, and publication accept both
evidence forms. The handoff manifest shape and fixed `approval.json` filename do not change. New
consumers can distinguish a set by `artifactType: "plan-approval-set"`; old consumers that parse
only `artifactType: "plan"` should continue using single approvals or upgrade before receiving a
set.
