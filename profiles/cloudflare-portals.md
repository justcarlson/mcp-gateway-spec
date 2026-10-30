# Profile: Cloudflare MCP server portals

How [SPEC.md](../SPEC.md) maps onto [Cloudflare MCP server portals][S40]: a hosted edge that puts many MCP servers behind one URL, with Cloudflare Access policies. Portals are usually an [edge](../SPEC.md#11-edge-exposure) in front of a gateway, but can also act as a small gateway on their own.

This profile maps rules to features as documented on 2026-10-30. It does not claim that portals conform; run the checker on your own portal.

## Mapping

| Spec term | Portal |
|---|---|
| View | Portal (one URL, up to 80 servers), filtered by Access policy |
| Group | Server added to the portal |
| Slug | Server ID; the portal prefixes tools with `{server_id}_` |
| Exposed name | `{server_id}_{tool}`, or an alias |
| Discovery mode | Flat by default; code mode by admin policy: `off`, `opt_in`, `default_on`, or `enforced`, with `?codemode=` for the client to choose within it [S40], [S20] |
| Edge allowlist | Per-server tool enablement |
| Metadata cache | The portal's copy of each server's tool list |

## Naming ([EDGE-2])

- Choose server IDs that meet [GRP-2]: `^[a-z][a-z0-9]{1,19}$`. The portal joins the ID and tool name with one `_`, which matches [ADR-0001](../docs/decisions/0001-prefix-separator.md).
- Aliases override names with precedence `portal_alias` > `server_alias` > `alias` [S40]. Use them to fix names you cannot change upstream, and keep one alias record per tool ([VIEW-9]).
- Check the prefixed names, not the upstream ones, against [NAME-5]: the prefix counts toward 64 characters.

## In front of a gateway

When the portal fronts a gateway such as [Executor](executor.md), expose only the gateway's meta-tools through it, plus any composite adapter tools:

| Server | Allowlist | Exposed as |
|---|---|---|
| Gateway (`gateway`) | `skills`, `search`, `describe`, `call`, `execute`, `resume` | `gateway_search`, `gateway_call`, ... |
| Adapters (`adapters`) | Each reviewed adapter tool | `adapters_<verb>_<object>` |

- Keep an explicit allowlist per server and keep new tools disabled until reviewed ([EDGE-1]).
- Give the portal its own gateway credential, scoped to a view built for the portal ([EDGE-4], [SEC-4]).
- The portal must not approve calls on a person's behalf; approvals pause in the gateway and reach a person ([EDGE-7]).
- Adapter tools follow this spec like any other tool, and a caller map lists the gateway paths each adapter calls ([EDGE-5], [CHG-8]).
- The checker skips [NAME-8] for a server whose exposed tools are all meta-tools, since passing them through is the point. It still flags a meta-tool name inside an ordinary server, such as `adapters_search`.
- Adapter names like `<domain>_<verb>` (for example `media_request`) give [NAME-4] info findings. These are advice, not errors. To record the choice, waive them:

```toml
[[waiver]]
rule = "NAME-4"
target = "adapters"
reason = "Adapter names are domain first, so related tools sort together"
owner = "edge maintainers"
expires = 2027-04-15
```

## Server instructions

The portal does not pass server instructions through. Its `initialize` result has empty `instructions`, even after a sync, so [DISC-10] and [DISC-11] cannot pass at a portal edge. Put that guidance somewhere the agent still sees it:

- in tool descriptions, for short rules about one tool;
- in a skill, if the agent's client loads skills;
- in the gateway behind the portal, which the agent reads through its own meta-tools (for example Executor's `skills`).

Verified on 2026-10-30: after `cf mcp servers sync`, the portal drops `instructions` but keeps each tool's `title` and `outputSchema`.

## Metadata sync ([EDGE-3])

The portal serves its cached copy of each server's tools. After an upstream change to names, descriptions, schemas, or hints, sync the server in the portal, then compare:

```sh
# upstream.json: tools/list from the server; edge.json: tools/list from the portal
mcp-gateway-check diff upstream.json edge.json --mode sync --strip-prefix gateway_
```

Any EDGE-3 finding means the portal still serves stale metadata.

## Checking a portal

```sh
MCP_TOKEN=... mcp-gateway-check check https://portal.example/mcp --namespace prefix
```

`--namespace prefix` splits each name at the first `_` into server ID and tool. Use `--header-env` for headers other than `Authorization`, for example a service token:

```sh
CF_ID=... CF_SECRET=... mcp-gateway-check check https://portal.example/mcp \
  --namespace prefix --header-env CF-Access-Client-Id=CF_ID --header-env CF-Access-Client-Secret=CF_SECRET
```

Header values come from the environment, never from the command line ([DEP-2]).

The checker sends `User-Agent: mcp-gateway-check/<version>`. A request with no User-Agent can get a 403 from Cloudflare's browser integrity check. Use `--user-agent` to send another value; a `--header-env User-Agent=ENV` header wins over both.

[S20]: https://blog.cloudflare.com/code-mode-mcp/ "Cloudflare blog: Code Mode for MCP"
[S40]: https://developers.cloudflare.com/cloudflare-one/access-controls/ai-controls/mcp-portals/ "Cloudflare: MCP server portals"
[GRP-2]: ../SPEC.md#grp-2
[NAME-4]: ../SPEC.md#name-4
[NAME-5]: ../SPEC.md#name-5
[NAME-8]: ../SPEC.md#name-8
[DISC-10]: ../SPEC.md#disc-10
[DISC-11]: ../SPEC.md#disc-11
[VIEW-9]: ../SPEC.md#view-9
[EDGE-1]: ../SPEC.md#edge-1
[EDGE-2]: ../SPEC.md#edge-2
[EDGE-3]: ../SPEC.md#edge-3
[EDGE-4]: ../SPEC.md#edge-4
[EDGE-5]: ../SPEC.md#edge-5
[EDGE-7]: ../SPEC.md#edge-7
[CHG-8]: ../SPEC.md#chg-8
[SEC-4]: ../SPEC.md#sec-4
[DEP-2]: ../SPEC.md#dep-2
