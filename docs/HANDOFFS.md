# Approved handoff packets

An approved handoff packet is the last local-first boundary before a person or separately
permissioned adapter imports campaign drafts into a publisher. It packages the current plan,
embedded approval record, exact rendered outputs, and bounded integrity metadata in one exclusive
directory.

The packet answers four offline questions:

1. Does the embedded approval still match the current plan and every referenced campaign?
2. Was the packet generated at or after that approval?
3. Does every expected file still have the exact current rendered bytes?
4. Does the directory contain any missing, substituted, or unexpected deliverable?

It does not answer who approved or produced the packet. The hashes are unsigned integrity and
current-source checks, not authenticated provenance, a digital signature, authorization, or
non-repudiation.

## Workflow

Run plan review and the aggregate quality gate, create an approval, then create the handoff:

```bash
samsarix-campaign plan diff launch-plan-before.json examples/launch-plan.json
samsarix-campaign plan check examples/launch-plan.json
samsarix-campaign plan approval create examples/launch-plan.json \
  --by "Launch reviewer" \
  --output launch-plan.approval.json
samsarix-campaign plan handoff create \
  examples/launch-plan.json \
  launch-plan.approval.json \
  --output handoff-outbox
```

The create command refuses a stale approval, a plan that no longer passes the recorded quality
policy, a generation time before the approval time, a symbolic-link output root, a non-directory
output root, or an existing packet identity. It creates the packet in a private temporary
directory and renames that directory into place only after every file is written.

Verify immediately before import, copy, or manual publication:

```bash
samsarix-campaign plan handoff verify \
  examples/launch-plan.json \
  handoff-outbox/release-sequence-sch_0123456789ab
```

Use `--json` for automation. Verification returns `0` only when the packet is current and intact,
`4` for a well-formed but invalid packet, `1` for malformed input or I/O failure, and `2` for CLI
usage errors.

## Packet contract

Each packet has a generated name ending in its `sch_*` handoff ID:

```text
handoff-outbox/
└── release-sequence-sch_0123456789ab/
    ├── handoff.json
    ├── approval.json
    ├── manifest.json
    ├── adapter.json
    ├── calendar.ics
    └── csv/
        ├── x.csv
        ├── linkedin.csv
        └── discord.csv
```

`handoff.json` uses handoff schema version 1. Print the bundled Draft 2020-12 schema with:

```bash
samsarix-campaign schema --kind handoff
```

Its `artifacts` object declares each plan-export file and the embedded `approval.json` by fixed,
packet-relative path, exact byte length, and lowercase SHA-256. The manifest also contains the full
plan source hash, plan ID, UTC generation time, producer name/version, a full `handoffHash`, and an
`sch_*` ID derived from that hash. The hash covers canonical handoff metadata and all artifact
descriptors; it intentionally excludes itself and its shortened ID.

The verifier:

- reloads current plan source and re-runs the approval's recorded aggregate quality policy;
- checks current plan ID and full source hash, including order, schedule, required channels,
  source paths, media metadata, and every referenced campaign;
- regenerates adapter JSON, calendar, plan manifest, and platform CSV bytes with the recorded
  generation time and current producer version;
- verifies the embedded approval bytes, every declared size and checksum, canonical on-disk
  `handoff.json`, fixed root/CSV directory shape, and absence of extra entries;
- refuses symbolic-link artifacts and non-regular files and detects file identity, size, or
  modification-time changes during a verification read.

Packets from another package version intentionally fail with `producer-version-changed`, because
the current verifier cannot promise byte-identical rendering across implementation versions. Keep
the producing wheel or version pin with long-lived evidence.

## Downstream adapter rule

A publisher adapter should accept only a successful verification result and use files from the
same verified packet directory. It must still implement provider authentication, account and
workspace selection, authorization, idempotency, media containment/content checks, current
provider limits, retry behavior, and an explicit operator decision to queue or publish. The core
package does none of those things.

Do not edit a packet in place. Revise source, review the semantic diff, create a new approval when
needed, and create a new packet. Packet creation has no overwrite flag so prior evidence remains
available for comparison.

## Why this boundary exists

Connected tools commonly move approved drafts toward a publishing queue: Buffer documents that
approved drafts move to the queue or schedule, and that full posting access is required to move
drafts there ([draft approval](https://support.buffer.com/article/665-managing-and-approving-draft-posts),
[draft scheduling](https://support.buffer.com/article/656-saving-and-scheduling-draft-posts)).
Samsarix provides a credential-free counterpart: a verified file boundary that an operator can
hand to any chosen downstream system.

GitHub's artifact attestations are a useful contrast. They are cryptographically signed claims,
and meaningful verification includes the signature, timestamp, and signer identity
([concepts](https://docs.github.com/en/actions/concepts/security/artifact-attestations),
[verification warning](https://docs.github.com/en/rest/repos/attestations)). Samsarix handoff
hashes provide no such identity. If authenticated provenance is required, protect source and
approvals with repository controls or add a separately reviewed signing/attestation layer over the
complete packet.

## Limits and retention

- Anyone who can replace the plan, approval, packet, and expected verifier can construct another
  internally consistent packet. Store evidence in a protected repository or immutable archive
  appropriate to the risk.
- SHA-256 detects accidental or uncoordinated modification; it does not authenticate the person
  named in `approvedBy` or the machine that generated the packet.
- Verification is local and point-in-time. A downstream consumer must minimize the gap between
  verify and use and apply its own race-safe file-opening controls when the directory is shared
  with an untrusted writer.
- Media paths remain metadata. Media bytes are not included, opened, checked, or uploaded by the
  core package; follow [MEDIA.md](MEDIA.md) before dereferencing them.
- The calendar records intent and the CSV/adapter files carry drafts. No file schedules or
  publishes a post by itself.
