# Portable content policies

Samsarix Creative Spirals 0.11 adds deterministic, repository-owned phrase guardrails to the
existing local quality and approval workflow. A policy is a bounded JSON file that can travel
beside campaign source, be reviewed in Git, and run without an account, API key, database, or
network connection.

Use this feature for exact, known requirements such as:

- preventing unreleased markers such as `internal only` from reaching copy-ready output;
- requiring an exact disclosure, campaign name, support address, or call to action;
- applying a rule only to selected platforms;
- reporting a review warning or blocking the quality gate; and
- proving which normalized policy was used when a campaign or plan was approved.

This is phrase governance, not semantic moderation, fact-checking, legal advice, or a guarantee of
regulatory compliance.

## Why this slice exists

Connected publishing suites demonstrate that approvals and content guardrails are real operating
needs. Sprout documents multi-step outgoing-message approval workflows intended to reduce errant
posts and improve copy review, and added blocked-word handling to approval workflows for
brand-specific governance. Buffer documents role-based draft approval before content moves into a
publishing queue. Sources:

- <https://support.sproutsocial.com/hc/en-us/articles/205974715-Message-Approval-Workflows>
- <https://support.sproutsocial.com/hc/en-us/articles/44013619229965-April-2026>
- <https://support.buffer.com/article/665-managing-and-approving-draft-posts>

Those systems coordinate connected accounts and hosted users. Samsarix occupies an earlier trust
boundary: deterministic checks against the exact rendered drafts, with a portable policy identity
bound into local approval and handoff evidence. It does not reproduce permissions, notifications,
queues, exceptions, or publishing.

## Runnable example

Validate and identify the included policy, then apply it to final platform drafts:

```bash
samsarix-campaign policy validate examples/content-policy.json --json
samsarix-campaign check examples/campaign-variants.json \
  --policy examples/content-policy.json --json
```

Bind the same policy when recording and verifying approval:

```bash
samsarix-campaign approval create examples/campaign-variants.json \
  --policy examples/content-policy.json \
  --by "Release reviewer"

samsarix-campaign approval verify examples/campaign-variants.json \
  examples/campaign-variants.json.approval.json \
  --policy examples/content-policy.json
```

Every plan quality, approval, handoff, and readiness command that evaluates or verifies evidence
also accepts `--policy`. If a plan approval contains `contentPolicy`, the exact current file must be
supplied to approval verification and handoff creation. The resulting handoff embeds normalized
`content-policy.json`, so handoff verification and readiness can use the packet alone. Supplying an
external policy to either remains useful as an additional equality check.

## Version 1 contract

```json
{
  "schemaVersion": 1,
  "name": "Release communications guardrails",
  "rules": [
    {
      "id": "no-internal-markers",
      "kind": "blockedPhrase",
      "phrase": "internal only"
    },
    {
      "id": "disclosure-required",
      "kind": "requiredPhrase",
      "phrase": "#ad",
      "platforms": ["x", "linkedin"],
      "severity": "error",
      "caseSensitive": false
    }
  ]
}
```

| Field | Rules |
| --- | --- |
| `schemaVersion` | Required; must be `1`. |
| `name` | Required single line, 1–120 characters. |
| `rules` | Required; 1–50 rules with unique IDs. |
| `id` | Lowercase stable key matching `[a-z][a-z0-9-]{0,63}`. |
| `kind` | `blockedPhrase` or `requiredPhrase`. |
| `phrase` | Literal, single-line text, 1–200 characters. It is never interpreted as regex. |
| `platforms` | Optional non-empty subset of the five supported platforms; omission targets all. |
| `severity` | Optional `warning` or `error`; defaults to `error`. |
| `caseSensitive` | Optional boolean; defaults to `false`. |

Unknown fields, duplicate JSON keys, duplicate rule IDs, invalid types, excessive nesting, and
files larger than the shared JSON input limit are rejected. Print or write the bundled Draft
2020-12 schema with:

```bash
samsarix-campaign schema --kind content-policy
```

## Exact evaluation semantics

The evaluator inspects each selected `PlatformDraft.content` after platform variants, formatting,
link and hashtag composition, normalization, and any truncation. This is the same copy-ready text
shown by preview and placed in downstream artifacts.

- Matching uses literal substring containment.
- Default matching uses Unicode `casefold`; `caseSensitive: true` uses exact casing.
- One violation is emitted per targeted rendered draft, with stable code
  `policy-blocked-phrase` or `policy-required-phrase` and the rule's `ruleId`.
- Warning rules remain non-blocking unless `--warnings-as-errors` is selected.
- Policy findings do not alter campaign or plan identity because the policy is an external,
  reusable input. Checks expose the policy binding, and approvals bind it separately.
- Media bytes and media alt text are not inspected. Core still treats media as bounded metadata;
  an adapter or human must perform any additional media governance.

Literal rules are intentionally less expressive than regex. That makes runtime cost bounded,
avoids regular-expression denial-of-service behavior, and makes review results easier to explain.

## Policy identity and approval behavior

Normalization fills rule defaults, orders platform targets canonically, normalizes text to NFC,
and serializes keys deterministically. SHA-256 over that representation yields:

```json
{
  "policyId": "scpol_0123456789ab",
  "sourceHash": "0123456789abcdef...64 lowercase hexadecimal characters...",
  "name": "Release communications guardrails"
}
```

`policyId` is a convenient 12-hex display prefix. `sourceHash` is the full comparison identity.
Neither is a signature.

Approval verification follows four explicit cases:

| Approval binding | Current `--policy` | Result |
| --- | --- | --- |
| absent | absent | legacy approval behavior is unchanged |
| present | absent | `content-policy-required` |
| absent | present | `content-policy-unapproved` |
| present | different | `content-policy-changed` |
| present | exact match | policy is re-run with the recorded warning policy |

This prevents a policy from being silently omitted or replaced after review. It does not prevent a
writer who controls both source and unsigned approval files from replacing all evidence. Use
protected repository review or a separately designed signature/attestation system when reviewer
identity and non-repudiation matter.

## Python API

```python
from samsarix_creative_spirals import (
    build_campaign,
    check_campaign,
    create_campaign_approval,
    load_campaign,
    load_content_policy,
)

bundle = build_campaign(load_campaign("campaign.json"))
policy = load_content_policy("content-policy.json")
check = check_campaign(bundle, content_policy=policy)
approval = create_campaign_approval(
    bundle,
    approved_by="Release reviewer",
    content_policy=policy,
)
```

Public immutable types are `ContentPolicy`, `ContentPolicyRule`, and `ContentPolicyBinding`.
`evaluate_content_policy` is available when a caller needs policy findings without the built-in
quality findings. Prefer `check_campaign` or `check_campaign_plan` for normal gates.

## Migration and safe operation

Content policy v1 is additive. Existing campaign, plan, approval, handoff, and readiness files
remain valid when no policy is supplied. Approval schema v1 and plan-approval schema v1 gain only
the optional `contentPolicy` member.

When adopting policies:

1. Commit and review the policy beside campaign sources.
2. Run it against existing copy and choose warning/error severity deliberately.
3. Supply the same path when creating approval.
4. Supply the exact policy when verifying standalone approvals or creating a handoff. Thereafter,
   verify the self-contained packet; optionally supply the repository copy as a cross-check.
5. Treat a policy edit as a new review event even when campaign source did not change.

Policies can contain embargo language, disclosures, campaign names, or other sensitive business
rules. Protect them like campaign source. The package never transmits them.
