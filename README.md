# Helix Creative Spirals

Helix Creative Spirals is a local-first CLI and Python library that turns one approved source
draft into copy-ready files for X, LinkedIn, and Discord. It validates campaign input, applies
platform-aware limits, reports every truncation, and exports a deterministic review bundle.

It is for solo creators, developer advocates, and small content teams that want a scriptable
review/export step without connecting social accounts or sending draft content to a service.

> Maturity: **0.1 release candidate.** Preview and local export are implemented and tested.
> Automatic publishing, scheduling, analytics, and AI generation are deliberately not included.

## Fastest successful path

Prerequisite: Python 3.10 or newer.

```bash
git clone https://github.com/Deathcharge/helix-creative-spirals.git
cd helix-creative-spirals
python -m venv .venv
```

Activate the environment:

```bash
# macOS/Linux
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1
```

Install and preview the included campaign:

```bash
python -m pip install -e .
helix-spirals preview examples/campaign.json
```

No API keys, accounts, database, or private Helix repository are required.

## Core journey

Create a starter file, preview it, then export only after reviewing the output:

```bash
helix-spirals init campaign.json
helix-spirals validate campaign.json
helix-spirals preview campaign.json
helix-spirals export campaign.json --output outbox
```

The export command creates a deterministic directory such as:

```text
outbox/
└── product-launch-csp_8b7f2a12c941/
    ├── manifest.json
    ├── x.md
    ├── linkedin.md
    └── discord.md
```

Re-exporting an unchanged campaign is refused by default. Use `--overwrite` only when replacing
that same deterministic bundle is intentional.

## Campaign format

Campaigns are UTF-8 JSON files. Unknown keys are errors so misspellings do not silently change
behavior.

```json
{
  "schemaVersion": 1,
  "name": "Product launch",
  "title": "We shipped something useful",
  "body": "One approved source draft becomes three reviewable outputs.",
  "link": "https://example.com/launch",
  "hashtags": ["buildinpublic", "product"],
  "platforms": ["x", "linkedin", "discord"]
}
```

| Field | Required | Rules |
| --- | --- | --- |
| `schemaVersion` | yes | Must be `1`. |
| `name` | yes | Single line, 1–120 characters; used to derive a safe folder name. |
| `body` | yes | 1–100,000 characters. |
| `platforms` | yes | Unique values from `x`, `linkedin`, `discord`. |
| `title` | no | Single line, at most 200 characters; omitted from X output. |
| `link` | no | Absolute HTTP(S) URL, at most 500 characters, no embedded credentials. |
| `hashtags` | no | Up to 10 unique values containing letters, numbers, or underscores. |

Formatting defaults are 280 weighted characters for X, 3,000 characters for LinkedIn, and
2,000 characters for Discord. The X counter implements X's published Unicode weighting and
23-character URL rule. Content is normalized to NFC and truncated on conservative text clusters;
links and suffix metadata are preserved where possible. Every modification is recorded as a
warning in preview output and `manifest.json`.

## CLI reference

```text
helix-spirals --help
helix-spirals --version
helix-spirals init [PATH]
helix-spirals validate CONFIG [--json]
helix-spirals preview CONFIG [--json]
helix-spirals export CONFIG [--output DIRECTORY] [--overwrite] [--json]
```

Successful commands return exit code `0`. Validation and I/O failures return `1`; invalid CLI
usage returns `2`. Human-readable errors go to stderr. `--json` keeps successful output suitable
for scripts.

## Python API

```python
from helix_creative_spirals import build_campaign, export_campaign, load_campaign

config = load_campaign("examples/campaign.json")
bundle = build_campaign(config)       # deterministic and side-effect free
for draft in bundle.drafts:
    print(draft.platform, draft.character_count, draft.content)

path = export_campaign(bundle, "outbox")
print(path)
```

See [API.md](docs/API.md) for the deliberately small public surface and error behavior.

## Development and verification

Install the pinned development toolchain:

```bash
python -m pip install -r requirements-dev.txt
```

Run the same checks enforced by CI:

```bash
python -m black --check helix_creative_spirals tests examples
python -m flake8 helix_creative_spirals tests examples
python -m mypy
python -m pytest --cov=helix_creative_spirals --cov-report=term-missing
python -m build
```

CI is configured to run these checks on Python 3.10 and 3.13 and smoke-test the built wheel and
console command.
The `requirements-dev.txt` file pins the direct development tools; the installed package has no
third-party runtime dependencies.

## Architecture

The package has four boundaries:

- `models.py` validates and normalizes local JSON input.
- `formatters.py` creates bounded platform drafts without network access.
- `workflow.py` computes deterministic IDs and safely exports review bundles.
- `cli.py` maps these operations to stable commands and exit codes.

`build_campaign` has no file or network side effects. Only `load_campaign`, `init`, and
`export_campaign` touch disk. See [ARCHITECTURE.md](docs/ARCHITECTURE.md) for trust boundaries and
failure behavior.

## Security, privacy, cost, and limitations

- Draft content stays on the local machine; there is no network client, telemetry, database, or
  credential loading.
- Input files are capped at 1 MB and content fields are bounded. Unknown fields, control
  characters, unsafe URL schemes, URL credentials, duplicate platforms, and invalid hashtags are
  rejected.
- Export paths are generated from a sanitized name plus a content hash. Existing bundles are not
  overwritten without explicit opt-in, and symbolic-link bundle targets are rejected.
- Discord broadcast mentions are surfaced as warnings. This tool never posts them.
- Runtime operating cost is zero beyond the user's local compute and storage.
- Platform policies and edge-case counting rules change. Review final text in the platform's own
  composer before publishing. The tool does not claim API conformance or automatic policy
  compliance.
- Media, per-account capabilities, calendars, approvals, network publishing, and analytics are
  outside the 0.1 scope.

## Distribution and release status

The simplest distribution is a source checkout or locally built wheel installed with `pipx` or
`pip`. This repository is not currently published on PyPI, so do not assume
`pip install helix-creative-spirals` resolves from the public index.

The repository's `LICENSE` is a customized Business Source License document. Its named Licensed
Work, licensor identity, contact domain, change date, and the separate `LICENSE.PROPRIETARY` file
require owner/legal confirmation before public package publication. Package metadata reports a
custom `LicenseRef` and does not claim an OSI-approved license. No license text was changed during
productization.

See [PRODUCTIZATION.md](docs/PRODUCTIZATION.md) for the evidence, completed work, known risks, and
release gates. Contribution instructions are in [CONTRIBUTING.md](CONTRIBUTING.md).
