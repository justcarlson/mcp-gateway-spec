# MCP gateway survey (GitHub, 2026-10-30)

Source: research agent pass, stars and push dates from `gh api` on 2026-10-30.
Items marked "unverified" or "inference" were not confirmed against primary sources.

## Consensus in one paragraph

The server is the namespace, and an admin-defined *view* (group, profile, virtual
server, toolset) picks a subset of tools across servers. Each view has its own
URL, and identity policy filters both `tools/list` and `tools/call`. The projects
disagree on progressive discovery: most use search -> describe -> call/execute,
but GitHub removed dynamic toolsets, IBM closed its meta-tool proposal, and
Stainless went code-mode only.

## Ranked

| # | Project | Stars / last push / license | Unit above tool | Tool name scheme | Discovery | Policy and approvals |
|---|---|---|---|---|---|---|
| 1 | samanhappy/mcphub | 2604 / 10-30 / Apache-2.0 | group -> server; URL per group, per user, `$smart/{group}` | `server-tool` (separator configurable) or original | `search_tools`, `describe_tool`, `call_tool` + pinned tools | allow/deny on user, key, group, server, tool; deny wins; fails closed |
| 2 | IBM/mcp-context-forge | 4730 / 10-30 / Apache-2.0 | virtual server (tools, resources, prompts, A2A agents) | `gateway-tool`; `custom_name`; SEP-986 regex check | flat only | RBAC, pre/post plugin hooks, elicitation |
| 3 | speakeasy-api/gram | 275 / 10-30 / AGPL-3.0 | toolset + tool-variations group | sanitized `[a-z0-9_-]` | `progressive`, `direct`, `code_mode` | `confirm` always/session/never per tool |
| 4 | Cloudflare MCP server portals (hosted; codemode lib in cloudflare/agents 5917, MIT) | n/a | portal (up to 80 servers) | `{server_id}_{tool}`; 3 alias levels | code mode policy off/opt_in/default_on/enforced | Access policies per server |
| 5 | agentgateway/agentgateway | 5810 / 10-30 / Apache-2.0 | route -> `targets[]` | `{target}_{tool}`; `prefixMode` | flat | CEL on `mcp.tool.name` + JWT claims; filters the list |
| 6 | github/github-mcp-server (single server) | 34098 / 10-30 / MIT | toolset (~21) | flat snake_case; deprecated aliases kept | static; dynamic toolsets removed 2026-05-20 (commit 0f0506d2) | read-only mode, token-scope filtering, lockdown |
| 7 | UsefulSoftwareCo/executor (was RhysSullivan) | 4301 / 10-30 / MIT | app (slug namespace) | `tools.<app>.<tool>` paths | `skills`, `search`, `describe`, `call`, `execute`, `resume` | approvals declared in code per operation |
| 8 | docker/mcp-gateway | 1617 / 10-26 / MIT | profile (shareable OCI artifact) | none by default; optional `prefix__tool`; collision = error | `mcp-find`, `mcp-add`, `mcp-exec`, `code-mode`, `find-tools` | invoke check fails closed; interceptors |
| | Kuadrant/mcp-gateway | 108 / 10-28 / Apache-2.0 | registration (category + hint); virtual server | user-chosen prefix | `discover_tools`, `select_tools` above a tool-count threshold | Kuadrant AuthPolicy |
| | maximhq/bifrost | 9230 / 10-30 / Apache-2.0 | MCP client scoped by virtual key | `client-tool` | code mode (Starlark, `.pyi` stubs) | `tools_to_auto_execute` |
| | 1mcp-app/agent | 525 / 10-30 / Apache-2.0 | tags + presets | `server_1mcp_tool`, 64-char cap, hash fallback | lazy `tool_list`, `tool_schema`, `tool_invoke` | none found |
| | metatool-ai/metamcp | 2737 / 06-22 (quiet) / MIT | namespace -> endpoint | `Server__tool` | flat | middleware; no approvals |
| | ComposioHQ/composio (Rube) | 30836 / 10-30 / MIT | session -> toolkit -> tags | `TOOLKIT_ACTION` | `SEARCH_TOOLS`, `GET_TOOL_SCHEMAS`, `MULTI_EXECUTE_TOOL` | `require_approval` by toolkit/tool/tag (experimental) |

Stale/dead: mcp-router archived (2026-09-18); Klavis Strata (last push 2026-06-01)
and metamcp quiet 4-5 months. Little surface shaping: lasso, sparfenyuk and tbxark
mcp-proxy, Pomerium, Microsoft mcp-gateway. Pomerium's `mcp_tool` policy checks
only `tools/call`, so denied tools likely still list (inference).
https://www.pomerium.com/docs/capabilities/mcp/limit-mcp-tools

