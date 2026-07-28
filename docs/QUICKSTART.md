# Quick start

Helix Creative Spirals needs Python 3.10+ and no API credentials.

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
helix-spirals --version
```

## 2. Create and preview a campaign

```bash
helix-spirals init campaign.json
helix-spirals preview campaign.json
```

Edit `campaign.json`, then run `preview` again. Preview is side-effect free: it reads the file and
writes only to stdout/stderr.

## 3. Validate for automation

```bash
helix-spirals validate campaign.json --json
```

Example success:

```json
{
  "valid": true,
  "campaignId": "csp_8b7f2a12c941",
  "platforms": ["x", "linkedin", "discord"]
}
```

Validation failures return exit code `1` and write the reason to stderr.

## 4. Export the approved drafts

```bash
helix-spirals export campaign.json --output outbox
```

The resulting folder contains one Markdown file per platform and `manifest.json` with the source
hash, limits, truncation state, warnings, and UTC export time. The tool does not publish anything;
copy the reviewed content into the destination platform or pass the files to a separate approved
integration.

If the exact same campaign was already exported, the command refuses to replace it. An intentional
replacement is explicit:

```bash
helix-spirals export campaign.json --output outbox --overwrite
```

## Troubleshooting

- `unknown field(s)`: fix the spelling or remove unsupported keys.
- `body must not be empty`: provide the approved source draft.
- `link must be an absolute http or https URL`: include the full scheme and hostname.
- `bundle already exists`: review the existing bundle, change the campaign, choose another output
  root, or explicitly pass `--overwrite`.
- `helix-spirals: command not found`: activate the environment where the package was installed, or
  run `python -m helix_creative_spirals` with the same arguments.
