# Python API

The supported public API is intentionally small. Imports not listed here are internal and may
change without notice.

## Models

### `CampaignConfig`

`CampaignConfig.from_dict(mapping)` validates and normalizes a JSON-compatible mapping. It returns
an immutable dataclass with `schema_version`, `name`, `body`, `platforms`, `title`, `link`,
`hashtags`, and normalized `platform_limits`. `limit_for(platform)` returns an explicit override or
the supported default. `to_dict()` returns the normalized JSON shape.

### `PlatformDraft`

An immutable result for one platform:

- `platform`
- `content`
- `character_count`
- `original_character_count`
- `character_limit`
- `truncated`
- `warnings`

### `CampaignBundle`

An immutable collection with deterministic `campaign_id`, full SHA-256 `source_hash`, `name`, and
ordered `drafts`. `to_dict()` produces machine-readable preview output.

### `QualityIssue`

One stable quality finding with `code`, `severity`, `platform`, and human-readable `message`.

### `CampaignCheck`

An immutable quality result with `campaign_id`, `publishable`, and ordered `issues`. `to_dict()`
returns the same schema used by `samsarix-campaign check --json`.

### `ConfigError`

Subclasses `ValueError`. `issues` is a tuple of one or more actionable validation messages. File
decoding and JSON syntax failures from `load_campaign` are also presented as `ConfigError` so CLI
and library consumers have one validation failure contract.

## Functions

### `load_campaign(path) -> CampaignConfig`

Reads a UTF-8 or UTF-8-with-BOM JSON file. Files larger than 1,000,000 bytes, non-object roots,
invalid JSON, invalid encodings, and schema violations raise `ConfigError`. No network access is
performed.

### `build_campaign(config) -> CampaignBundle`

Accepts a `CampaignConfig` or plain dictionary. It normalizes the source, hashes canonical JSON,
and formats each requested platform. Repeated calls with equal normalized input return equal
bundles. It performs no file or network I/O.

Supported platform defaults are X (280 weighted characters), LinkedIn (3,000 UTF-16 code units),
Bluesky (300 graphemes and 3,000 UTF-8 bytes), Mastodon (500 characters with 23-character URL
accounting), and Discord (2,000 UTF-16 code units). `platformLimits` may make any platform stricter;
Mastodon may be raised to match an intended instance's advertised limit.

### `check_campaign(bundle, *, warnings_as_errors=False) -> CampaignCheck`

Produces a deterministic quality report without file or network I/O. Truncation is always an error.
Other platform review warnings remain warnings unless `warnings_as_errors=True`. `publishable` is
true when the report contains no error-severity issue.

### `export_campaign(bundle, output_root="outbox", *, overwrite=False, exported_at=None) -> Path`

Creates `<safe-name>-<campaign-id>` beneath the resolved output root, writes one UTF-8 Markdown
file per draft, writes `manifest.json`, and returns the absolute bundle path.

The default refuses an existing bundle. `overwrite=True` replaces files only inside the generated
bundle directory. A non-directory or symbolic-link bundle target is rejected. `exported_at` exists
for reproducible tests; normal callers should leave it unset.

I/O failures raise the relevant `OSError` subclass.

### `load_campaign_schema() -> dict[str, Any]`

Loads a fresh dictionary from the JSON Schema bundled in the installed wheel. It performs no
network access and is useful for editor, form, or CI integration. The CLI exposes the same artifact
through `samsarix-campaign schema`.

## Example

```python
from samsarix_creative_spirals import (
    ConfigError,
    build_campaign,
    check_campaign,
    export_campaign,
    load_campaign,
)

try:
    config = load_campaign("campaign.json")
    bundle = build_campaign(config)
    report = check_campaign(bundle)
    if not report.publishable:
        raise ConfigError([issue.message for issue in report.issues])
    destination = export_campaign(bundle, "outbox")
except ConfigError as error:
    for issue in error.issues:
        print(issue)
except OSError as error:
    print(f"Export failed: {error}")
else:
    print(destination)
```

## Compatibility policy

The package is pre-1.0. The exported names, JSON `schemaVersion: 1`, manifest shape, and documented
CLI behavior are the compatibility surface for 0.3.x. Internal helpers and exact prose in warning
messages may evolve. Breaking schema or public API changes require a minor-version increment while
the package remains pre-1.0.