## What each top project does best

1. mcphub: most complete self-hosted shaping. Group-scoped search, pinned tools,
   per-group instructions, `hiddenParams`, policy applied before search ranking and
   at call time. https://github.com/samanhappy/mcphub/blob/main/docs/features/smart-routing.mdx
   https://github.com/samanhappy/mcphub/blob/main/src/utils/toolPolicy.ts
2. ContextForge: per-tool override of name, description (<= 8192 chars), all four
   hints, `jsonpath_filter` on output; RBAC.
   https://github.com/IBM/mcp-context-forge/blob/main/docs/docs/using/tool-annotations.md
3. Gram: per-tool "variation" overrides `name`, `title`, `description`, `tags`,
   all four hints, `confirm`, `confirm_prompt`, `summarizer`.
   https://github.com/speakeasy-api/gram/blob/main/server/design/shared/variations.go
   Discovery mode enum: https://github.com/speakeasy-api/gram/blob/main/server/internal/mcp/metamcp/discovery_mode.go
4. Cloudflare portals: client picks discovery mode under admin policy; alias
   precedence `portal_alias` > `server_alias` > `alias`.
   https://developers.cloudflare.com/cloudflare-one/access-controls/ai-controls/mcp-portals/
5. agentgateway: CEL policy filters what each caller sees; `prefixMode`; merges
   server instructions. https://github.com/agentgateway/agentgateway/blob/main/examples/mcp-authorization/config.yaml
6. github-mcp-server: reference grouping model. Composable scoping by header or URL
   (`/x/{toolset}/readonly`); exclude and read-only win; instructions generated from
   enabled toolsets. https://github.com/github/github-mcp-server/blob/main/docs/server-configuration.md
   https://github.com/github/github-mcp-server/blob/main/pkg/github/toolset_instructions.go
7. Executor: approvals keyed on intent (e.g. `destructiveHint` -> `always()`); each
   app's instructions become a skill. https://executor.sh/docs/concepts/tools-and-approvals
   Unverified: public `main` registers `integrations`, `search`, `invoke`, `execute`,
   `resume`, `skills`; V2 apps source not found there.
   https://github.com/UsefulSoftwareCo/executor/blob/main/packages/hosts/mcp/src/tool-server.ts
8. Docker: profiles shareable as OCI artifacts; agent can provision servers itself.
   https://github.com/docker/mcp-gateway/blob/main/docs/profiles.md

## Spec state as seen by gateway projects

- SEP-986 (Final): names 1-128 chars from `[A-Za-z0-9_.-]` (SHOULD). No `/`.
  Aggregators SHOULD prefix with a server identifier, not `serverInfo.name`.
  https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/specification/2026-07-28/server/tools.mdx
- Grouping: SEP-2084 "Primitive Grouping" closed unmerged 2026-02-05. Progressive
  Disclosure WG decisions (2026-10-27, pre-SEP): primitive named `group`; stateless
  `group/list`, `group/get`; `description` = when to use, optional `instructions` = how.
  https://github.com/modelcontextprotocol/progressive-disclosure-wg/blob/main/docs/decisions.md
- Revision 2026-07-28 is stateless; list results no longer vary per connection.
  This works against session-state discovery (Kuadrant `select_tools`, Docker
  `mcp-add`, Cloudflare toggles) and favours views scoped by URL or header.
  https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/specification/2026-07-28/changelog.mdx
- Skills extension SEP-2640 (`skills/list`, `skills/get`) is Final.

## Common 2026 shape

- Hierarchy: view -> server/app namespace -> tool. A view has one stable URL;
  identity filtering applies on top.
- Naming: `server__tool` most common (Docker, metamcp, MCPJungle, agent-router).
  Others: `_` (agentgateway, Cloudflare), `-` (ContextForge, mcphub, Bifrost), `___`
  (gh-aw-mcpg), `.` paths (Executor). agentgateway and agent-router added a `Never`
  prefix mode because MCP Apps call tools by original names.
  https://github.com/theagentrouter/agent-router/blob/main/docs/proposals/012-mcp-tool-name-prefix-mode/proposal.md
- Descriptions pass through by default, overridable per view; instructions at group
  level. gh-aw-mcpg uses `[serverID] desc`.
- Schemas usually pass through. Trimming is rare: mcphub `hiddenParams`, ContextForge
  `jsonpath_filter`, Strata `include_output_fields`. Hint overrides exist in metamcp,
  ContextForge, Gram, Kong.
