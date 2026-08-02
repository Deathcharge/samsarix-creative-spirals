# Portable media references

Samsarix Creative Spirals 0.6 adds image metadata to the same local, reviewable campaign source as
the post text. The core validates references, carries them through semantic review and exports,
and includes the applicable references beside each platform draft. It never opens, hashes, copies,
decodes, sniffs, resizes, or uploads an image.

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
[single-image media posts](https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/post-api-schema?view=li-lms-2026-07)
and [multi-image posts of 2–20 images](https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/multiimage-post-api?view=li-lms-2026-02).

The 1,000-character alt-text cap matches
[X's documented maximum](https://docs.x.com/x-api/fundamentals/data-dictionary) and stays beneath
Discord's 1,024-character attachment-description limit in the
[Message Resource](https://docs.discord.com/developers/resources/message). LinkedIn and many
Mastodon servers allow more. Samsarix requires non-empty descriptions even where a provider schema
would accept an empty string because the field exists for accessibility, not merely API validity.

GIF, WebP, AVIF, video, audio, documents, dimensions, MIME types, byte sizes, crops, captions,
sensitivity flags, and AI-media disclosure are deliberately outside this first portable contract.
Several platforms impose mutually exclusive combinations or provider/account-specific limits that
cannot be proven from an unread local path.

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

`adapter.json` does not embed image bytes and media files are not copied into the export directory.
Consumers therefore need an explicitly trusted checkout or artifact containing the original plan,
campaign files, and referenced media. Treat all paths and content as untrusted even when the JSON
schema passes.
