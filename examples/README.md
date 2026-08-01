# Examples

`campaign.json` is a complete input for the primary CLI journey:

```bash
samsarix-campaign validate examples/campaign.json
samsarix-campaign preview examples/campaign.json
samsarix-campaign check examples/campaign.json
samsarix-campaign export examples/campaign.json --output outbox
```

Expected behavior:

- validation reports one deterministic campaign ID and the five requested platforms;
- preview prints bounded X, LinkedIn, Bluesky, Mastodon, and Discord drafts without writing files;
- check reports truncation and review warnings with a CI-safe exit code;
- export creates `manifest.json` and one Markdown file per requested platform beneath a generated
  campaign folder;
- running the same export again fails safely unless `--overwrite` is explicit.

`library_usage.py` demonstrates the same journey through the documented Python API:

```bash
python examples/library_usage.py
```

This script writes an `outbox/` directory. It does not use the network or publish content.
