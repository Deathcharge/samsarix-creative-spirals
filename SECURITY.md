# Security policy

## Supported versions

The latest `0.12.x` release line is supported. Earlier pre-productization and
Helix-branded snapshots are not supported.

## Reporting a vulnerability

Email `support@samsarix.com` with the subject `Samsarix Creative Spirals security
report`, or use GitHub's private vulnerability reporting flow if it is enabled.
Do not place exploit details, secrets, or private campaign content in a public
issue.

Include the affected version, operating system, minimal reproduction, impact,
and any proposed mitigation. Samsarix LLC does not currently promise a response
time SLA.

## Security and privacy boundary

Samsarix Creative Spirals reads local UTF-8 JSON and writes local Markdown, JSON, CSV, and iCalendar
files selected by the invoking user. The supported workflow:

- performs no network requests, subprocess execution, dynamic imports, telemetry,
  account access, or remote publishing;
- limits campaign files to 1 MiB and individual body text to 100,000 characters;
- rejects duplicate JSON fields and excessive nesting before validating allowed fields, platforms,
  complete per-platform content variants, links, hashtags, and control characters;
- bounds source-controlled link tracking to 20 lowercase parameter names and 200-character
  values, rejects existing-name collisions, percent-encodes values, and caps tracked URLs at
  2,000 characters without opening them;
- constrains limit overrides so hard platform ceilings cannot be raised, except for Mastodon's
  documented instance-specific maximum;
- evaluates quality gates deterministically without writing files or contacting platforms;
- limits portable content policies to 50 literal phrase rules of at most 200 characters, rejects
  unknown/duplicate rule identity and unsupported controls, and does not execute regex or models;
- confines plan campaign references beneath the plan directory and rejects absolute, parent,
  backslash, drive-qualified, and symbolic-link escape paths;
- generates output names instead of trusting configuration as a filesystem path;
- refuses implicit replacement of existing bundles and symbolic-link targets;
- prefixes text fields that begin with common spreadsheet formula markers in CSV exports so
  spreadsheet applications treat them as text;
- binds campaign approvals to the normalized campaign SHA-256 and plan approvals to the normalized
  plan plus every referenced campaign, optionally binds the normalized external content-policy
  SHA-256, then requires and re-runs that exact policy during verification;
- creates approved handoff packets exclusively and verifies their current plan/approval identity,
  embedded approval-bound policy, producer version, fixed directory shape, exact regenerated
  bytes, declared sizes and SHA-256 values, regular-file types, and file stability during reads;
- creates readiness HTML exclusively, escapes all campaign-controlled text, includes no scripts or
  remote resources, and applies restrictive CSP and no-referrer metadata;
- validates bounded campaign-relative JPEG/PNG path metadata, required alt text, target platforms,
  and case-insensitive uniqueness without resolving or opening a referenced file;
- writes exact campaign text to deterministic adapter JSON without executing, transmitting, or
  automatically logging that content.

Media references are not evidence that a file exists, remains beneath a directory after symbolic
link resolution, has the claimed format, is non-malicious, fits a provider limit, or is authorized
for upload. The core never reads those files. Any external adapter that does must use a trusted
source root, resolve links and enforce containment, bound reads, inspect actual content, revalidate
current provider/account rules, use a race-safe open or revalidate and process the same opened
handle, and obtain explicit operator authorization as described in `docs/MEDIA.md`.

The tool runs with the invoking user's filesystem permissions. Treat campaign
and content-policy files as potentially sensitive content, review drafts before pasting them into a
platform, and do not commit private drafts or secrets.
Consumers that require byte-for-byte source content should use the manifest and campaign source
rather than stripping the CSV protection.

Campaign and plan approval records do not prove reviewer identity. `approvedBy` is untrusted text,
the files are not signed, and anyone with filesystem write access can replace source or approval
data. Use Git permissions and protected review workflows, or a separately reviewed signing system,
when authenticated authorization or non-repudiation is required.

Content policies perform literal substring checks on final rendered `PlatformDraft.content` only.
They do not understand meaning, context, spelling variants, images, media alt text, facts, laws, or
provider rules, and they cannot prove a post is safe or compliant. Rule phrases may disclose
embargo markers, required legal language, or other internal policy; protect them like campaign
source. Policy IDs and SHA-256 bindings detect omission/substitution only when the verifier and
evidence are trusted—they are not signatures.

Link-tracking parameters are public URL content, not a secret store. Never place access tokens,
credentials, email addresses, user identifiers, or other personal data in them. The core does not
open destinations, follow redirects, shorten links, collect clicks, load analytics code, or prove
that a destination retains or reports parameters. A downstream publisher or redirect can still
rewrite the reviewed URL; verify that boundary separately.

Approved handoff hashes are also unsigned. They detect stale source and accidental or
uncoordinated file modification when checked with a trusted verifier, but do not authenticate the
reviewer, producer, or repository. Verify immediately before using files from the same directory;
use protected storage or a separately reviewed signature/attestation system when authenticated
provenance is required. See `docs/HANDOFFS.md` for the complete threat model.

Readiness JSON and HTML are point-in-time observations, not authenticated workflow state or proof
of publication. HTML reports contain complete draft content, intended times, links, media metadata,
and evidence status; protect them with the same controls as campaign source. Browser extensions,
file synchronization, and local viewers remain outside the report's no-network boundary.