- Discovery: search returns names/descriptions/tags; describe returns schemas; call
  runs one or many; execute runs code. 3-6 meta-tools typical.
  - GitHub removed dynamic toolsets 2026-05-20: progressive disclosure belongs to the
    client/model API (e.g. Anthropic tool search `defer_loading`).
  - Stainless benchmark (31 tasks): SDK code mode 98% vs dynamic meta-tools 70%.
    https://www.stainless.com/blog/sdk-code-mode/
  - Anthropic: 85% fewer upfront tokens with tool search.
    https://www.anthropic.com/engineering/advanced-tool-use
- Approvals: annotations are becoming the policy key. The gateway must enforce
  approvals itself, because behind one `call_tool` the client makes a single approval
  decision for every tool (mcphub documents this).

## Patterns worth copying

1. Pinned tools beside the meta-tools, with policy applied before ranking (mcphub).
   `{"name":"production","servers":[{"name":"time","tools":"all","pinnedTools":["get_current_time"]}]}`
2. One override record per tool per view: name, title, description, four hints,
   confirm mode, summarizer (Gram variations).
3. Discovery mode set by admin policy, chosen by client (Cloudflare off/opt_in/
   default_on/enforced + `?codemode=`; Gram enum; Kuadrant threshold switch).
   https://github.com/Kuadrant/mcp-gateway/blob/main/docs/guides/tool-discovery.md
4. Composable view scoping + generated instructions (GitHub toolsets).
5. Names that always meet the spec: `__` prefix, a `Never` mode, hash fallback when a
   name breaks the rules (1mcp `prefix_1mcp_<sha256[:40]>`, 64-char cap).
   https://github.com/1mcp-app/agent/blob/main/src/utils/core/toolNames.ts

## Sources

Every link above, in order of first use. Each was opened and checked against the claim it supports on the date shown. The weekly link check reopens them.

- https://www.pomerium.com/docs/capabilities/mcp/limit-mcp-tools (verified on 2026-10-30)
- https://github.com/samanhappy/mcphub/blob/main/docs/features/smart-routing.mdx (verified on 2026-10-30)
- https://github.com/samanhappy/mcphub/blob/main/src/utils/toolPolicy.ts (verified on 2026-10-30)
- https://github.com/IBM/mcp-context-forge/blob/main/docs/docs/using/tool-annotations.md (verified on 2026-10-30)
- https://github.com/speakeasy-api/gram/blob/main/server/design/shared/variations.go (verified on 2026-10-30)
- https://github.com/speakeasy-api/gram/blob/main/server/internal/mcp/metamcp/discovery_mode.go (verified on 2026-10-30)
- https://developers.cloudflare.com/cloudflare-one/access-controls/ai-controls/mcp-portals/ (verified on 2026-10-30)
- https://github.com/agentgateway/agentgateway/blob/main/examples/mcp-authorization/config.yaml (verified on 2026-10-30)
- https://github.com/github/github-mcp-server/blob/main/docs/server-configuration.md (verified on 2026-10-30)
- https://github.com/github/github-mcp-server/blob/main/pkg/github/toolset_instructions.go (verified on 2026-10-30)
- https://executor.sh/docs/concepts/tools-and-approvals (verified on 2026-10-30)
- https://github.com/UsefulSoftwareCo/executor/blob/main/packages/hosts/mcp/src/tool-server.ts (verified on 2026-10-30)
- https://github.com/docker/mcp-gateway/blob/main/docs/profiles.md (verified on 2026-10-30)
- https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/specification/2026-07-28/server/tools.mdx (verified on 2026-10-30)
- https://github.com/modelcontextprotocol/progressive-disclosure-wg/blob/main/docs/decisions.md (verified on 2026-10-30)
- https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/specification/2026-07-28/changelog.mdx (verified on 2026-10-30)
- https://github.com/theagentrouter/agent-router/blob/main/docs/proposals/012-mcp-tool-name-prefix-mode/proposal.md (verified on 2026-10-30)
- https://www.stainless.com/blog/sdk-code-mode/ (verified on 2026-10-30)
- https://www.anthropic.com/engineering/advanced-tool-use (verified on 2026-10-30)
- https://github.com/Kuadrant/mcp-gateway/blob/main/docs/guides/tool-discovery.md (verified on 2026-10-30)
- https://github.com/1mcp-app/agent/blob/main/src/utils/core/toolNames.ts (verified on 2026-10-30)
