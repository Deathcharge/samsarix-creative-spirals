# Evaluate a local campaign workflow

This guide is for a creator, release operator, or small team evaluating Samsarix without an account,
another repository, or private source. Use Python 3.10+ with the package installed as described in
the README. `plan init` is available in 0.19.0 and later.

## Start an editable plan

```bash
samsarix-campaign plan init my-release --platform x --platform linkedin
samsarix-campaign plan preview my-release/plan.json
samsarix-campaign plan check my-release/plan.json
```

The new directory contains only ordinary editable source:

```text
my-release/
  plan.json
  campaigns/
    001-announcement.json
    002-follow-up.json
```

The plan requires every selected channel in both items. Omit `--platform` to use all five supported
channels. Repeated, unknown, empty, or excessive platform lists are rejected rather than silently
deduplicated. Platforms normalize to canonical order. `--name` changes the plan's display name,
not its filenames or sample copy. Edit both campaign files and replace the `example.com` links
before using this as real content. Passing a quality check is not editorial approval.

No intended times are assigned by default. When you know the announcement time:

```bash
samsarix-campaign plan init dated-release --name "September release" \
  --platform x --platform linkedin --start-at 2030-09-10T09:00:00-04:00
```

The follow-up is exactly 48 elapsed hours later after normalization to UTC. It is not a local-time
recurrence, so daylight-saving transitions do not preserve wall-clock time. Edit `intendedAt` in
`plan.json` to choose other times. An explicit offset is required; an unknown `-00:00` offset,
invalid date, or overflow is an error. Nothing is scheduled or sent remotely.

Creation uses the same staged, reloaded, exclusively reserved source export as CSV import.
An existing destination is never merged or overwritten. Pick a new directory if a previous
evaluation exists. `--json` returns `path` (the absolute plan filename), `planId`, `items`,
`requiredPlatforms`, and `scheduled`. Invalid options/I/O return `1`; CLI argument errors return `2`.

## Reproduce the entire technical journey

The source archive includes `examples/evaluate_release.py`; the release also attaches it separately
for wheel-only users. Review the script, then run it with the same Python environment that contains
the installed package:

```bash
# From the source archive or checkout:
python examples/evaluate_release.py --output evaluation-run

# Or, after downloading the attached script beside your terminal:
python evaluate_release.py --output evaluation-run
```

The runner needs only the installed CLI. It does not read checkout campaign examples. It:

1. Creates a fresh two-campaign plan and checks all ten generated drafts.
2. Creates explicitly simulated review metadata.
3. Changes sample copy, verifies that the approval becomes stale (exit `4`), restores the sample,
   and verifies the original approval again.
4. Creates and verifies the exact handoff.
5. Initializes a pending ledger and verifies its expected incomplete exit `4`.
6. Records ten simulated skips into separate snapshots. Nothing is actually published.
7. Verifies completion and saves a script-free offline readiness board plus `evaluation.json`.

All dates are fixed and passed explicitly, so the dry run does not depend on wall clock or local
timezone. Its synthetic dates, reviewer labels, and outcomes are not real operational evidence.
The report says `synthetic-offline-evaluation`, `providerActions: 0`, and `publication-complete`;
the last field means only that every simulated record was intentionally skipped.

The helper invokes the installed CLI as subprocesses, bounded to 30 seconds each. This is an
evaluation script, not a new subprocess/network capability in the core library. Failed steps
exit nonzero and keep the directory for diagnosis; the script never deletes a run or reuses an
existing destination. Inspect `evaluation.json`, `readiness.html`, source files, and immutable
evidence snapshots. A repeated command on the same directory must fail without modifying it.

## A small real-user pilot

Automated success is not adoption evidence. With a consenting evaluator, use a non-sensitive
announcement they actually need to prepare. Do not auto-send invitations or collect telemetry.
Ask the evaluator to:

1. Install in a fresh environment and create a plan without cloning another Samsarix repository.
2. Replace sample copy/links and remove channels they do not need.
3. Preview, correct a quality issue if present, and inspect both campaigns.
4. Have a reviewer inspect the actual copy, then create approval and handoff evidence.
5. Change the copy once and notice that the prior evidence is stale; review the new revision and
   create new evidence rather than silently editing old approvals.
6. Record an intentional skip or a genuinely observed downstream outcome, then interpret status.

Use the full workflow guide for commands beyond initialization. Do not publish real content merely
to complete a pilot. Record the following locally, with the evaluator's consent:

| Observation | Record without private drafts or credentials |
| --- | --- |
| Environment | OS, Python/package version, installation method |
| Scenario | Generic role, chosen channels, and intended output |
| Setup | Completed unaided, needed help, or stopped; exact failing command if any |
| Review/handoff | What was confusing; whether source changes were understood |
| Reconciliation | Whether pending, failed, skipped, and published meanings were clear |
| Time/friction | Observed elapsed time and manual steps, not invented benchmarks |
| Follow-through | Whether they chose to use it again; what they used instead and why |

Redact account names, post URLs, local usernames, private claims, and screenshots before sharing.
The evaluator can choose to send sanitized feedback to `support@samsarix.com` or file an issue.
No feedback is uploaded automatically. Record sample size and context; one successful pilot does
not establish market fit, regulatory suitability, authenticated approval, or provider reliability.

## Current design evidence

As checked on 2026-08-31, Buffer documents template-based authoring and CSV-to-draft workflows,
and Postiz exposes a draft state separate from immediate publishing. These support lowering
first-use authoring friction, not claims that Samsarix has acquired users:
[Buffer templates](https://support.buffer.com/en-us/articles/using-templates-in-buffer-Gbn93vR56i),
[Buffer bulk import](https://support.buffer.com/en-us/articles/how-to-upload-posts-in-bulk-to-buffer-cTIhl4mv6H),
and [Postiz draft creation](https://docs.postiz.com/public-api/posts/create).

Samsarix supplies local sources and inspectable evidence, not connected-account storage, a queue,
analytics, or a remote publisher. The starter and runner are freely inspectable MPL-2.0 material.
