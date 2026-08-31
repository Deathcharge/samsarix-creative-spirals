# Publication ledgers

A publication ledger is a local JSON sidecar for reconciling every platform draft after an
approved handoff. It answers: **what outcome did an operator record for each exact draft?** It
does not connect to a platform or claim that a post is live.

## Why this workflow exists

Connected publishing tools retain post-handoff history, but their own documentation shows why a
local record must use careful language:

- Buffer's **Sent** history retains posts, author labels, sent times, and channel metrics, including
  posts later deleted from Buffer. Buffer also documents notification publishing where an item can
  move to **Sent** after a reminder is delivered even though a person must still finish publishing
  in the native app: [Sent history](https://support.buffer.com/article/517-understanding-sent-post-metrics-within-buffer-publish)
  and [notification publishing](https://support.buffer.com/article/658-using-notification-publishing).
- Sprout Social's Publishing Calendar exposes Scheduled, Queued, and Sent states. It can also pull
  successfully published native or third-party messages into the calendar, while some externally
  published activity has no author information:
  [Publishing Calendar](https://support.sproutsocial.com/hc/en-us/articles/360000121343-How-do-I-use-the-Publishing-Calendar)
  and [calendar troubleshooting](https://support.sproutsocial.com/hc/en-us/articles/38373940164877-Troubleshooting-Sprout-Social-Publishing-Calendar-Issues).

Samsarix cannot make those provider-side observations because it has no accounts, tokens, or
network client. Its defensible counterpart is a Git-friendly operator assertion bound to the exact
approved handoff. A URL is useful reconciliation metadata, not remote verification.

## Workflow

Create and verify the approved handoff first, then initialize a ledger:

```bash
samsarix-campaign plan publication init \
  examples/launch-plan.json \
  handoff-outbox/local-first-release-sequence-sch_0123456789ab \
  --output launch-plan.publication.json
```

Initialization verifies the current plan, embedded approval, optional embedded policy, handoff
metadata, and exact packet bytes. It then writes one `pending` record for every generated
`(sequence, platform)` pair. Existing ledger files are never replaced.

After the manual or separately authorized downstream step, record an outcome in a new snapshot:

```bash
samsarix-campaign plan publication record \
  examples/launch-plan.json \
  handoff-outbox/local-first-release-sequence-sch_0123456789ab \
  launch-plan.publication.json \
  --item 1 --platform mastodon --status published --by "Release operator" \
  --at 2026-08-10T13:04:00Z --url https://social.example/@samsarix/123 \
  --output launch-plan.publication-1.json
```

Use the new snapshot as input for the next outcome, selecting its one-based plan item and exact
platform. Supply the actual handoff directory returned by `plan handoff create`, not the example
ID above. The outcome timestamp is explicit; `--assessed-at` optionally pins verification time
for deterministic replay (default: current UTC time).

The result contains this record; manual authoring of the v1 JSON contract remains supported:

```json
{
  "sequence": 1,
  "campaignId": "scs_0123456789ab",
  "platform": "mastodon",
  "status": "published",
  "recordedBy": "Release operator",
  "occurredAt": "2026-08-10T13:04:00Z",
  "url": "https://social.example/@samsarix/123"
}
```

Use `skipped` when a channel was intentionally omitted and `failed` when an attempt needs follow-up:

```json
{
  "sequence": 2,
  "campaignId": "scs_abcdef012345",
  "platform": "discord",
  "status": "skipped",
  "recordedBy": "Release operator",
  "occurredAt": "2026-08-10T13:10:00Z",
  "note": "Community announcement deferred to the next release."
}
```

Verify the complete record and optionally require it in consolidated status:

```bash
samsarix-campaign plan publication verify \
  examples/launch-plan.json \
  handoff-outbox/local-first-release-sequence-sch_0123456789ab \
  launch-plan.publication-1.json

samsarix-campaign plan status examples/launch-plan.json \
  --handoff handoff-outbox/local-first-release-sequence-sch_0123456789ab \
  --publication launch-plan.publication-1.json \
  --require-stage publication \
  --json
```

`publication verify` returns `0` only when the ledger is current and every record is `published`
or `skipped`. It returns `4` for a current but pending/failed ledger or for stale bindings and
chronology. Malformed JSON, invalid record combinations, I/O failures, and invalid URLs return `1`.

## Recording, retrying, and correcting outcomes

The `record` command verifies current source, exact handoff bytes, ledger coverage, and chronology
before making a change. It validates the resulting ledger again before writing. A current ledger
may still contain pending or failed outcomes; those do not prevent recording other outcomes.

- Pending records may become published, failed, or skipped.
- Failed attempts may be recorded again or retried as published/skipped. A retry never inherits
  the previous note or URL; supply the full new outcome.
- Changing a published or skipped outcome requires `--replace-outcome`. This can record a
  correction as any of the three outcome states; it does not delete or retry anything remotely.
- Repeating an identical normalized outcome is idempotent: the publication ID stays unchanged and
  no replacement flag is needed. An explicitly requested new output file is still created.
- Retry/correction times must not precede the previous recorded outcome. All times must remain
  between handoff generation and the assessment time. An outcome may precede ledger creation
  when recording a historical downstream action.
- There is no reset-to-pending command. A changed campaign requires a new approval/handoff and
  ledger, not an attempt to carry forward stale outcomes.

For example, record a failure, then a later successful retry using the failed snapshot:

```bash
samsarix-campaign plan publication record PLAN HANDOFF pending.json \
  --item 1 --platform x --status failed --by "Release operator" \
  --at 2026-08-10T13:00:00Z --note "Provider unavailable; no post confirmed." \
  --output failed.json
samsarix-campaign plan publication record PLAN HANDOFF failed.json \
  --item 1 --platform x --status published --by "Release operator" \
  --at 2026-08-10T13:05:00Z --url https://social.example/post/123 \
  --output retried.json
```

Replace `PLAN` and `HANDOFF` with your current source and verified packet paths. `--output` is
required and exclusive: existing files, including the input, are never replaced. Commit snapshots
to Git or apply your own retention policy if you need history. Snapshots are not linked, signed,
authenticated, or append-only; concurrent operators can produce divergent snapshots, and the
command does not infer which file is latest or merge them. Use repository review to choose one
input for the next step. A supplied `--policy` must match the handoff's embedded content policy.

`record` returns `0` for a saved valid snapshot, even for a failed outcome or an incomplete ledger;
it is not a completion gate. It returns `1` for validation/I/O errors and `2` for invalid CLI
arguments. `--json` returns `path`, `previousPublicationId`, `publicationId`, and the full
`publication` v1 object. Use `verify` or readiness for completion gating.

### Current workflow evidence (2026-08-31)

Buffer documents explicit retries after channel refresh and warns that a failed status can require
checking the native platform before attempting another post. Postiz's authenticated post-list API
exposes release URLs. These establish practical reconciliation needs, not evidence of Samsarix
adoption: [Buffer retry guidance](https://support.buffer.com/en-us/articles/refreshing-a-channel-in-buffer-7oDS4jk7l1),
[failure caveats](https://support.buffer.com/en-us/articles/facebook-error-library-x7IMglwe8J),
and [Postiz post list](https://docs.postiz.com/public-api/posts/list).

Samsarix's corresponding workflow is deliberately an offline operator record. Saving `published`
does not inspect the URL, retry the provider, resolve ambiguous delivery, or prevent duplicate
remote posts. Check the actual platform before a separately authorized retry.

## Contract

The top-level `plan-publication` v1 record binds:

- the current `planId` and full normalized `sourceHash`;
- the exact `handoffId` and full `handoffHash`;
- a timezone-aware `createdAt`; and
- 1–500 ordered outcome records, matching the canonical plan/draft order exactly.

The verifier derives `scpub_*` and a full SHA-256 from canonical ledger JSON. The ID changes when
any outcome metadata changes; it is not embedded, so a human never has to update a self-hash.

Record states are strict:

| Status | Required outcome fields | Meaning for completion |
|---|---|---|
| `pending` | none | incomplete |
| `published` | `recordedBy`, `occurredAt`, absolute HTTP(S) `url` | complete for that draft |
| `failed` | `recordedBy`, `occurredAt`, `note` | incomplete; retry or deliberately skip |
| `skipped` | `recordedBy`, `occurredAt`, `note` | complete for that draft |

Outcome times cannot precede handoff generation or be later than the explicit/current assessment
time. URLs are limited to 2,000 characters, must use HTTP(S), and cannot contain credentials,
whitespace, or controls. They are never opened, resolved, shortened, or restricted to centralized
platform hostnames; federated services legitimately use many domains.

Print the bundled Draft 2020-12 authoring schema with:

```bash
samsarix-campaign schema --kind publication
```

Runtime verification additionally enforces exact current-plan coverage and chronology that a
standalone JSON Schema cannot establish.

## Readiness integration

Supplying both `--handoff` and `--publication` adds three post-handoff stages:

- `publication-invalid`: the ledger is stale, misbound, incomplete in shape, or chronologically
  impossible;
- `publication-in-progress`: bindings and coverage are current, but at least one record is pending
  or failed; and
- `publication-complete`: every exact draft is recorded as published or intentionally skipped.

`ready` remains true for a verified handoff in both current publication progress states because
the downstream handoff and ledger binding are valid. Invalid publication evidence sets it false.
Only `publication-complete` satisfies
`--require-stage publication`. Once current publication evidence is supplied, past intended times
remain visible as schedule findings but do not mask the post-handoff stage.

Readiness v1 adds `publicationStatus`, `publicationId`, and `publicationCounts` only when a ledger
is supplied. Existing reports without publication evidence retain their prior shape and stages.

## Trust, privacy, and retention

- `recordedBy` is a label, not an authenticated user. Anyone who can edit the file can forge or
  replace it.
- A syntactically valid URL is not evidence that the content was accepted, visible to the intended
  audience, unchanged, still live, or authored by the named operator.
- `failed` notes can contain provider diagnostics; do not put tokens, cookies, private messages,
  or unnecessary personal data in them.
- Ledger files reveal campaign identity, channels, timing, operator labels, live URLs, and failure
  context. Protect and retain them according to the campaign's sensitivity.
- Hashes detect changes only when the source, handoff, ledger, and verifier are obtained through a
  trusted process. They are not signatures or non-repudiation.
- Verification performs no DNS lookup or HTTP request and has zero provider/API operating cost.

Use protected repository review or a separately designed signed-attestation system when
authenticated identity or durable compliance evidence is required. Use provider exports or API
evidence when the question is whether content actually exists remotely.
