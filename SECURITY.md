# Security policy

## Supported versions

The latest `0.2.x` release line is supported. Earlier pre-productization and
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

Samsarix Creative Spirals reads local UTF-8 JSON and writes local Markdown and
JSON files selected by the invoking user. The supported workflow:

- performs no network requests, subprocess execution, dynamic imports, telemetry,
  account access, or remote publishing;
- limits campaign files to 1 MiB and individual body text to 100,000 characters;
- validates allowed fields, platforms, links, hashtags, and control characters;
- generates output names instead of trusting configuration as a filesystem path;
- refuses implicit replacement of existing bundles and symbolic-link targets.

The tool runs with the invoking user's filesystem permissions. Treat campaign
files as potentially sensitive content, review drafts before pasting them into a
platform, and do not commit private drafts or secrets.
