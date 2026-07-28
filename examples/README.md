# Examples

`campaign.json` is a complete input for the primary CLI journey:

```bash
helix-spirals validate examples/campaign.json
helix-spirals preview examples/campaign.json
helix-spirals export examples/campaign.json --output outbox
```

Expected behavior:

- validation reports one deterministic campaign ID and the three requested platforms;
- preview prints bounded X, LinkedIn, and Discord drafts without writing files;
- export creates `manifest.json`, `x.md`, `linkedin.md`, and `discord.md` beneath a generated
  campaign folder;
- running the same export again fails safely unless `--overwrite` is explicit.

`library_usage.py` demonstrates the same journey through the documented Python API:

```bash
python examples/library_usage.py
```

This script writes an `outbox/` directory. It does not use the network or publish content.
