# Samsarix Creative Spirals

Samsarix Creative Spirals is a local-first CLI and typed Python library that turns one approved
source draft into copy-ready files for X, LinkedIn, Bluesky, Mastodon, and Discord. It validates campaign input,
applies platform-aware limits, reports every truncation, and exports a deterministic review bundle.

It is for solo creators, developer advocates, and small content teams that want a scriptable
review/export step without connecting social accounts or sending draft content to a service.

> Maturity: **0.3 alpha.** Federated-platform preview, quality gates, and local export are implemented
> and tested. Automatic
> publishing, scheduling, analytics, and AI generation are deliberately not included.

## Fastest successful path

Prerequisite: Python 3.10 or newer.

```bash
git clone https://github.com/Deathcharge/samsarix-creative-spirals.git
cd samsarix-creative-spirals
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
samsarix-campaign preview examples/campaign.json
```

No API keys, accounts, database, network connection, or other Samsarix repository is required.

## Core journey

Create a starter file, preview it, run the quality gate, then export after reviewing the output:

```bash
samsarix-campaign init campaign.json
samsarix-campaign validate campaign.json
samsarix-campaign preview campaign.json
samsarix-campaign check campaign.json
samsarix-campaign export campaign.json --output outbox
```

The export command creates a deterministic directory such as:

```text
outbox/
└── product-launch-scs_8b7f2a12c941/
    ├── manifest.json
    ├── x.md
    ├── linkedin.md
    ├── bluesky.md
    ├── mastodon.md
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
  "body": "One approved source draft becomes five reviewable outputs.",
  "link": "https://example.com/launch",
  "hashtags": ["buildinpublic", "product"],
  "platforms": ["x", "linkedin", "bluesky", "mastodon", "discord"],
  "platformLimits": {"mastodon": 1000}
}
```

| Field | Required | Rules |
| --- | --- | --- |
| `schemaVersion` | yes | Must be `1`. |
| `name` | yes | Single line, 1–120 characters; used to derive a safe folder name. |
| `body` | yes | 1–100,000 characters. |
| `platforms` | yes | Unique values from `x`, `linkedin`, `bluesky`, `mastodon`, `discord`. |
| `title` | no | Single line, at most 200 characters; omitted from X and Bluesky output. |
| `link` | no | Absolute HTTP(S) URL, at most 500 characters, no embedded credentials. |
| `hashtags` | no | Up to 10 unique values containing letters, numbers, or underscores. |
| `platformLimits` | no | Stricter per-platform limits, or a Mastodon instance limit up to 100,000. Keys must also appear in `platforms`. |

Print the bundled JSON Schema for editor or CI integration, or write it to a new file:

```bash
samsarix-campaign schema
samsarix-campaign schema --output campaign.schema.json
```

Formatting defaults are 280 weighted characters for X, 3,000 UTF-16 code units for LinkedIn, 300
graphemes plus 3,000 UTF-8 bytes for Bluesky, 500 characters for Mastodon, and 2,000 UTF-16 code
units for Discord. X and Mastodon apply their documented 23-character URL rule. Mastodon instances
may advertise another maximum; record it explicitly in `platformLimits`. Content is normalized to
NFC and truncated on conservative text clusters; links and suffix metadata are preserved where
possible. Every modification is recorded in preview output and `manifest.json`.

## Quality gate

`check` makes content QA useful in scripts and pull requests. It returns `3` if any platform draft
was truncated. Review warnings are visible but non-blocking by default; promote them to failures
when a workflow requires a clean report:

```bash
samsarix-campaign check campaign.json --json
samsarix-campaign check campaign.json --warnings-as-errors
```

This command performs no writes or network calls. A successful JSON report has
`"publishable": true`; findings have stable `code`, `severity`, `platform`, and `message` fields.

## CLI reference

