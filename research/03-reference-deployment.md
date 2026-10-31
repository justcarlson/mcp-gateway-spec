# Reference deployment: an anonymized case study (2026-10-30)

One real, self-hosted gateway was inventoried read-only before this spec was written. This file keeps the findings that shaped the rules. Hostnames, accounts, key paths, repository names, and private app names are left out; app names below are public products or generic labels.

The checker was later run on a dump of the same gateway's tool metadata. The dump is not in this repo.

## Shape

- **Gateway:** Executor (stock image, pinned by digest), path-namespaced: `tools.<slug>.<tool>`, reached through `skills`, `search`, `describe`, `call`, `execute`, and `resume`.
- **Groups:** 38 authored apps, plus catalog apps that the Executor catalog owns and overwrites on update. The checker dump covered 55 groups and 2,853 tools.
- **Edge:** a Cloudflare MCP server portal. It exposes the gateway's six meta-tools through an allowlist, plus a second server of 10 composite adapter tools. The portal prefixes each tool with `<server_id>_`.
- **Views:** app-level audiences generated from one JSON file (a personal view, per-host views, a service view, and a five-app canary view). Tool-level limits live in app source.
- **Deploy:** image digest in a lock file; a script uploads each app and connects its account. New apps start private until the view script runs.

## How apps were built

| Form | Count and size | Descriptions |
|---|---|---|
| Wraps an MCP server (own, community, or vendor) | Most apps; one vendor app has 196 tools | Passed through from the server |
| Wraps an MCP server, filtered to an allowlist | 9 apps from one vendor stack, 9-243 tools each, one shared token | Passed through |
| OpenAPI | 4+ apps, some importing a whole spec | From the spec |
| Hand-written | 2 apps, 5-9 tools | Terse ("All books") |

Approvals were declared in app code: `always()` for anything not marked read-only, with a few recorded exceptions (a preview-or-ask helper and one `never()` for a low-risk subscribe action).

## What went wrong, and the rule it led to

| Finding | Rule |
|---|---|
| One app had 243 tools; three had more than 100 | [GRP-4](../SPEC.md#grp-4), [DISC-2](../SPEC.md#disc-2) |
| Names in four styles: snake_case, kebab (`resolve-library-id`), camel inside snake (`cmd_album_addPhotos`), and double underscore with Pascal case (`llm__GetDateTime`) | [NAME-3](../SPEC.md#name-3) |
| Tools named `search`, `execute`, and `describe_command` inside a gateway whose meta-tools are `search`, `describe`, and `execute` | [NAME-8](../SPEC.md#name-8) |
| Tool names that repeat the slug: `firecrawl_*`, `unifi_*`, `browser_*` | [NAME-7](../SPEC.md#name-7) |
| Kebab slugs forced bracket syntax in code (`tools["media-requests"]`) and broke the single-`_` prefix | [GRP-2](../SPEC.md#grp-2), [ADR-0003](../docs/decisions/0003-group-slug-charset.md) |
| A movie request tool lived in a music request app | [GRP-5](../SPEC.md#grp-5) |
| Two apps for the same DNS filter type, lab and production, differed only by instance | [GRP-8](../SPEC.md#grp-8) |
| Seven apps shared one upstream token; two more shared another | [VIEW-10](../SPEC.md#view-10), [SEC-5](../SPEC.md#sec-5) |
| Boilerplate "Writes ask for approval" on apps whose tools are all read-only | [DESC-8](../SPEC.md#desc-8) |
| Three apps had one-line descriptions; three had none | [DESC-9](../SPEC.md#desc-9) |
| Two descriptions over 4,096 characters, one of 11,620 | [DESC-3](../SPEC.md#desc-3) |
| Two tools marked both read-only and destructive, so they ran without approval | [ANN-2](../SPEC.md#ann-2), [ANN-4](../SPEC.md#ann-4) |
| 23 catalog tools whose prefixed names pass 64 characters | [NAME-5](../SPEC.md#name-5) |
| Edge adapters called gateway paths directly; a rename would break them silently | [CHG-8](../SPEC.md#chg-8), [EDGE-5](../SPEC.md#edge-5) |
| The portal served a cached copy of descriptions and schemas until someone ran a sync | [EDGE-3](../SPEC.md#edge-3) |
| One large code-mode program crashed the gateway with an out-of-memory error | [DEP-9](../SPEC.md#dep-9) |
| Views file comments and docs still described the previous gateway | [DEP-10](../SPEC.md#dep-10) |
| 196 catalog tools in one scraping app carried the upstream API version: `v1_twitter_tweet` (checked on 2026-10-31) | [NAME-11](../SPEC.md#name-11) |
| A phone client was asked about a shared social post and did not use the gateway until the user named it. It saw only the meta-tools, and neither the search description nor the instructions said what the gateway can do | [DISC-12](../SPEC.md#disc-12) |
| The answer needed a second tool (the post's video transcript), and nothing in the first tool's description named it | [DISC-13](../SPEC.md#disc-13) |
| Each site had its own tools, with no single entry for "read this URL" | [DISC-14](../SPEC.md#disc-14) |
| The only written naming rule covered edge adapters (`<domain>_<verb>`); nothing covered apps | This spec |

## What worked

- Approvals in code, failing closed for anything not marked read-only ([ANN-4](../SPEC.md#ann-4)).
- An explicit edge allowlist with new tools disabled by default ([EDGE-1](../SPEC.md#edge-1)).
- Image pinned by digest with a lock file ([DEP-1](../SPEC.md#dep-1)).
- A small canary view used for post-deploy checks ([DEP-8](../SPEC.md#dep-8)).
- Views generated from one file ([VIEW-7](../SPEC.md#view-7)).

## Checker run on the dump

`mcp-gateway-check` on 2,853 tools in 55 groups (path namespace, progressive discovery) found 54 errors, 9,521 warnings, and 1,694 info findings before waivers with v0.1.0. Most warnings came from upstream servers the owner does not control (missing hints, missing titles, short descriptions), which is why [waivers](../SPEC.md#conf-2) carry an owner and an expiry.

v0.1.1 found 635 errors, 9,520 warnings, and 1,694 info findings on the same dump. The new errors are [ANN-4](../SPEC.md#ann-4): v0.1.0 read the admin `readOnly` field as the approval state, but it is the tool's kind. With `approval` taken from app source, 581 mutations in 12 apps run without approval because the app uses `never()`. These findings are correct: each needs approval or an [ANN-7](../SPEC.md#ann-7) exception record. The checker also listed 648 tools with no approval data and 55 groups with no instruction text as "not checked".
