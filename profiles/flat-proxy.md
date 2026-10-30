# Profile: flat-list proxies (agentgateway, mcphub, and similar)

How [SPEC.md](../SPEC.md) maps onto gateways that merge several MCP servers into one prefixed tool list: [agentgateway][S41], [mcphub][S52], [IBM ContextForge][S37], the [Docker MCP gateway][S45], and others. Facts come from the [gateway survey](../research/01-gateway-survey.md) of 2026-10-30.

This profile maps rules to features. It does not claim that any of these products conforms; run the checker on your own deployment.

## Mapping

| Spec term | agentgateway | mcphub | ContextForge | Docker MCP gateway |
|---|---|---|---|---|
| View | Route, with CEL policy on `mcp.tool.name` and JWT claims [S41] | Group, at its own URL; `$smart/{group}` for search [S35] | Virtual server [S37] | Profile [S45] |
| Group | Target | Server | Gateway (upstream) | Server |
| Prefix | `{target}_{tool}`; `prefixMode` can turn it off [S41] | `server-tool`, separator configurable | `gateway-tool`; `custom_name` | None by default; optional `prefix__tool` |
| Discovery | Flat | Flat, or `search_tools`, `describe_tool`, `call_tool` with pinned tools [S35] | Flat | Flat, plus `mcp-find`, `mcp-add`, `mcp-exec` |
| Policy | Filters list and call | Allow/deny on user, key, group, server, tool; deny wins; fails closed [S36] | RBAC, plugin hooks | Invoke check fails closed |
| Per-tool overrides | No | `hiddenParams` | Name, description, four hints, `jsonpath_filter` [S37] | No |

## Settings that meet the spec

1. **Separator `_` ([EDGE-2], [ADR-0001](../docs/decisions/0001-prefix-separator.md)).** agentgateway uses it by default. Set mcphub's separator to `_`. ContextForge and Docker use other separators; if you cannot change them, run the checker with `--separator` set to theirs and record a waiver for EDGE-2.
2. **Target or server names that meet [GRP-2].** They become the prefix: `^[a-z][a-z0-9]{1,19}$`.
3. **Keep prefixes on ([EDGE-6]).** Turn them off only for tools that MCP Apps call by their original names.
4. **Filter both list and call ([VIEW-2]).** agentgateway's CEL and mcphub's policy do both. A proxy that checks only `tools/call` still lists denied tools; the survey found this likely for Pomerium [S51].
5. **One URL per view ([VIEW-1]).** mcphub groups and agentgateway routes each have their own URL. Avoid session toggles such as `mcp-add` ([DISC-8]); revision 2026-07-28 is stateless.
6. **Stay under the flat limits ([DISC-1], [DISC-2]).** Past 10 tools, use mcphub's smart routing or a client with tool search. Past 50 tools or 25,000 tokens, flat is not allowed.
7. **Approvals in the gateway ([ANN-5]).** Behind mcphub's `call_tool` the client makes one approval decision for every tool, so the gateway must enforce approvals itself [S35]. Proxies without an approval feature need a client that asks per tool, and a view that holds only reviewed tools.
8. **Hints ([ANN-1], [ANN-3]).** Where the proxy supports hint overrides (ContextForge), use them for the reviewed classification. Otherwise fix hints upstream.

## Checking a flat proxy

```sh
MCP_TOKEN=... mcp-gateway-check check https://proxy.example/mcp --namespace prefix
```

For a proxy with a different separator:

```sh
mcp-gateway-check check tools.json --namespace prefix --separator -
```

The checker reports Level 1 and Level 2 results for the checked rules, and DISC-1 and DISC-2 against the whole list.

## Add your gateway

Copy this file, fill in the mapping table from the product's docs, cite each fact, and open a pull request. See [CONTRIBUTING.md](../CONTRIBUTING.md#add-a-profile).

[S35]: https://github.com/samanhappy/mcphub/blob/main/docs/features/smart-routing.mdx "mcphub: Smart routing"
[S36]: https://github.com/samanhappy/mcphub/blob/main/src/utils/toolPolicy.ts "mcphub: toolPolicy.ts"
[S37]: https://github.com/IBM/mcp-context-forge/blob/main/docs/docs/using/tool-annotations.md "IBM ContextForge: Tool annotations"
[S41]: https://github.com/agentgateway/agentgateway/blob/main/examples/mcp-authorization/config.yaml "agentgateway: MCP authorization example"
[S45]: https://github.com/docker/mcp-gateway/blob/main/docs/profiles.md "Docker MCP Gateway: Profiles"
[S51]: https://www.pomerium.com/docs/capabilities/mcp/limit-mcp-tools "Pomerium: Limit MCP tools"
[S52]: https://github.com/samanhappy/mcphub "mcphub"
[GRP-2]: ../SPEC.md#grp-2
[EDGE-2]: ../SPEC.md#edge-2
[EDGE-6]: ../SPEC.md#edge-6
[VIEW-1]: ../SPEC.md#view-1
[VIEW-2]: ../SPEC.md#view-2
[DISC-1]: ../SPEC.md#disc-1
[DISC-2]: ../SPEC.md#disc-2
[DISC-8]: ../SPEC.md#disc-8
[ANN-1]: ../SPEC.md#ann-1
[ANN-3]: ../SPEC.md#ann-3
[ANN-5]: ../SPEC.md#ann-5
