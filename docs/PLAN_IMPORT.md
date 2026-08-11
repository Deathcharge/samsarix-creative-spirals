# Canonical CSV and plan import

Samsarix can turn a bounded UTF-8 authoring CSV into ordinary campaign JSON files and one campaign
plan without connecting an account or partially writing invalid rows. The generated sources use the
same schemas, hashes, quality gates, diffs, feedback, approvals, handoffs, and exports as files
written by hand.

## Quick start

Copy [`examples/plan-import.csv`](../examples/plan-import.csv), edit its rows, then run:

```bash
samsarix-campaign plan import examples/plan-import.csv \
  --name "Release sequence" \
  --required-platform x \
  --required-platform linkedin \
  --output imported-release \
  --json
samsarix-campaign plan check imported-release/plan.json --json
```

The output directory must not already exist. A successful import contains `plan.json` and one
normalized `campaigns/NNN-SLUG.json` file per row. Every source is immediately loadable by the
existing public API and CLI.

## Exact v1 CSV contract

The first record must contain this exact, case-sensitive field order:

```text
name,title,body,link,hashtags,platforms,intended_at,media_path,media_alt_text,media_platforms
```

| Field | Required | Contract |
| --- | --- | --- |
| `name` | yes | Campaign name; one line, 1–120 characters. |
| `title` | no | Baseline title; one line, at most 200 characters. |
| `body` | yes | Baseline body; 1–100,000 characters. Quoted CSV cells may contain line breaks. |
| `link` | no | Absolute credential-free HTTP(S) URL. |
| `hashtags` | no | Canonical hashtag names without `#`, separated by a pipe character. |
| `platforms` | yes | One or more of `x`, `linkedin`, `bluesky`, `mastodon`, `discord`, separated by a pipe character. |
| `intended_at` | no | Full RFC 3339 date-time with `Z` or a known explicit offset; normalized to UTC. |
| `media_path` | no | One portable campaign-relative `.jpg`, `.jpeg`, or `.png` metadata path. |
| `media_alt_text` | with media | Required non-empty alt text when `media_path` is present. |
| `media_platforms` | no | Optional requested-platform subset separated by a pipe character; blank targets all row platforms. |

The import accepts an optional UTF-8 byte-order mark for spreadsheet compatibility. It does not
guess encodings, delimiters, headers, locale dates, workspace timezones, or queue slots. The input
is capped at 1,000,000 bytes and 100 data rows, matching the existing plan bound. Blank rows,
malformed row shapes, empty list elements such as `x||linkedin`, and unknown UTC offsets are
reported rather than silently skipped.

This first source-authoring contract deliberately omits per-platform variants, link-tracking maps,
limit overrides, and multiple images. Add those advanced fields to the generated campaign JSON
after import, then use normal semantic diff and review. The optional media path is metadata relative
to its generated campaign file; import neither opens nor copies image bytes. Exact pixel review
remains an explicit later `--include-media` operation.

## Validation and failure behavior

`inspect_campaign_plan_csv(...)` decodes and parses at most the declared byte ceiling, validates
the plan name and required-platform policy, and checks every accepted logical data row. Its
`CampaignPlanImportCheck` reports stable issue codes plus optional row and field locations. Logical
row numbers include the header as row 1.

No output path is touched when inspection fails. On success,
`export_campaign_plan_import(...)` writes a private temporary sibling and reloads the complete plan
through the authoritative runtime validator. It then atomically reserves the absent destination,
publishes each file without replacement, and publishes `plan.json` last as the completeness marker.
It refuses an existing or concurrently created destination instead of merging, deleting, or
overwriting source work. An I/O failure cleans only shapes created by that call.

`plan import --json` emits the check object and plan identity on success. Invalid input emits the
schema-backed `plan-import-check` object and returns exit `1`; it still writes no package. Use
`samsarix-campaign schema --kind plan-import` for the diagnostic schema.

## Product rationale and current workflow evidence

Bulk spreadsheet authoring is a common entry path, but connected tools make different assumptions:

- [Buffer bulk upload](https://support.buffer.com/article/926-how-to-upload-posts-in-bulk-to-buffer)
  uses a case-sensitive template, one post per row, optional posting time, a review screen, and an
  error CSV; current paid uploads accept up to 100 posts per channel.
- [Planable import](https://help.planable.io/hc/en-us/articles/21715324907804-Import-posts-in-Planable)
  accepts a predefined CSV below 1 MB and 400 rows, with workspace-timezone date interpretation and
  a bounded set of post/media types.
- [Hootsuite bulk scheduling](https://help.hootsuite.com/hc/de/articles/1260804306069-Create-and-schedule-content-in-a-calendar)
  positions CSV bulk composition as a way to prepare hundreds of calendar posts.

Samsarix keeps the familiar spreadsheet entry point but produces provider-neutral, Git-reviewable
source instead of scheduling remote posts. The conservative 100-row/1 MB envelope, explicit
offsets, existing campaign validation, and exclusive package write avoid silent plan-limit truncation,
locale-dependent times, partial imports, and account coupling. This evidence supports the workflow
need; it does not establish external-user adoption or claim direct compatibility with a provider's
template.

## Trust boundary

CSV cells are untrusted content, never commands, templates, environment substitutions, or paths
except for the existing strictly portable media metadata field. Import performs no network access,
media dereference, spreadsheet evaluation, publishing, or scheduling. Formula-looking input is
preserved as literal source text; later Samsarix CSV export continues to neutralize formula prefixes
for spreadsheet viewing. Generated JSON may contain private draft text and should inherit the same
repository and filesystem protections as hand-authored campaign sources.