```text
samsarix-campaign --help
samsarix-campaign --version
samsarix-campaign init [PATH]
samsarix-campaign validate CONFIG [--json]
samsarix-campaign preview CONFIG [--json]
samsarix-campaign check CONFIG [--warnings-as-errors] [--json]
samsarix-campaign export CONFIG [--output DIRECTORY] [--overwrite] [--json]
samsarix-campaign schema [--output PATH]
```

Successful commands return exit code `0`. Validation and I/O failures return `1`; invalid CLI
usage returns `2`; a valid campaign that fails `check` returns `3`. Human-readable errors go to
stderr. Quality reports—including failed reports requested with `--json`—stay on stdout for scripts.

## Python API

```python
from samsarix_creative_spirals import build_campaign, check_campaign, export_campaign, load_campaign

config = load_campaign("examples/campaign.json")
bundle = build_campaign(config)       # deterministic and side-effect free
report = check_campaign(bundle)
if not report.publishable:
    raise SystemExit(report.to_dict())
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
python -m black --check samsarix_creative_spirals tests examples
python -m flake8 samsarix_creative_spirals tests examples
python -m mypy
python -m pytest --cov=samsarix_creative_spirals --cov-report=term-missing
python -m build
```

CI runs these checks on Python 3.10 and 3.13 and smoke-tests the built wheel, schema resource, and
console command. The package has no third-party runtime dependencies.

## Architecture and boundaries

- `models.py` validates and normalizes local JSON input.
- `formatters.py` creates bounded platform drafts without network access.
- `workflow.py` computes deterministic IDs and safely exports review bundles.
- `quality.py` evaluates deterministic, machine-readable campaign quality gates.
- `schema.py` exposes the campaign JSON Schema bundled in the wheel.
- `cli.py` maps these operations to stable commands and exit codes.

`build_campaign` and `check_campaign` have no file or network side effects. Only `load_campaign`, `init`, `schema
--output`, and `export_campaign` touch disk. See [ARCHITECTURE.md](docs/ARCHITECTURE.md) for trust
boundaries and failure behavior.

## Security, privacy, cost, and limitations

- Draft content stays on the local machine; there is no network client, telemetry, database, or
  credential loading.
- Input files are capped at 1 MB and content fields are bounded. Duplicate or excessively nested
  JSON, unknown fields, control characters, unsafe URL schemes, URL credentials, duplicate
  platforms, and invalid hashtags are rejected.
- Export paths are generated from a sanitized name plus a content hash. Existing bundles are not
  overwritten without explicit opt-in, and symbolic-link bundle targets are rejected.
- Discord broadcast mentions are surfaced as warnings. This tool never posts them.
- Runtime operating cost is zero beyond local compute and storage.
- Platform policies and edge-case counting rules change. Review final text in each platform's own
  composer before publishing; this tool does not claim API conformance.
- Mastodon limits are instance-configurable; the default is 500 and `platformLimits` records a
  known instance maximum without contacting that instance.
- Media, per-account capabilities, calendars, approvals, network publishing, and analytics are
  outside the 0.3 scope.

Security reports belong at `support@samsarix.com`; see [SECURITY.md](SECURITY.md).

## Distribution and license

The simplest distribution is a source checkout or locally built wheel installed with `pipx` or
`pip`. The package is not currently published on PyPI, so do not assume
`pip install samsarix-creative-spirals` resolves from the public index.

The code is licensed under [MPL-2.0](LICENSE), a file-level copyleft license selected to keep
distributed changes to covered source files open while allowing use in larger works. Copyright
and origin notices are in [NOTICE](NOTICE), practical licensing context is in
[LICENSING.md](LICENSING.md), and brand use is addressed in [TRADEMARKS.md](TRADEMARKS.md).

General and licensing contact: `contact@samsarix.com`

Support and security contact: `support@samsarix.com`

See [PRODUCTIZATION.md](docs/PRODUCTIZATION.md) for the evidence, completed work, known risks, and
release gates. Contribution instructions are in [CONTRIBUTING.md](CONTRIBUTING.md).
