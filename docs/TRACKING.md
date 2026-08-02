# Deterministic link tracking

Samsarix Creative Spirals 0.12 can append bounded, source-controlled query parameters to the
structured campaign link while it renders each platform draft. The result is visible before
approval and remains part of campaign identity, semantic diffs, plans, exports, adapters,
handoffs, and readiness reports.

This feature builds attribution URLs. It does not contact an analytics service, collect a click,
shorten a link, follow a redirect, install a tracking pixel, or prove that a destination site is
configured to record the parameters.

## Why this slice exists

Link attribution is a normal campaign-operations task:

- Google Analytics documents manual campaign parameters, recommends consistent case-sensitive
  naming, and specifically recommends `utm_source`, `utm_medium`, and `utm_campaign` when manual
  tagging is used:
  <https://support.google.com/analytics/answer/10917952?hl=en>.
- Buffer can automatically add and, on paid plans, customize UTM parameters for supported social
  channels:
  <https://support.buffer.com/article/518-understanding-utm-parameters-and-google-analytics>.
- Sprout Social provides saved link-tracking parameter sets, per-network values, URL matching,
  previews, and custom parameters on its connected publishing platform:
  <https://support.sproutsocial.com/hc/en-us/articles/202703663-How-do-I-use-Link-Tracking>.

Those systems attach attribution at a connected account or hosted composer. Samsarix handles the
earlier, Git-native boundary: the exact URL is generated deterministically from reviewed source
without an account, owner role, paid analytics plan, or network request.

## Runnable example

```bash
samsarix-campaign validate examples/campaign-tracking.json --json
samsarix-campaign preview examples/campaign-tracking.json --json
samsarix-campaign diff examples/campaign.json examples/campaign-tracking.json --json
samsarix-campaign check examples/campaign-tracking.json --json
```

The example uses common campaign values for every platform and a distinct `utm_source` override:

```json
{
  "link": "https://samsarix.com#creative-spirals",
  "linkTracking": {
    "parameters": {
      "utm_campaign": "creative-spirals-0-12",
      "utm_content": "product-release",
      "utm_medium": "organic-social"
    },
    "platformParameters": {
      "x": {"utm_source": "x"},
      "linkedin": {"utm_source": "linkedin"}
    }
  }
}
```

For X, the resulting structured link is:

```text
https://samsarix.com?utm_campaign=creative-spirals-0-12&utm_content=product-release&utm_medium=organic-social&utm_source=x#creative-spirals
```

Parameters are sorted by name, encoded with UTF-8 percent encoding, appended after any existing
query string, and inserted before a URL fragment. Platform parameters replace common values with
the same name and add new values for that platform.

## Version 1 contract

`linkTracking` is optional and has two optional members, at least one of which must be non-empty:

- `parameters`: common parameter names and values;
- `platformParameters`: parameter maps for requested platforms.

The combined effective map for any platform contains at most 20 parameters. Names are lowercase
ASCII and match `[a-z][a-z0-9_-]{0,63}`. Values are normalized to NFC, trimmed, non-empty,
single-line strings of at most 200 characters. The complete tracked URL is at most 2,000
characters.

The contract accepts ordinary UTM names and bounded custom names; it does not hard-code one
analytics provider. Values are literal. There are no placeholders, environment substitutions,
template expressions, random identifiers, timestamps, or remote lookups, so equal normalized
campaign source always produces equal URLs and identities.

## Link selection and conflicts

Tracking applies only to the structured `link` field used by the effective content block:

- a platform variant with its own `link` receives that platform's parameters;
- a platform without a variant uses the baseline `link` and its platform parameters;
- a complete variant that omits `link` intentionally has no tracked link;
- URL-looking text inside `body` or `title` is never scanned or rewritten.

At least one requested platform must have an effective link when `linkTracking` is present. If an
effective link already contains a parameter with a name the tracking configuration would add,
validation fails instead of silently replacing it or emitting ambiguous duplicates. Remove the
source query parameter or remove that name from `linkTracking` and review the resulting semantic
diff.

## Identity, review, and downstream artifacts

Normalized tracking configuration is part of campaign source hashing. Changing a common or
platform value changes the campaign ID, every affected rendered draft, nested plan identity, and
approval validity. Semantic diff reports `linkTracking` plus affected draft content.

No new adapter, manifest, approval, handoff, or readiness schema is needed: those existing
contracts already bind normalized source identity and exact rendered draft text. Handoff
verification regenerates and checks the tracked URL bytes immediately before downstream use.

## Security and privacy boundary

Query parameters are public campaign content. Do not place secrets, access tokens, email
addresses, user IDs, or other personal data in them. Samsarix rejects URL credentials and control
characters, but it cannot decide whether a literal value is commercially sensitive or personal.

The package never opens the destination, validates ownership, checks redirect retention, or
confirms analytics ingestion. A downstream publisher can still rewrite or shorten links, and a
destination or redirect can discard parameters. Preview the exact draft, test the destination in
the intended environment, and verify analytics configuration separately.

Tracking makes URLs longer. X and Mastodon retain their documented fixed URL weight, while other
platform limits count the rendered URL text under the existing conservative formatter rules.
Samsarix may therefore truncate body text that previously fit; the ordinary quality gate makes
that modification visible.

## Compatibility and migration

Campaign schema version 1 gains only optional `linkTracking`. Sources that omit it normalize,
hash, render, and export as before. To adopt it:

1. choose a lowercase naming convention and confirm the destination analytics requirements;
2. add common values plus explicit platform source values;
3. run `preview` and `diff`, checking fragments, existing queries, and platform limits;
4. create new approval and handoff evidence because attribution changes rendered content; and
5. keep the values stable for the reporting period to avoid fragmented analytics rows.

Remove `linkTracking` to restore the unmodified structured links. Previously generated approval
and handoff evidence remains tied to the old exact source and should not be edited in place.
