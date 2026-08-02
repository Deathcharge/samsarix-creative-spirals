# Security policy

## Supported versions

The latest `0.7.x` release line is supported. Earlier pre-productization and
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
  links, hashtags, and control characters;
- constrains limit overrides so hard platform ceilings cannot be raised, except for Mastodon's
  documented instance-specific maximum;
- evaluates quality gates deterministically without writing files or contacting platforms;
- confines plan campaign references beneath the plan directory and rejects absolute, parent,
  backslash, drive-qualified, and symbolic-link escape paths;
- generates output names instead of trusting configuration as a filesystem path;
- refuses implicit replacement of existing bundles and symbolic-link targets;
- prefixes text fields that begin with common spreadsheet formula markers in CSV exports so
  spreadsheet applications treat them as text;
- binds campaign approvals to the normalized campaign SHA-256 and plan approvals to the normalized
  plan plus every referenced campaign, then re-runs the recorded quality policy during verification;
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
files as potentially sensitive content, review drafts before pasting them into a
platform, and do not commit private drafts or secrets.
Consumers that require byte-for-byte source content should use the manifest and campaign source
rather than stripping the CSV protection.

Campaign and plan approval records do not prove reviewer identity. `approvedBy` is untrusted text,
the files are not signed, and anyone with filesystem write access can replace source or approval
data. Use Git permissions and protected review workflows, or a separately reviewed signing system,
when authenticated authorization or non-repudiation is required.
