# Platform-native content variants

One message rarely reads naturally everywhere. Samsarix campaigns can keep a baseline content block
and add complete overrides for selected requested platforms. Platforms without an override continue
to use the baseline.

```json
{
  "schemaVersion": 1,
  "name": "Release announcement",
  "title": "A safer release workflow",
  "body": "Baseline copy for every requested channel.",
  "link": "https://example.com/release",
  "hashtags": ["Samsarix", "release"],
  "platforms": ["x", "linkedin", "discord"],
  "platformVariants": {
    "x": {
      "body": "Short, direct copy written for X.",
      "link": "https://example.com/x",
      "hashtags": ["Samsarix"]
    },
    "discord": {
      "title": "Community release note",
      "body": "Conversational copy written for the community.",
      "hashtags": []
    }
  }
}
```

Run the complete example without an account or network connection:

```bash
samsarix-campaign validate examples/campaign-variants.json
samsarix-campaign preview examples/campaign-variants.json
samsarix-campaign check examples/campaign-variants.json
```

## Replacement semantics

Each value in `platformVariants` is a complete content block, not a partial merge:

- `body` is required and must be non-empty;
- `title` and `link` are optional; omission means they are absent from that platform draft;
- `hashtags` is optional; omission means no hashtags, just like an explicit empty array;
- a variant key must be one of the five canonical lowercase names and must also be present in the
  campaign's `platforms` array;
- every field uses the same normalization, length, URL, hashtag, and control-character rules as
  baseline content.

Complete replacement makes intent visible. For example, leaving `link` out of an X variant removes
the baseline link from X; it cannot be mistaken for accidental inheritance. Remove the entire X
entry to return X to the baseline content.

Variants still pass through the normal formatter. X and Bluesky omit titles, each platform uses its
documented counting model and configured limit, oversized bodies are visibly truncated, hashtags
may be omitted to preserve body room, and Discord broadcast mentions produce a warning. Media stays
separate and retains its existing platform targeting.

## Review and identity

Normalized variants are part of the campaign source hash and deterministic `scs_*` ID. Adding,
removing, or changing one therefore:

- appears as `platformVariants` in semantic source diffs;
- changes only the generated platform drafts whose rendered result changed;
- invalidates campaign and whole-plan approvals tied to the old source;
- propagates through plan identity, adapter output, handoff verification, and readiness reports.

Equivalent Unicode and surrounding-whitespace spelling normalizes to the same identity. Variant
objects are ordered canonically in normalized output, independent of JSON object insertion order.

## Product and security boundary

Current connected-account publishers explicitly support per-network customization. Buffer starts
from a base post and exposes “Customize for each network”; Sprout Social splits network tabs into
unique content after customization. Those workflows support the need, while Samsarix keeps a
different boundary: deterministic local files before a human or separately authorized publisher.

- Buffer: <https://support.buffer.com/article/642-scheduling-posts>
- Sprout Social: <https://support.sproutsocial.com/hc/en-us/articles/36494895896589-How-do-I-use-Customize-Post-per-Network-in-Compose>

Variant text is untrusted local input. Core validates and renders it but never executes it, resolves
mentions against an account, contacts a provider, uploads media, or publishes. Generated files can
contain confidential campaign content; protect them like the source and review each result in the
target platform's own composer before publication.

## Compatibility

`platformVariants` is optional in campaign schema version 1 and was added in package 0.10. Existing
campaigns and consumers that ignore absent optional fields retain their previous behavior. A
consumer that rejects every unknown optional source field must update its schema before accepting a
campaign that uses variants. Adapter v2 and generated draft shapes do not change; they already carry
the exact rendered content. As with every package-version change, handoff v1 packets retain their
recorded `producerVersion`; verify a 0.9-produced packet with 0.9 under the existing byte-exact
compatibility rule, or regenerate approval-dependent evidence under 0.10.
