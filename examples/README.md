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

`campaign-media.json` demonstrates campaign-wide and LinkedIn-only image metadata:

```bash
samsarix-campaign preview examples/campaign-media.json --json
samsarix-campaign diff examples/campaign.json examples/campaign-media.json --json
```

The referenced image files are intentionally not bundled: validation and preview still pass
because core treats paths as review metadata and never opens them. Replace the paths with real
campaign-relative JPEG/PNG files only when handing the source tree to a separately permissioned
adapter that implements the controls in `docs/MEDIA.md`.

`launch-plan.json` references `campaign.json` and `campaign-follow-up.json` as one release sequence:

```bash
samsarix-campaign plan validate examples/launch-plan.json
samsarix-campaign plan preview examples/launch-plan.json
samsarix-campaign plan check examples/launch-plan.json
samsarix-campaign plan export examples/launch-plan.json --output plan-outbox
```

The plan export contains a manifest, v2 adapter JSON, an RFC 5545 calendar, and one
publisher-neutral CSV for each used platform. It records intended UTC times but never schedules or
publishes a post.
