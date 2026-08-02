# Quick start

Samsarix Creative Spirals needs Python 3.10+ and no API credentials.

## 1. Install from this checkout

```bash
python -m venv .venv
```

```bash
# macOS/Linux
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1
```

```bash
python -m pip install -e .
samsarix-campaign --version
```

## 2. Create, preview, and check a campaign

```bash
samsarix-campaign init campaign.json
samsarix-campaign preview campaign.json
samsarix-campaign check campaign.json
```

Edit `campaign.json`, then run `preview` and `check` again. Both are side-effect free: they read the
file and write only to stdout/stderr. `check` exits with `3` when any draft was truncated.

## 3. Validate for automation

```bash
samsarix-campaign validate campaign.json --json
```

Example success:

```json
{
  "valid": true,
  "campaignId": "scs_8b7f2a12c941",
  "platforms": ["x", "linkedin", "bluesky", "mastodon", "discord"]
}
```

Validation failures return exit code `1` and write the reason to stderr.

To make every review warning block CI as well as truncation:

```bash
samsarix-campaign check campaign.json --warnings-as-errors --json
```

For editor or CI support, print the bundled schema or write it to a new file:

```bash
samsarix-campaign schema
samsarix-campaign schema --output campaign.schema.json
```

## 4. Export the approved drafts

```bash
samsarix-campaign export campaign.json --output outbox
```

The resulting folder contains one Markdown file per requested platform and `manifest.json` with the source
hash, limits, truncation state, warnings, and UTC export time. The tool does not publish anything;
copy the reviewed content into the destination platform or pass the files to a separate approved
integration.

If the exact same campaign was already exported, the command refuses to replace it. An intentional
replacement is explicit:

```bash
samsarix-campaign export campaign.json --output outbox --overwrite
```

## 5. Review and export a complete campaign plan

The included plan references two standalone campaign files and declares the channels every item
must cover:

```bash
samsarix-campaign plan validate examples/launch-plan.json --json
samsarix-campaign plan preview examples/launch-plan.json
samsarix-campaign plan check examples/launch-plan.json
samsarix-campaign plan export examples/launch-plan.json --output plan-outbox
```

Plan paths use forward slashes, remain relative to the plan file, and cannot escape its directory.
`intendedAt` is optional; when present it must be RFC 3339 with an explicit offset or `Z`.

The exported directory contains:

```text
plan-outbox/
└── local-first-release-sequence-scp_<content-id>/
    ├── manifest.json
    ├── calendar.ics
    └── csv/
        ├── x.csv
        ├── linkedin.csv
        ├── bluesky.csv
        ├── mastodon.csv
        └── discord.csv
```

The calendar is an interchange artifact, not a scheduler. CSV files use stable Samsarix columns
and explicit UTC timestamps for review or adapter input; publisher-specific imports may require a
separate transformation.

## Troubleshooting

- `unknown field(s)`: fix the spelling or remove unsupported keys.
- `body must not be empty`: provide the approved source draft.
- `link must be an absolute http or https URL`: include the full scheme and hostname.
- `bundle already exists`: review the existing bundle, change the campaign, choose another output
  root, or explicitly pass `--overwrite`.
- `Quality check failed`: inspect the listed platform findings; shorten the source, reduce suffix
  metadata, or use an accurate `platformLimits.mastodon` value for the intended instance.
- `resolves outside the plan directory`: move the campaign JSON beneath the plan directory and use
  a portable relative path without `..` or a symbolic-link escape.
- `samsarix-campaign: command not found`: activate the environment where the package was installed,
  or run `python -m samsarix_creative_spirals` with the same arguments.
