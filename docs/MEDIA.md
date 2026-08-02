# Portable media references

Samsarix Creative Spirals keeps image references in the same local, reviewable campaign source as
the post text. The default metadata workflow validates and carries those references without opening
them. Version 0.14 adds one explicit opt-in: plan approval creation can inspect, hash, and bind the
exact static JPEG/PNG bytes, and the approved handoff can carry those exact bytes. The package still
never uploads, resizes, transforms, or sends an image over a network.

## Authoring contract

Add an optional `media` array to a campaign:

```json
{
  "schemaVersion": 1,
  "name": "Product launch",
  "body": "A reviewable launch update.",
  "platforms": ["x", "linkedin", "bluesky", "mastodon", "discord"],
  "media": [
    {
      "path": "media/launch-dashboard.png",
      "altText": "Campaign review dashboard showing five platform drafts"
    },
    {
      "path": "media/linkedin-detail.jpg",
      "altText": "Detailed campaign approval workflow",
      "platforms": ["linkedin"]
    }
  ]
}
```

`platforms` on a media reference is optional. Omission targets every platform requested by the
campaign. When present, it must be a unique, non-empty subset of the campaign platforms. Target
order normalizes to campaign order, so equivalent spelling and ordering produce the same campaign
identity.

The portable core envelope is intentionally narrow:

- `.jpg`, `.jpeg`, and `.png` static-image references only;
- at most 20 references in one campaign and at most four applicable images per platform;
- a unique case-insensitive path for each image;
- required, single-line alt text from 1 through 1,000 Unicode characters;
- NFC-normalized forward-slash relative paths, at most 240 characters, with no absolute, drive,
  backslash, empty, dot, parent, Windows-reserved, control, or whitespace-padded segment.

Media paths are relative to the directory containing their campaign JSON file. The path may point
to a file that does not exist: validation is about safe portable metadata, not filesystem or media
truth. Adding, removing, retargeting, or editing a reference changes campaign and plan identity,
appears in semantic diff output, and invalidates source-bound approval metadata.

## Why this envelope

The common four-image ceiling is supported by
[X's official media guidance](https://docs.x.com/x-api/media/quickstart/best-practices) and the
canonical [Bluesky images Lexicon](https://github.com/bluesky-social/atproto/blob/main/lexicons/app/bsky/embed/images.json).
Mastodon exposes its actual attachment ceiling and description limit through each server's
[instance configuration](https://docs.joinmastodon.org/entities/Instance/), so four remains a
portable default rather than a promise about every server. LinkedIn defines both
[single-image media posts](https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/images-api?view=li-lms-2026-05)
and [multi-image posts of 2–20 images](https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/multiimage-post-api?view=li-lms-2026-02).

The 1,000-character alt-text cap matches
[X's documented maximum](https://docs.x.com/x-api/fundamentals/data-dictionary) and stays beneath
Discord's 1,024-character attachment-description limit in the
[Message Resource](https://docs.discord.com/developers/resources/message). LinkedIn and many
Mastodon servers allow more. Samsarix requires non-empty descriptions even where a provider schema
would accept an empty string because the field exists for accessibility, not merely API validity.

GIF, WebP, AVIF, video, audio, documents, crops, captions, sensitivity flags, and AI-media
disclosure remain outside this portable contract. Several platforms impose mutually exclusive
combinations or provider/account-specific limits that cannot be proven locally.

## Exact-media approval and packaging

Use exact-media mode only when the reviewer has actually inspected the referenced images:

```bash
samsarix-campaign plan approval create launch-plan.json \
  --by "Visual reviewer" \
  --include-media \
  --output launch-plan.approval.json
samsarix-campaign plan approval verify launch-plan.json launch-plan.approval.json
samsarix-campaign plan handoff create \
  launch-plan.json launch-plan.approval.json \
  --output handoff-outbox
```

`--include-media` is available only on plan approval creation. Once the resulting approval contains
a `media` binding, approval verification and handoff creation automatically re-collect the current
files and fail if any byte, path mapping, dimension, alt text, or platform target changed. The
handoff embeds normalized `media-index.json` and deduplicated files named
`media/<sha256>.jpg|png`. Handoff verification needs no original image checkout: it verifies the
packet bytes against the exact snapshot already bound by the embedded approval.

The collection boundary is deliberately conservative:

- static `.jpg`, `.jpeg`, and `.png` only, with suffix and structural signature agreement;
- 1–2,000,000 bytes per file, matching the current canonical Bluesky image-blob ceiling;
- fewer than 36,152,320 pixels, matching LinkedIn's current image pixel rule;
- at most 400 plan references and 100,000,000 unique image bytes in one packet;
- campaign-relative containment, no symbolic-link path component, regular-file checks, and the
  same opened file identity/size/modification time before and after a bounded read;
- PNG chunk CRC, required IHDR/IDAT/IEND structure, and animated-PNG rejection; and
- JPEG SOI/EOI plus bounded frame/scan header and positive-dimension checks.

The 2,000,000-byte limit is stricter than [X's 5 MB image limit](https://docs.x.com/x-api/media/introduction)
and [Discord's 10 MiB default per-file limit](https://docs.discord.com/developers/reference#uploading-files).
Mastodon publishes supported MIME types, byte size, pixel matrix, attachment count, and description
limits through each server's [instance configuration](https://docs.joinmastodon.org/entities/Instance/),
so a downstream adapter must still query and enforce the selected instance at use time. The
canonical [Bluesky images Lexicon](https://github.com/bluesky-social/atproto/blob/main/lexicons/app/bsky/embed/images.json)
is the source of the 2,000,000-byte ceiling.

This is structural validation, not a full pixel decode, antivirus scan, content moderation check,
copyright or consent determination, or guarantee of provider acceptance. Images may contain EXIF,
embedded profiles, private visual information, or exploit content for downstream decoders. Treat a
media packet as sensitive untrusted input and let the chosen provider/adapter perform its own full
decode and current capability checks.

## Adapter responsibilities

Adapter contract v2 carries the complete normalized references on each campaign item and the
applicable `{path, altText}` pairs on each draft. An adapter that chooses to dereference a path must:

1. resolve the item `source` beneath the trusted plan directory and the media path beneath that
   campaign file's directory;
2. resolve symbolic links and reject any result outside that campaign directory;
3. perform a race-safe open relative to a trusted directory handle with no-follow semantics where
   available; otherwise revalidate the opened handle's identity and containment, then inspect and
   upload that same opened object instead of validating a path and reopening it later;
4. require an ordinary file and impose its own read and upload size limits before reading;
5. inspect the actual MIME type, dimensions, animation, and provider-supported format rather than
   trusting the suffix;
6. revalidate attachment count, alt-text rules, and all provider/account/instance constraints at
   the moment of draft creation;
7. show the exact resolved files and destination account to the operator before any external side
   effect; and
8. keep draft creation, scheduling, publishing, replacement, and deletion behind separate explicit
   authorization.

`adapter.json` and ordinary plan exports never embed image bytes. A metadata-only approval/handoff
also remains unchanged. Only an approval created with `--include-media` causes its later handoff to
carry exact files. Treat every path and payload as untrusted even when the JSON schema and packet
verification pass.
