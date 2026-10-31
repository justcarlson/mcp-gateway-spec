# MCP Gateway Specification

**Version:** 0.2.0 · **Status:** Draft for use · **Date:** 2026-10-31 · **MCP revisions:** [2026-07-28][S1] (target), [2025-11-25][S62]

This specification sets rules for an MCP gateway's tool surface and operations: naming, grouping, descriptions, schemas, approvals, discovery, views, edge exposure, change management, deployment, observability, and security. Read it before you change a gateway's tools, groups, descriptions, approvals, edge exposure, or deployment, and before you set up a gateway for a new client.

The rules apply to any gateway product. [Profiles](profiles/) map them onto [Executor](profiles/executor.md), [Cloudflare MCP server portals](profiles/cloudflare-portals.md), and [flat-list proxies](profiles/flat-proxy.md) such as agentgateway, mcphub, IBM ContextForge, and the Docker MCP gateway. Custom gateways use the rules directly.

## Contents

1. [Conventions](#1-conventions)
2. [Scope and terms](#2-scope-and-terms)
3. [Model](#3-model)
4. [Naming](#4-naming)
5. [Grouping](#5-grouping)
6. [Descriptions and group instructions](#6-descriptions-and-group-instructions)
7. [Schemas, responses, and errors](#7-schemas-responses-and-errors)
8. [Annotations and approvals](#8-annotations-and-approvals)
9. [Discovery modes](#9-discovery-modes)
10. [Views, scoping, and identity](#10-views-scoping-and-identity)
11. [Edge exposure](#11-edge-exposure)
12. [Change management](#12-change-management)
13. [Deployment and operations](#13-deployment-and-operations)
14. [Observability](#14-observability)
15. [Security](#15-security)
16. [Conformance](#16-conformance)
17. [Rule index](#17-rule-index)
18. [Sources](#18-sources)

## 1. Conventions

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "NOT RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in BCP 14 ([RFC 2119][S64], [RFC 8174][S65]) when, and only when, they appear in all capitals, as shown here.

Each rule has:

- a stable ID (`NAME-1`) that never changes meaning; retired IDs are not reused;
- a level (**MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**, or **MAY**);
- `checked` when [`mcp-gateway-check`](README.md#30-second-quick-start) tests it, or `manual` when a reviewer tests it with the [change checklist](templates/change-review-checklist.md);
- the MCP revisions it applies to: `MCP 2025-11-25+` means that revision and every later one; `MCP 2025-11-25 only` means that revision alone. [upstream.json](upstream.json) lists the supported revisions and the target, and `mcp-gateway-check --mcp-revision` skips rules outside the window. The [rule index](#17-rule-index) lists every window;
- a one-line rationale (*Why*) and its evidence (*Source*). Numbered sources are in [section 18](#18-sources). The [research notes](research/) summarize them.

A rule that says "SHOULD" can be broken with a recorded reason. A rule that says "MUST" can be broken only with a [waiver](#conf-2).

Six decisions with real trade-offs have their own records in [docs/decisions/](docs/decisions/):

| ADR | Decision |
|---|---|
| [0001](docs/decisions/0001-prefix-separator.md) | Gateway-added prefixes use a single `_`: `<slug>_<tool>` |
| [0002](docs/decisions/0002-verb-noun-order.md) | Tool names put the verb first: `search_issues` |
| [0003](docs/decisions/0003-group-slug-charset.md) | Group slugs match `^[a-z][a-z0-9]{1,19}$` |
| [0004](docs/decisions/0004-name-length-budget.md) | Exposed names at most 64 characters, target 48; tool names target 32 |
| [0005](docs/decisions/0005-group-and-view-thresholds.md) | At most 10 tools per group; flat views at most 10 tools and 10,000 tokens; never flat past 50 tools or 25,000 tokens |
| [0006](docs/decisions/0006-description-length-budget.md) | Tool descriptions 80-1,024 characters (hard limit 4,096); group descriptions at most 300; instructions at most 2,048 (hard limit 4,096) |

## 2. Scope and terms

This spec covers the surface a gateway presents to MCP clients and the way it is changed and run. It does not change the MCP protocol. Where the protocol and this spec differ, the protocol wins and this spec is the bug.

**Gateway.** A server that aggregates tools from one or more upstreams and serves them to MCP clients, adding policy, naming, discovery, or approvals. Examples: Executor, Cloudflare MCP server portals, agentgateway, mcphub, IBM ContextForge, Docker MCP gateway.

**Upstream.** A source of tools behind the gateway: an MCP server, an OpenAPI service, or code inside the gateway.

**Group.** The unit above a tool: one domain, one owner, one slug, usually one upstream and one credential. Products call it an app (Executor), a server or target (Cloudflare, agentgateway), a namespace, or a toolset. MCP has no group primitive; the Progressive Disclosure Working Group has agreed on the name `group` and a description/instructions split, but no spec text exists yet ([S7], [S46]).

**Slug.** The group's stable identifier. It becomes the gateway prefix (`tracker_search_issues`) or the path segment (`tools.tracker.search_issues`).

**Tool.** An MCP tool as defined by the protocol: `name`, `title`, `description`, `inputSchema`, `outputSchema`, `annotations`, `_meta` ([S1]).

**Exposed name.** The name a flat client sees, with any gateway prefix: `<slug>_<tool>`. Path-namespaced gateways have no exposed name on the wire, but edges and adapters often create one, so the rules budget for it.

**View.** A named subset of groups and tools served to one audience at one stable URL or credential. Products call it a profile, a virtual server, a portal, a toolset, or an audience.

**Meta-tool.** A tool that operates on other tools: `search`, `describe`, `call`, `execute`, `resume`, `skills`, or a product's equivalent.

**Discovery mode.** How a view reaches the model: *flat* (every tool listed), *progressive* (search, describe, call), or *code* (the model writes a program that calls tools).

**Edge.** A layer in front of the gateway that re-exposes its tools to other clients: a hosted portal, a reverse proxy with MCP awareness, or an adapter service. An edge often adds a prefix, an allowlist, and a metadata cache.

**Owner.** The person or team that may change a group's tools, descriptions, and approvals.

## 3. Model

```
client ──► edge (optional) ──► gateway view ──► group ──► tool ──► upstream
            prefix, allowlist,   URL or           slug,      name, schema,
            metadata cache       credential       owner      hints, approval
                                 discovery mode
                                 meta-tools
```

A view selects groups (and optionally single tools) and fixes a discovery mode. Each group holds tools for one domain. Every tool call passes the view's policy and the gateway's approval check, whatever path it takes: a direct call, a `call` meta-tool, a code-mode program, or an edge adapter. The [README diagram](README.md#the-model) links each part to its source.

## 4. Naming

#### NAME-1
**MUST** · checked · MCP 2025-11-25+ · Every tool name is 1-128 characters from `[A-Za-z0-9_.-]`, with no spaces or `/`.
*Why:* the MCP spec fixes this format and clients reject other names. *Source:* [S1], [S6].

#### NAME-2
**MUST** · checked · MCP 2025-11-25+ · Tool names are unique within a view, compared without regard to case.
*Why:* clients key tools by name, and some fold case or rewrite characters before they compare. *Source:* [S1], [S13].

#### NAME-3
**SHOULD** · checked · MCP 2025-11-25+ · Tool names are snake_case (`^[a-z][a-z0-9]*(_[a-z0-9]+)*$`). In path-namespaced gateways every path segment is an identifier.
*Why:* Claude and OpenAI function-name patterns reject dots, Claude Code rewrites other characters to `_`, and code-mode paths need identifiers. *Source:* [S12], [S13], [S18].

#### NAME-4
**SHOULD** · checked · MCP 2025-11-25+ · Tool names put the verb first, then the object: `search_issues`, `get_issue`, `create_issue`. See [ADR-0002](docs/decisions/0002-verb-noun-order.md).
*Why:* one order everywhere lets models and people predict names, and OpenAI and Block examples use verb first. *Source:* [S8], [S16], [S22], [S25].

#### NAME-5
**MUST** · checked · MCP 2025-11-25+ · Exposed names, including any gateway prefix, are at most 64 characters.
*Why:* OpenAI rejects longer function names, and a name that only some clients accept breaks the view. *Source:* [S18], [ADR-0004](docs/decisions/0004-name-length-budget.md).

#### NAME-6
**SHOULD** · checked · MCP 2025-11-25+ · Exposed names are at most 48 characters, and tool names without a prefix are at most 32.
*Why:* clients add their own prefix, such as `mcp__<server>__` in Claude Code, which uses up the rest of the 64. *Source:* [S13], [ADR-0004](docs/decisions/0004-name-length-budget.md).

#### NAME-7
**SHOULD NOT** · checked · MCP 2025-11-25+ · A tool name repeats its group slug (`firecrawl_scrape` in group `firecrawl`, or `pihole_stats` in `pihole`).
*Why:* the gateway already adds the slug, so the repeat wastes the name budget and doubles in prefixed lists. *Source:* [S1], [S61].

#### NAME-8
**SHOULD NOT** · checked · MCP 2025-11-25+ · A tool name equals a meta-tool name of its gateway (`search`, `describe`, `call`, `execute`, `resume`, `skills`).
*Why:* a tool named `search` inside a gateway whose meta-tool is `search` confuses models and people reading logs. *Source:* [S61].

#### NAME-9
**SHOULD** · manual · MCP 2025-11-25+ · Names are specific and easy to tell apart: `search_customer_orders`, not `query_db_orders`; no two tools in a view differ by one word that a user would not say.
*Why:* models choose tools by name first, and lookalike names cause wrong calls. *Source:* [S8], [S9].

#### NAME-10
**SHOULD** · checked · MCP 2025-11-25+ · Every tool has a `title`: a short human label such as "Get issue details".
*Why:* clients show the title in approval prompts and tool lists. *Source:* [S1], [S16].

#### NAME-11
**SHOULD NOT** · checked · MCP 2025-11-25+ · A tool name, or a segment of a path name, starts with an upstream API version: `v1_twitter_tweet`, `v2beta_get_user`, or `api.v1.users`. Name the tool for the task (`get_tweet`), and keep the version in the group's upstream configuration.
*Why:* the version is the upstream's routing detail, not a word a user says. It uses up the name budget, pushes the verb out of first place ([NAME-4](#name-4)), and forces a rename ([CHG-1](#chg-1)) when the upstream moves to `v2`. *Source:* [S8], [S15], [S61].

## 5. Grouping

#### GRP-1
**MUST** · manual · MCP 2025-11-25+ · Every tool belongs to exactly one group, and every group has one named owner.
*Why:* someone must decide on each change, and a tool in two groups gets two sets of rules. *Source:* [S7], [S46].

#### GRP-2
**MUST** · checked · MCP 2025-11-25+ · Group slugs match `^[a-z][a-z0-9]{1,19}$`: a lowercase letter, then lowercase letters and digits, 2-20 characters. See [ADR-0003](docs/decisions/0003-group-slug-charset.md).
*Why:* it is the one form that works as an Executor slug, a JavaScript and Python identifier, a DNS label, and a prefix that a single `_` separates without ambiguity. *Source:* [S1], [S44], [S61].

#### GRP-3
**MUST** · manual · MCP 2025-11-25+ · A slug, once published, does not change except through [change management](#12-change-management) with aliases and a migration plan for accounts, views, and grants.
*Why:* callers, adapters, and credentials refer to the slug. *Source:* [S34], [S61].

#### GRP-4
**SHOULD** · checked · MCP 2025-11-25+ · A group has at most 10 tools. Split larger groups by sub-domain or by risk, or filter the upstream to the tools the audience needs. See [ADR-0005](docs/decisions/0005-group-and-view-thresholds.md).
*Why:* OpenAI targets fewer than 10 functions per namespace, and large groups bury the right tool. *Source:* [S17], [S11].

#### GRP-5
**SHOULD** · manual · MCP 2025-11-25+ · A group covers one domain, and every tool in it fits the group description. A movie request tool does not live in a music group.
*Why:* models read the group description to decide whether to look inside. *Source:* [S4], [S61].

#### GRP-6
**SHOULD** · checked · MCP 2025-11-25+ · Each tool has one risk level. Reads and writes are separate tools (`issue_read`, `issue_write`), and an `action` or `method` enum does not mix reads with writes.
*Why:* approvals and read-only views work per tool, so a mixed tool forces the strictest policy on every call. *Source:* [S12], [S16], [S22], [S25].

#### GRP-7
**SHOULD** · manual · MCP 2025-11-25+ · Tools that are always called in a fixed sequence are merged into one workflow tool, and each tool matches one user goal.
*Why:* fewer round trips and fewer chances to call them in the wrong order. *Source:* [S8], [S16].

#### GRP-8
**SHOULD** · manual · MCP 2025-11-25+ · Groups that serve the same upstream type for different instances (lab and production) say so in their descriptions and use the same slug pattern (`dnslab`, `dnsprod`).
*Why:* without it the model cannot tell which instance a call reaches. *Source:* [S61].

## 6. Descriptions and group instructions

A group has two texts, matching the Progressive Disclosure WG decision ([S46]): the **description** says *when* to use the group, and the optional **instructions** say *how*. Tool descriptions follow the [tool description template](templates/tool-description.md).

#### DESC-1
**MUST** · checked · MCP 2025-11-25+ · Every tool has a non-empty description.
*Why:* search, ranking, and the model's choice all read the description. *Source:* [S1], [S11].

#### DESC-2
**SHOULD** · checked · MCP 2025-11-25+ · A tool description is 80-1,024 characters: the first sentence, when to use it, when not to (with the alternative), inputs, and returns. See [ADR-0006](docs/decisions/0006-description-length-budget.md).
*Why:* Anthropic asks for at least three or four sentences, and clients truncate long text. *Source:* [S12], [S15], [S13].

#### DESC-3
**MUST** · checked · MCP 2025-11-25+ · A tool description is at most 4,096 characters.
*Why:* Claude Code truncates descriptions of tools loaded at startup at 4,096 characters, and long text costs tokens on every request. *Source:* [S13].

#### DESC-4
**SHOULD** · checked · MCP 2025-11-25+ · The first sentence states the verb, object, and scope in words a user would type, in at most 160 characters.
*Why:* search matches names and descriptions, and truncation keeps only the start. *Source:* [S11], [S13], [S16].

#### DESC-5
**SHOULD** · manual · MCP 2025-11-25+ · When tools overlap, each says "Use this when ..." and "Do not use for ... (use `other_tool`)".
*Why:* explicit routing text is the main fix for wrong-tool calls. *Source:* [S15], [S26].

#### DESC-6
**SHOULD** · manual · MCP 2025-11-25+ · Descriptions give input formats, units, defaults, and where IDs come from; the shape and size of the result; and paging or truncation. Complex inputs get one to three example calls.
*Why:* examples raised accuracy from 72% to 90% in Anthropic's tests, and MCP has no separate examples field. *Source:* [S9], [S12], [S26].

#### DESC-7
**MUST NOT** · checked · MCP 2025-11-25+ · Names, titles, descriptions, or instructions contain hidden directives ("ignore previous instructions", text aimed at the model that the user would not see), secrets, or private hostnames and addresses.
*Why:* tool metadata goes straight into the model's context and into logs and screenshots. *Source:* [S5], [S53].

#### DESC-8
**MUST NOT** · checked · MCP 2025-11-25+ · Descriptions or group text claim safety behavior that the gateway does not enforce: "read-only" on a tool that writes or asks for approval, or "writes ask for approval" on a group whose tools all run without approval.
*Why:* models and reviewers trust these claims, and a false one hides real risk or adds noise. *Source:* [S5], [S61].

#### DESC-9
**MUST** · checked · MCP 2025-11-25+ · Every group has a description that says when to use the group: its domain, the questions it answers, and what it is not for.
*Why:* in progressive and code modes the group description is often the only text the model sees before it searches. *Source:* [S4], [S33], [S46].

#### DESC-10
**SHOULD** · checked · MCP 2025-11-25+ · A group description is at most 300 characters, in one or two sentences.
*Why:* it is repeated in every listing, and the WG keeps "how" text in instructions. *Source:* [S46], [S16].

#### DESC-11
**SHOULD** · checked · MCP 2025-11-25+ · Group instructions say how to use the group: call order, cross-tool rules, limits, and when to search. Keep them under 2,048 characters with the critical text in the first 512.
*Why:* clients load instructions eagerly and cut them short. *Source:* [S4], [S13], [S16], [S19].

#### DESC-12
**MUST** · checked · MCP 2025-11-25+ · Group instructions are at most 4,096 characters.
*Why:* Claude Code truncates server instructions at 4,096 characters. *Source:* [S13].

#### DESC-13
**MUST NOT** · manual · MCP 2025-11-25+ · Instructions repeat tool descriptions or act as a security control ("never call delete without asking").
*Why:* models may ignore instructions; only the gateway enforces policy. *Source:* [S4], [S5].

#### DESC-14
**SHOULD** · manual · MCP 2025-11-25+ · Workflow guidance longer than the instruction budget lives in a skill (MCP Skills extension or the gateway's skill feature), not in instructions.
*Why:* skills load on demand, so long guidance does not cost tokens on every request. *Source:* [S31], [S44].

## 7. Schemas, responses, and errors

#### SCHEMA-1
**MUST** · checked · MCP 2025-11-25+ · `inputSchema` is a JSON Schema object with `"type": "object"`.
*Why:* the MCP spec requires it, and clients fail on anything else. *Source:* [S1].

#### SCHEMA-2
**SHOULD** · checked · MCP 2025-11-25+ · A tool without arguments uses `{"type": "object", "additionalProperties": false}`.
*Why:* it tells the model to send nothing and lets the gateway reject stray input. *Source:* [S1].

#### SCHEMA-3
**SHOULD** · checked · MCP 2025-11-25+ · Every input property has a description; closed sets use `enum`.
*Why:* the model fills arguments from these texts. *Source:* [S8], [S15].

#### SCHEMA-4
**SHOULD** · checked · MCP 2025-11-25+ · Parameter names are descriptive (`user_id`, not `user`) and use one style per group, snake_case by default.
*Why:* mixed styles in one group cause wrong argument names. *Source:* [S8].

#### SCHEMA-5
**SHOULD** · checked · MCP 2025-11-25+ · Input schemas are flat and inline, without `$ref` or `$defs`.
*Why:* revision 2026-07-28 allows JSON Schema 2020-12, but client support for references varies. *Source:* [S2].

#### SCHEMA-6
**SHOULD** · manual · MCP 2025-11-25+ · Only the true minimum is required; filters and paging have sensible defaults.
*Why:* every required field is a chance for the model to invent a value. *Source:* [S8].

#### SCHEMA-7
**MUST NOT** · checked · MCP 2025-11-25+ · Input schemas ask the model for credentials (`api_key`, `token`, `password`) or for values the gateway injects (account IDs, tenant IDs). The gateway supplies them and hides them.
*Why:* secrets in arguments end up in model context and logs. *Source:* [S53], [S35].

#### SCHEMA-8
**SHOULD** · manual · MCP 2025-11-25+ · Tools with structured results declare `outputSchema`, return `structuredContent` that conforms, and also return the same data as text.
*Why:* the spec requires conformance when a schema is declared, and text keeps older clients working. *Source:* [S1].

#### SCHEMA-9
**SHOULD** · manual · MCP 2025-11-25+ · Responses stay under 10,000 tokens. Tools paginate (cursor, or page and limit up to 100), filter, and truncate; a truncated result says how to narrow the request. Offer `response_format: concise | detailed` where it helps.
*Why:* Claude Code warns at 10,000 tokens and caps at 25,000; concise formats cut tokens by two thirds in Anthropic's test. *Source:* [S8], [S13], [S22], [S25].

#### SCHEMA-10
**MUST** · manual · MCP 2025-11-25+ · Tool failures return a result with `isError: true` and a message that says what to change. Protocol errors are only for protocol faults.
*Why:* the model can read and correct a tool error, but not a protocol error. *Source:* [S1], [S8].

#### SCHEMA-11
**SHOULD** · manual · MCP 2025-11-25+ · Rate-limit errors include `retry_after_seconds`.
*Why:* the model can wait instead of retrying at once. *Source:* [S27].

#### SCHEMA-12
**SHOULD** · manual · MCP 2025-11-25+ · Results carry stable IDs for follow-up calls, with readable names beside them. A tool that creates a stateful handle states its lifetime, and expiry errors say what to do.
*Why:* follow-up calls need IDs, and people read names. *Source:* [S1], [S8], [S16].

## 8. Annotations and approvals

Annotations are hints. MCP says clients must treat them as untrusted unless the server is trusted ([S1], [S5]). A gateway is the trusted party for its clients, so it reviews upstream hints and enforces approvals itself. Behind one `call` meta-tool, the client can make only one approval decision for every tool, which is why the gateway has to do it ([S35]).

#### ANN-1
**SHOULD** · checked · MCP 2025-11-25+ · Every tool sets all four hints explicitly: `readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint`.
*Why:* missing hints default to the worst case, and OpenAI requires three of them. *Source:* [S3], [S5], [S14].

#### ANN-2
**MUST** · checked · MCP 2025-11-25+ · `readOnlyHint: true` is set only on tools without side effects, and never together with `destructiveHint: true`.
*Why:* clients run read-only tools in parallel, retry them, and skip confirmation. *Source:* [S3], [S13], [S19].

#### ANN-3
**MUST** · manual · MCP 2025-11-25+ · The gateway treats upstream hints as untrusted input to its own review. The reviewed classification, not the upstream hint, sets the approval policy.
*Why:* an upstream can change or misstate hints at any time. *Source:* [S1], [S5], [S14].

#### ANN-4
**MUST** · checked · MCP 2025-11-25+ · A tool that has not been reviewed as read-only requires approval by default. Unknown or missing classification means approval required.
*Why:* failing closed limits the damage of a missed review. *Source:* [S5], [S44].

#### ANN-5
**MUST** · manual · MCP 2025-11-25+ · The gateway enforces approval on every call path: direct calls, the `call` meta-tool, each call inside a code-mode program, edge adapters, and scheduled jobs.
*Why:* one unguarded path defeats every other check. *Source:* [S35], [S44].

#### ANN-6
**SHOULD** · manual · MCP 2025-11-25+ · Approval prompts show the tool, group, account, and arguments in readable form.
*Why:* people approve what they can read. *Source:* [S1], [S38].

#### ANN-7
**MUST** · manual · MCP 2025-11-25+ · Every exception that lets a write run without approval is recorded in source with a reason and a reviewer.
*Why:* exceptions are where approval mistakes hide. *Source:* [S44], [S61].

#### ANN-8
**SHOULD** · manual · MCP 2025-11-25+ · `idempotentHint: true` is set only when a repeat call is safe, and `openWorldHint: false` only for a bounded private workspace.
*Why:* clients use these hints to decide on retries and on how to frame results. *Source:* [S3], [S15].

## 9. Discovery modes

| Mode | Shape | Use when | Evidence |
|---|---|---|---|
| Flat | Every tool in `tools/list` | View has at most 10 tools and 10,000 tokens of definitions | [S11] |
| Progressive | `search`, `describe`, `call` (and optional pinned tools) | More than 10 tools or 10,000 tokens | Anthropic: tool search cut ~77K to ~8.7K tokens and raised accuracy from 79.5% to 88.1% [S9] |
| Code | `search`, `describe`, `execute` (the model writes code) | Many tools, chained calls, or large results to filter | Code execution: 150K to 2K tokens [S10]; Cloudflare ~2,500 endpoints in ~1,000 tokens [S20]; Stainless 98% vs 70% for meta-tools [S49] |

#### DISC-1
**SHOULD** · checked · MCP 2025-11-25+ · A view is served flat only when it has at most 10 tools and at most 10,000 tokens of tool definitions. See [ADR-0005](docs/decisions/0005-group-and-view-thresholds.md).
*Why:* Anthropic recommends tool search above these numbers. *Source:* [S9], [S11].

#### DISC-2
**MUST NOT** · checked · MCP 2025-11-25+ · A view with more than 50 tools or more than 25,000 tokens of definitions is served flat.
*Why:* selection accuracy degrades past 30-50 tools, and VS Code caps a request at 128. *Source:* [S11], [S23], [S24].

#### DISC-3
**MUST** · manual · MCP 2025-11-25+ · In progressive mode, search returns exact tool names or paths, describe returns full schemas, and call accepts exactly those names.
*Why:* the model copies names from search results, so any difference breaks the call. *Source:* [S9], [S10], [S35].

#### DISC-4
**MUST** · manual · MCP 2025-11-25+ · Search and describe apply view policy before ranking, so hidden tools never appear, even in counts or "did you mean" hints.
*Why:* a search result is a disclosure. *Source:* [S35], [S36].

#### DISC-5
**SHOULD** · manual · MCP 2025-11-25+ · A progressive view pins at most five frequently used tools beside the meta-tools, and pinned tools obey the same policy.
*Why:* the most common calls skip a search round trip. *Source:* [S9], [S13], [S35].

#### DISC-6
**MUST** · manual · MCP 2025-11-25+ · Code mode runs programs in a sandbox with no network or file access except calls through the gateway, applies view policy and approvals to each tool call inside the program, and limits memory and time.
*Why:* a program is many tool calls, each of which needs the same checks. *Source:* [S10], [S20], [S61].

#### DISC-7
**SHOULD** · manual · MCP 2025-11-25+ · In progressive and code modes, server instructions name the groups in the view and say when to search.
*Why:* when tools load lazily, the model needs routing text up front. *Source:* [S33], [S4].

#### DISC-8
**SHOULD NOT** · manual · MCP 2026-07-28+ · Discovery depends on per-session state such as `select_tools`, `mcp-add`, or tool toggles.
*Why:* revision 2026-07-28 is stateless, and `tools/list` may not vary per connection. *Source:* [S2], [S50].

#### DISC-9
**SHOULD** · manual · MCP 2025-11-25+ · The admin sets the allowed discovery modes per view, and a client may choose within them.
*Why:* clients differ in what they handle, and Cloudflare and Gram both work this way. *Source:* [S40], [S39].

#### DISC-10
**MUST** · manual · MCP 2026-07-28+ · The `server/discover` result carries the view's instructions, and they are the same on every request for the same view and credential.
*Why:* revision 2026-07-28 moved instructions from `initialize` to `server/discover`, and there is no session to hold per-connection text. *Source:* [S2], [S3].

#### DISC-11
**SHOULD** · manual · MCP 2025-11-25 only · The `initialize` result carries the view's instructions, and they are the same in every session for the same view and credential.
*Why:* in 2025-11-25 the handshake is the only place for server instructions. *Source:* [S63], [S4].

#### DISC-12
**SHOULD** · manual · MCP 2025-11-25+ · A view that exposes only meta-tools states its capability categories in one short line, in the description of its search tool and in its server instructions ([DISC-10](#disc-10), [DISC-11](#disc-11)): "Reads social posts and video transcripts from a URL, searches the web, manages GitHub issues, and controls the home." The line names categories, not each group or tool, so it stays the same when one tool changes.
*Why:* a client that sees only `search`, `describe`, and `call` cannot tell what the gateway does, so the model does not use it unless the user names it. Some edges drop server instructions, so the search description must carry the line too. *Source:* [S4], [S15], [S33], [S61].

#### DISC-13
**SHOULD** · manual · MCP 2025-11-25+ · A tool that is usually followed by another tool names that tool in its description: "For the spoken text of a video post, call `get_tweet_transcript`." Tools that are always called in sequence are one tool instead ([GRP-7](#grp-7)).
*Why:* in progressive and code modes the model sees only the tools that its search returned, so it does not know that the follow-up tool exists. *Source:* [S8], [S61].

#### DISC-14
**SHOULD** · manual · MCP 2025-11-25+ · A view gives one entry for tasks that start from a URL ("what is this post about?"): a tool that accepts any supported URL and routes it to the correct tool, or a skill that maps each supported site to its tools.
*Why:* users share links more often than they name a site, and without one entry the model must search for each site and choose among many site-specific tools. *Source:* [S8], [S31], [S61].

## 10. Views, scoping, and identity

#### VIEW-1
**MUST** · manual · MCP 2026-07-28+ · A URL path or a credential selects the view. Session toggles do not.
*Why:* revision 2026-07-28 is stateless, and list results may vary by authorization but not by connection. *Source:* [S2], [S42].

#### VIEW-2
**MUST** · manual · MCP 2025-11-25+ · View policy filters every operation: `tools/list`, search, describe, `tools/call`, `call`, and each tool call in `execute`.
*Why:* filtering only the list leaves hidden tools callable by name. *Source:* [S36], [S41], [S52].

#### VIEW-3
**MUST** · manual · MCP 2025-11-25+ · When allow and deny rules both match, deny wins.
*Why:* it is the only order that keeps a deny rule meaningful. *Source:* [S36], [S42].

#### VIEW-4
**MUST** · manual · MCP 2025-11-25+ · Policy fails closed: an unknown identity, a missing policy, or an error while evaluating policy yields no tools and denied calls.
*Why:* open failure turns every policy bug into an exposure. *Source:* [S36], [S45].

#### VIEW-5
**MUST** · manual · MCP 2026-07-28+ · `tools/list` returns the same tools in the same order for the same credential.
*Why:* the spec asks for a fixed order, and caches depend on it. *Source:* [S2].

#### VIEW-6
**MUST** · manual · MCP 2025-11-25+ · A new group starts in no view. Someone adds it to each view on purpose.
*Why:* new tools have not had a risk review. *Source:* [S61].

#### VIEW-7
**SHOULD** · manual · MCP 2025-11-25+ · Views are defined as code in one place, and the gateway's view config is generated from it.
*Why:* hand edits drift, and reviews need a diff. *Source:* [S45], [S61].

#### VIEW-8
**SHOULD** · manual · MCP 2025-11-25+ · Each audience gets the smallest view that serves it, and views that need writes have a read-only variant.
*Why:* least privilege limits what a confused or compromised agent can do. *Source:* [S25], [S42].

#### VIEW-9
**SHOULD** · manual · MCP 2025-11-25+ · Per-view overrides of name, title, description, hints, or approval are one record per tool per view.
*Why:* one record is easy to review and to diff. *Source:* [S38], [S37].

#### VIEW-10
**MUST** · manual · MCP 2025-11-25+ · A view grants upstream accounts only for its own groups. Credentials shared by several groups are listed.
*Why:* a shared credential silently widens every view that holds it. *Source:* [S61].

## 11. Edge exposure

#### EDGE-1
**MUST** · manual · MCP 2025-11-25+ · The edge exposes an explicit allowlist of tool names per upstream. New upstream tools start disabled.
*Why:* an upstream change must not publish tools that nobody reviewed. *Source:* [S40], [S61].

#### EDGE-2
**MUST** · manual · MCP 2025-11-25+ · An edge prefix is `<slug>_` with a slug that meets [GRP-2](#grp-2), and every prefixed name meets [NAME-1](#name-1) and [NAME-5](#name-5). Run the checker on the edge with `--namespace prefix` to test those three rules.
*Why:* the edge's names are the names clients see. *Source:* [S1], [S40], [ADR-0001](docs/decisions/0001-prefix-separator.md).

#### EDGE-3
**MUST** · checked · MCP 2025-11-25+ · After any upstream change to names, descriptions, schemas, or hints, the edge refreshes its metadata cache, and the served copy matches upstream (`mcp-gateway-check diff --mode sync`).
*Why:* some edges serve a cached copy until synced, so clients see stale schemas. *Source:* [S40], [S61].

#### EDGE-4
**MUST** · manual · MCP 2025-11-25+ · The edge authenticates clients on its own and uses its own credential for the gateway. It never passes a client token through.
*Why:* token passthrough breaks audit and lets one token reach services it was not issued for. *Source:* [S53].

#### EDGE-5
**SHOULD** · manual · MCP 2025-11-25+ · Edge adapters (composite tools at the edge) follow this spec, and a caller map lists every gateway path each adapter calls.
*Why:* adapters are the callers most likely to break on a rename. *Source:* [S61].

#### EDGE-6
**SHOULD** · manual · MCP 2025-11-25+ · Unprefixed exposure is used only for tools that MCP Apps call by their original name.
*Why:* prefixes prevent collisions, and agentgateway and agent-router added an unprefixed mode only for this case. *Source:* [S48], [S41].

#### EDGE-7
**MUST NOT** · manual · MCP 2025-11-25+ · The edge auto-approves a call that the gateway would ask a person to approve.
*Why:* the approval must reach a person, not a proxy. *Source:* [S5], [S61].

## 12. Change management

#### CHG-1
**MUST** · checked · MCP 2025-11-25+ · A renamed or removed tool keeps its old name as an alias, or as a deprecated tool, for the deprecation window. `mcp-gateway-check diff` takes an alias file.
*Why:* callers, skills, and saved prompts use the old name. *Source:* [S34], [S16].

#### CHG-2
**MUST** · manual · MCP 2025-11-25+ · The deprecation window lasts at least 30 days and at least one release. A deprecated tool's description starts with "Deprecated: use `new_name`."
*Why:* callers need time and a pointer. *Source:* [S34].

#### CHG-3
**MUST** · checked · MCP 2025-11-25+ · Input schema changes are additive: no removed properties, no new required properties, no narrowed types, and no removed enum values.
*Why:* existing calls must keep working. *Source:* [S16].

#### CHG-4
**SHOULD** · checked · MCP 2025-11-25+ · Output schema changes are additive: no removed fields and no changed types.
*Why:* programs and adapters parse structured output. *Source:* [S16], [S1].

#### CHG-5
**MUST** · manual · MCP 2025-11-25+ · A server that can change its list sends `notifications/tools/list_changed` when it changes.
*Why:* clients reload on the notification; without it they keep the old list. *Source:* [S1], [S13].

#### CHG-6
**MUST** · manual · MCP 2025-11-25+ · Every change to tools, groups, descriptions, approvals, views, edge, or deployment goes through the [change review checklist](templates/change-review-checklist.md), with checker output attached.
*Why:* most surface bugs are visible in review if someone looks. *Source:* [S8], [S61].

#### CHG-7
**SHOULD** · manual · MCP 2025-11-25+ · Each view's surface has a semantic version: major for removals and breaking schemas, minor for additions, patch for text.
*Why:* consumers can pin and read the impact of a change at a glance. *Source:* [S66].

#### CHG-8
**MUST** · manual · MCP 2025-11-25+ · Before a rename or removal, the owner lists every caller of the tool (adapters, scripts, skills, schedules) and tells each caller's owner.
*Why:* a path-based caller fails silently until it runs. *Source:* [S61].

#### CHG-9
**MUST** · checked · MCP 2025-11-25+ · A change that loosens approval (a write reclassified as read-only, `destructiveHint` cleared, or approval removed) gets explicit sign-off from a reviewer who is not the author.
*Why:* it is the one change that can turn an agent mistake into an unapproved write. *Source:* [S5], [S44].

#### CHG-10
**SHOULD** · manual · MCP 2025-11-25+ · Description and naming changes are verified with an eval or at least a canary task before and after.
*Why:* Anthropic found small description changes moved results measurably. *Source:* [S8], [S9].

#### CHG-11
**MUST** · checked · MCP 2026-07-28+ · `tools/list` results set `ttlMs` and `cacheScope` to match how often the list changes and whether it depends on the caller. A list that varies by credential uses `cacheScope: "private"`.
*Why:* revision 2026-07-28 requires both fields, and a shared cache of a per-credential list leaks tools across views. *Source:* [S2], [S3].

## 13. Deployment and operations

#### DEP-1
**MUST** · manual · MCP 2025-11-25+ · The gateway image is pinned by digest, and a lock file in version control records image, tag, digest, and date.
*Why:* tags move; digests do not. *Source:* [S57], [S61].

#### DEP-2
**MUST** · manual · MCP 2025-11-25+ · Secrets live in a secret manager and reach the gateway as environment variables or files at run time. They never appear in git, images, command-line arguments, or logs.
*Why:* argv is visible to every local user through the process list, and git history is forever. *Source:* [S55], [S56].

#### DEP-3
**MUST** · manual · MCP 2025-11-25+ · Gateway state (config, database, app sources) is backed up before every deploy, and a restore is tested on a schedule.
*Why:* an untested backup is a hope. *Source:* [S60], [S61].

#### DEP-4
**MUST** · manual · MCP 2025-11-25+ · The gateway exposes a health check, and a deploy waits for it before it sends traffic.
*Why:* a failed start must not replace a working gateway. *Source:* [S58].

#### DEP-5
**MUST** · manual · MCP 2025-11-25+ · Gateway and sandbox egress go through an allowlist of upstream hosts that fails closed.
*Why:* it limits what a prompt-injected tool call can reach. *Source:* [S54], [S10].

#### DEP-6
**SHOULD** · manual · MCP 2025-11-25+ · Image upgrades are deployed manually. Config and app changes may deploy automatically after CI runs the checker.
*Why:* image upgrades change the meta-tools and approval engine; config changes are reviewed diffs. *Source:* [S58], [S61].

#### DEP-7
**MUST** · manual · MCP 2025-11-25+ · Rollback is written down (previous digest, backup restore) and rehearsed.
*Why:* rollback under pressure without a rehearsal fails. *Source:* [S58].

#### DEP-8
**MUST** · manual · MCP 2025-11-25+ · Each deploy ends with `mcp-gateway-check` on the live endpoint of every changed view and a canary call through a read-only canary view.
*Why:* the live surface is the one clients see, and a canary proves the call path works. *Source:* [S58], [S61].

#### DEP-9
**SHOULD** · manual · MCP 2025-11-25+ · Code execution has memory and time limits, and large jobs are split, for example one `execute` per group.
*Why:* one large program can exhaust the gateway, as the reference deployment saw with an out-of-memory crash. *Source:* [S61].

#### DEP-10
**SHOULD** · manual · MCP 2025-11-25+ · Desired state (views, edge allowlists, image lock) is code, and a scheduled job reports drift from it.
*Why:* drift is invisible until it breaks something. *Source:* [S61].

## 14. Observability

#### OBS-1
**MUST** · manual · MCP 2025-11-25+ · The gateway logs every tool call with time, identity, view, group, tool, approval decision, outcome, and latency.
*Why:* audit and incident response need who called what and who approved it. *Source:* [S53].

#### OBS-2
**MUST NOT** · manual · MCP 2025-11-25+ · Logs contain secrets or full payloads with personal data unless redacted.
*Why:* logs travel further than the gateway. *Source:* [S56].

#### OBS-3
**SHOULD** · manual · MCP 2025-11-25+ · Metrics cover calls, errors, latency, pending approvals, and denials per group and tool.
*Why:* error and denial rates show broken tools and misdirected agents. *Source:* [S58].

#### OBS-4
**SHOULD** · manual · MCP 2025-11-25+ · A synthetic probe calls each public endpoint on a schedule and alerts when `tools/list` changes unexpectedly.
*Why:* metadata drift and upstream rug pulls show up first in the list. *Source:* [S5], [S61].

#### OBS-5
**SHOULD** · manual · MCP 2025-11-25+ · Changes to views, approvals, and edge config are audited with author and time.
*Why:* policy changes need the same trail as code. *Source:* [S53].

#### OBS-6
**SHOULD** · manual · MCP 2025-11-25+ · The gateway propagates W3C trace context to upstreams.
*Why:* one trace across edge, gateway, and upstream shortens debugging. *Source:* [S59].

## 15. Security

#### SEC-1
**MUST** · manual · MCP 2025-11-25+ · Each view is reviewed for the lethal trifecta: access to private data, exposure to untrusted content, and a way to send data out. A view with all three requires approval on every outbound tool, or is split.
*Why:* that combination lets injected text exfiltrate private data. *Source:* [S54], [S5].

#### SEC-2
**MUST** · manual · MCP 2025-11-25+ · Adding a group to a view triggers a cross-app risk review of the new combinations, not only of the new group.
*Why:* each group can be safe alone and dangerous together. *Source:* [S5], [S54].

#### SEC-3
**MUST** · manual · MCP 2025-11-25+ · Upstream metadata is untrusted. A change to an upstream's names, descriptions, schemas, or hints is reviewed before the edge or a view serves it.
*Why:* a server can change its tools after approval (a rug pull). *Source:* [S5], [S53].

#### SEC-4
**MUST NOT** · manual · MCP 2025-11-25+ · The gateway passes client tokens to upstreams. It holds its own credential per upstream.
*Why:* the MCP security guidance forbids token passthrough. *Source:* [S53].

#### SEC-5
**MUST** · manual · MCP 2025-11-25+ · Upstream credentials have the least privilege the group needs. A credential shared by several groups is recorded.
*Why:* a group's blast radius is its credential's scope. *Source:* [S53], [S61].

#### SEC-6
**SHOULD** · manual · MCP 2025-11-25+ · Automation and people use separate views and credentials.
*Why:* unattended agents need narrower access and separate audit trails. *Source:* [S61].

## 16. Conformance

A gateway, view, or edge conforms at one of three levels. Claims are per view.

| Level | Name | Requirement |
|---|---|---|
| 1 | Core | Every MUST and MUST NOT rule passes, or has an unexpired waiver. |
| 2 | Recommended | Level 1, and every SHOULD and SHOULD NOT rule passes or has a recorded reason. |
| 3 | Operated | Level 2, and evidence from the last 30 days for DEP-3, DEP-7, DEP-8, and OBS-4 (backup restore, rollback rehearsal, post-deploy check, probe). |

The checker reports Level 1 and Level 2 for the rules it can test. Manual rules need the [change review checklist](templates/change-review-checklist.md).

#### CONF-1
**MUST** · manual · MCP 2025-11-25+ · A conformance claim names the spec version, the level, the view, and the evidence: the checker report and the completed checklist.
*Why:* a claim without evidence cannot be checked. *Source:* [S66].

#### CONF-2
**MUST** · checked · MCP 2025-11-25+ · A waiver names the rule, the target, a reason, an owner, and an expiry date at most 180 days away. The checker refuses waivers that miss any of these.
*Why:* a waiver without an expiry becomes a permanent exception. *Source:* [S61].

#### CONF-3
**SHOULD** · checked · MCP 2025-11-25+ · Waivers that match nothing or have expired are removed.
*Why:* stale waivers hide new findings that happen to match them. *Source:* [S61].

### Waiver file

```toml
[[waiver]]
rule = "GRP-2"                    # rule ID, or a glob such as "NAME-*"
target = "web-crawl"              # group, tool, or group/tool; globs allowed
reason = "Catalog app; the slug is owned upstream. Rename tracked in #12."
owner = "gateway-team"
expires = 2027-03-31              # TOML date, at most 180 days ahead
```

## 17. Rule index

Generated from the checker's registry; a test keeps the two in step. *MCP until* is inclusive and empty while the rule still applies.

| ID | Level | Test | MCP since | MCP until | Rule |
|---|---|---|---|---|---|
| [NAME-1](#name-1) | MUST | checked | 2025-11-25 |  | Tool names use 1-128 characters from [A-Za-z0-9_.-] |
| [NAME-2](#name-2) | MUST | checked | 2025-11-25 |  | Tool names are unique in a view, ignoring case |
| [NAME-3](#name-3) | SHOULD | checked | 2025-11-25 |  | Tool names are snake_case; namespace segments are identifiers |
| [NAME-4](#name-4) | SHOULD | checked | 2025-11-25 |  | Tool names put the verb first (verb_noun) |
| [NAME-5](#name-5) | MUST | checked | 2025-11-25 |  | Exposed names, with any gateway prefix, are at most 64 characters |
| [NAME-6](#name-6) | SHOULD | checked | 2025-11-25 |  | Exposed names are at most 48 characters; tool names at most 32 |
| [NAME-7](#name-7) | SHOULD NOT | checked | 2025-11-25 |  | Tool names repeat the group slug |
| [NAME-8](#name-8) | SHOULD NOT | checked | 2025-11-25 |  | Tool names reuse a meta-tool name |
| [NAME-9](#name-9) | SHOULD | manual | 2025-11-25 |  | Tool names are specific and easy to tell apart |
| [NAME-10](#name-10) | SHOULD | checked | 2025-11-25 |  | Tools have a human-readable title |
| [NAME-11](#name-11) | SHOULD NOT | checked | 2025-11-25 |  | Tool names start with an upstream API version such as v1_ |
| [GRP-1](#grp-1) | MUST | manual | 2025-11-25 |  | Every tool belongs to exactly one group with one owner |
| [GRP-2](#grp-2) | MUST | checked | 2025-11-25 |  | Group slugs match ^[a-z][a-z0-9]{1,19}$ |
| [GRP-3](#grp-3) | MUST | manual | 2025-11-25 |  | Group slugs are stable; renames follow change management |
| [GRP-4](#grp-4) | SHOULD | checked | 2025-11-25 |  | Groups have at most 10 tools |
| [GRP-5](#grp-5) | SHOULD | manual | 2025-11-25 |  | A group covers one domain; every tool fits its description |
| [GRP-6](#grp-6) | SHOULD | checked | 2025-11-25 |  | Each tool has one risk level; reads and writes are separate tools |
| [GRP-7](#grp-7) | SHOULD | manual | 2025-11-25 |  | Tools that are always chained become one workflow tool |
| [GRP-8](#grp-8) | SHOULD | manual | 2025-11-25 |  | Groups that differ only by instance say so and share a naming pattern |
| [DESC-1](#desc-1) | MUST | checked | 2025-11-25 |  | Every tool has a non-empty description |
| [DESC-2](#desc-2) | SHOULD | checked | 2025-11-25 |  | Tool descriptions are 80-1,024 characters |
| [DESC-3](#desc-3) | MUST | checked | 2025-11-25 |  | Tool descriptions are at most 4,096 characters |
| [DESC-4](#desc-4) | SHOULD | checked | 2025-11-25 |  | The first sentence states verb, object, and scope in at most 160 characters |
| [DESC-5](#desc-5) | SHOULD | manual | 2025-11-25 |  | Overlapping tools say when to use them and which tool to use instead |
| [DESC-6](#desc-6) | SHOULD | manual | 2025-11-25 |  | Descriptions explain inputs, returns, and limits; complex inputs get examples |
| [DESC-7](#desc-7) | MUST NOT | checked | 2025-11-25 |  | Metadata contains hidden directives, secrets, or private endpoints |
| [DESC-8](#desc-8) | MUST NOT | checked | 2025-11-25 |  | Text claims safety behavior that the gateway does not enforce |
| [DESC-9](#desc-9) | MUST | checked | 2025-11-25 |  | Every group has a description that says when to use it |
| [DESC-10](#desc-10) | SHOULD | checked | 2025-11-25 |  | Group descriptions are at most 300 characters |
| [DESC-11](#desc-11) | SHOULD | checked | 2025-11-25 |  | Group instructions say how to use the group in at most 2,048 characters |
| [DESC-12](#desc-12) | MUST | checked | 2025-11-25 |  | Group instructions are at most 4,096 characters |
| [DESC-13](#desc-13) | MUST NOT | manual | 2025-11-25 |  | Instructions repeat tool descriptions or act as a security control |
| [DESC-14](#desc-14) | SHOULD | manual | 2025-11-25 |  | Long workflow guidance lives in a skill, not in instructions |
| [SCHEMA-1](#schema-1) | MUST | checked | 2025-11-25 |  | inputSchema is an object schema |
| [SCHEMA-2](#schema-2) | SHOULD | checked | 2025-11-25 |  | Tools without arguments set additionalProperties to false |
| [SCHEMA-3](#schema-3) | SHOULD | checked | 2025-11-25 |  | Every input property has a description |
| [SCHEMA-4](#schema-4) | SHOULD | checked | 2025-11-25 |  | Parameter names are descriptive and use one style per group |
| [SCHEMA-5](#schema-5) | SHOULD | checked | 2025-11-25 |  | Input schemas are flat and inline, without $ref |
| [SCHEMA-6](#schema-6) | SHOULD | manual | 2025-11-25 |  | Only true minimum inputs are required; filters and paging have defaults |
| [SCHEMA-7](#schema-7) | MUST NOT | checked | 2025-11-25 |  | Input schemas expose credentials or gateway-injected parameters |
| [SCHEMA-8](#schema-8) | SHOULD | manual | 2025-11-25 |  | Structured results declare outputSchema and also return text |
| [SCHEMA-9](#schema-9) | SHOULD | manual | 2025-11-25 |  | Responses stay under 10,000 tokens, paginate, and say how to narrow |
| [SCHEMA-10](#schema-10) | MUST | manual | 2025-11-25 |  | Tool failures return isError results with a fix hint |
| [SCHEMA-11](#schema-11) | SHOULD | manual | 2025-11-25 |  | Rate-limit errors include retry_after_seconds |
| [SCHEMA-12](#schema-12) | SHOULD | manual | 2025-11-25 |  | Results carry stable IDs; stateful handles document their lifetime |
| [ANN-1](#ann-1) | SHOULD | checked | 2025-11-25 |  | Tools set all four annotation hints explicitly |
| [ANN-2](#ann-2) | MUST | checked | 2025-11-25 |  | readOnlyHint is true only for tools without side effects |
| [ANN-3](#ann-3) | MUST | manual | 2025-11-25 |  | The gateway treats upstream hints as untrusted input to its own review |
| [ANN-4](#ann-4) | MUST | checked | 2025-11-25 |  | Tools not reviewed as read-only require approval by default |
| [ANN-5](#ann-5) | MUST | manual | 2025-11-25 |  | The gateway enforces approval on every call path |
| [ANN-6](#ann-6) | SHOULD | manual | 2025-11-25 |  | Approval prompts show tool, group, account, and arguments |
| [ANN-7](#ann-7) | MUST | manual | 2025-11-25 |  | Every approval exception records a reason and a reviewer |
| [ANN-8](#ann-8) | SHOULD | manual | 2025-11-25 |  | idempotentHint and openWorldHint are accurate |
| [DISC-1](#disc-1) | SHOULD | checked | 2025-11-25 |  | Flat views have at most 10 tools and 10,000 tokens of definitions |
| [DISC-2](#disc-2) | MUST NOT | checked | 2025-11-25 |  | Views with more than 50 tools or 25,000 tokens are served flat |
| [DISC-3](#disc-3) | MUST | manual | 2025-11-25 |  | Progressive mode offers search, describe, and call with exact names |
| [DISC-4](#disc-4) | MUST | manual | 2025-11-25 |  | Search and describe apply view policy before ranking |
| [DISC-5](#disc-5) | SHOULD | manual | 2025-11-25 |  | Views pin at most 5 frequent tools beside the meta-tools |
| [DISC-6](#disc-6) | MUST | manual | 2025-11-25 |  | Code mode runs in a sandbox and applies the same approvals per call |
| [DISC-7](#disc-7) | SHOULD | manual | 2025-11-25 |  | Server instructions name the groups and say when to search |
| [DISC-8](#disc-8) | SHOULD NOT | manual | 2026-07-28 |  | Discovery depends on per-session toggles |
| [DISC-9](#disc-9) | SHOULD | manual | 2025-11-25 |  | Admins set the discovery mode per view; clients choose within it |
| [DISC-10](#disc-10) | MUST | manual | 2026-07-28 |  | server/discover returns the view's instructions, the same on every request |
| [DISC-11](#disc-11) | SHOULD | manual | 2025-11-25 | 2025-11-25 | The initialize result returns the view's instructions, the same in every session |
| [DISC-12](#disc-12) | SHOULD | manual | 2025-11-25 |  | A meta-tool-only view states its capabilities in search and instructions |
| [DISC-13](#disc-13) | SHOULD | manual | 2025-11-25 |  | Tools that are usually chained name the follow-up tool |
| [DISC-14](#disc-14) | SHOULD | manual | 2025-11-25 |  | A view has one entry tool or routing skill for URL tasks |
| [VIEW-1](#view-1) | MUST | manual | 2026-07-28 |  | A URL or a credential selects the view |
| [VIEW-2](#view-2) | MUST | manual | 2025-11-25 |  | View policy filters list, search, describe, call, and execute |
| [VIEW-3](#view-3) | MUST | manual | 2025-11-25 |  | Deny wins over allow |
| [VIEW-4](#view-4) | MUST | manual | 2025-11-25 |  | Policy fails closed |
| [VIEW-5](#view-5) | MUST | manual | 2026-07-28 |  | tools/list is deterministic for a given credential |
| [VIEW-6](#view-6) | MUST | manual | 2025-11-25 |  | New groups start in no view |
| [VIEW-7](#view-7) | SHOULD | manual | 2025-11-25 |  | Views are defined as code in one source of truth |
| [VIEW-8](#view-8) | SHOULD | manual | 2025-11-25 |  | Views follow least privilege and offer a read-only variant |
| [VIEW-9](#view-9) | SHOULD | manual | 2025-11-25 |  | Per-view overrides are one record per tool |
| [VIEW-10](#view-10) | MUST | manual | 2025-11-25 |  | A view grants accounts only for its own groups |
| [EDGE-1](#edge-1) | MUST | manual | 2025-11-25 |  | The edge exposes an explicit allowlist; new tools start disabled |
| [EDGE-2](#edge-2) | MUST | manual | 2025-11-25 |  | Edge prefixes are <slug>_ and the result meets the naming rules |
| [EDGE-3](#edge-3) | MUST | checked | 2025-11-25 |  | Edge metadata caches are synced after every upstream change |
| [EDGE-4](#edge-4) | MUST | manual | 2025-11-25 |  | Edge authentication is separate; tokens are never passed through |
| [EDGE-5](#edge-5) | SHOULD | manual | 2025-11-25 |  | Edge adapters follow this spec and are listed in a caller map |
| [EDGE-6](#edge-6) | SHOULD | manual | 2025-11-25 |  | Unprefixed exposure is used only for tools that MCP Apps call by name |
| [EDGE-7](#edge-7) | MUST NOT | manual | 2025-11-25 |  | The edge auto-approves calls that need upstream approval |
| [CHG-1](#chg-1) | MUST | checked | 2025-11-25 |  | Renamed or removed tools keep an alias for the deprecation window |
| [CHG-2](#chg-2) | MUST | manual | 2025-11-25 |  | Deprecation windows last at least 30 days and one release |
| [CHG-3](#chg-3) | MUST | checked | 2025-11-25 |  | Input schema changes are additive |
| [CHG-4](#chg-4) | SHOULD | checked | 2025-11-25 |  | Output schema changes are additive |
| [CHG-5](#chg-5) | MUST | manual | 2025-11-25 |  | Servers announce list changes |
| [CHG-6](#chg-6) | MUST | manual | 2025-11-25 |  | Surface changes pass the review checklist with a checker report |
| [CHG-7](#chg-7) | SHOULD | manual | 2025-11-25 |  | Each view's surface has a semantic version |
| [CHG-8](#chg-8) | MUST | manual | 2025-11-25 |  | Callers of a tool are inventoried and notified before a rename |
| [CHG-9](#chg-9) | MUST | checked | 2025-11-25 |  | Changes that loosen approval get explicit sign-off |
| [CHG-10](#chg-10) | SHOULD | manual | 2025-11-25 |  | Description changes are verified with an eval or a canary |
| [CHG-11](#chg-11) | MUST | checked | 2026-07-28 |  | tools/list results set ttlMs and cacheScope |
| [DEP-1](#dep-1) | MUST | manual | 2025-11-25 |  | Images are pinned by digest and recorded in a lock file |
| [DEP-2](#dep-2) | MUST | manual | 2025-11-25 |  | Secrets live in a secret manager, never in git, images, argv, or logs |
| [DEP-3](#dep-3) | MUST | manual | 2025-11-25 |  | State is backed up before each deploy; restores are tested |
| [DEP-4](#dep-4) | MUST | manual | 2025-11-25 |  | Health checks gate each deploy |
| [DEP-5](#dep-5) | MUST | manual | 2025-11-25 |  | Egress uses an allowlist that fails closed |
| [DEP-6](#dep-6) | SHOULD | manual | 2025-11-25 |  | Image upgrades are manual; config deploys may be automatic behind checks |
| [DEP-7](#dep-7) | MUST | manual | 2025-11-25 |  | Rollback is documented and rehearsed |
| [DEP-8](#dep-8) | MUST | manual | 2025-11-25 |  | Each deploy ends with a live conformance check and a canary call |
| [DEP-9](#dep-9) | SHOULD | manual | 2025-11-25 |  | Code execution has resource limits; large jobs are split |
| [DEP-10](#dep-10) | SHOULD | manual | 2025-11-25 |  | Desired state is code with drift detection |
| [OBS-1](#obs-1) | MUST | manual | 2025-11-25 |  | Every call is logged with identity, view, tool, decision, and outcome |
| [OBS-2](#obs-2) | MUST NOT | manual | 2025-11-25 |  | Logs contain secrets or unredacted payloads |
| [OBS-3](#obs-3) | SHOULD | manual | 2025-11-25 |  | Metrics cover calls, errors, latency, approvals, and denials |
| [OBS-4](#obs-4) | SHOULD | manual | 2025-11-25 |  | A synthetic probe watches each endpoint and alerts on drift |
| [OBS-5](#obs-5) | SHOULD | manual | 2025-11-25 |  | Configuration changes are audited |
| [OBS-6](#obs-6) | SHOULD | manual | 2025-11-25 |  | Trace context propagates to upstreams |
| [SEC-1](#sec-1) | MUST | manual | 2025-11-25 |  | Each view is reviewed for the lethal trifecta |
| [SEC-2](#sec-2) | MUST | manual | 2025-11-25 |  | Adding a group to a view triggers a cross-app risk review |
| [SEC-3](#sec-3) | MUST | manual | 2025-11-25 |  | Upstream metadata is untrusted and re-reviewed when it changes |
| [SEC-4](#sec-4) | MUST NOT | manual | 2025-11-25 |  | The gateway passes client tokens to upstreams |
| [SEC-5](#sec-5) | MUST | manual | 2025-11-25 |  | Upstream credentials are least-privilege; shared ones are recorded |
| [SEC-6](#sec-6) | SHOULD | manual | 2025-11-25 |  | Automation and people use separate views |
| [CONF-1](#conf-1) | MUST | manual | 2025-11-25 |  | Conformance claims name the spec version, level, and evidence |
| [CONF-2](#conf-2) | MUST | checked | 2025-11-25 |  | Waivers name a rule, target, reason, owner, and expiry |
| [CONF-3](#conf-3) | SHOULD | checked | 2025-11-25 |  | Unused and expired waivers are removed |

## 18. Sources

Numbers S1-S34 follow [research/02-standards-guidance.md](research/02-standards-guidance.md); S35-S52 come from [research/01-gateway-survey.md](research/01-gateway-survey.md). *Verified on* is the last date a person or the [link check](.github/workflows/links.yml) confirmed the page still says what the rule cites. MCP revisions are pinned by tag and commit in [upstream.json](upstream.json).

[S1]: https://modelcontextprotocol.io/specification/2026-07-28/server/tools "MCP specification 2026-07-28: Tools"
[S2]: https://modelcontextprotocol.io/specification/2026-07-28/changelog "MCP specification 2026-07-28: Changelog"
[S3]: https://modelcontextprotocol.io/specification/2026-07-28/schema "MCP specification 2026-07-28: Schema reference"
[S4]: https://blog.modelcontextprotocol.io/posts/2025-11-03-using-server-instructions/ "MCP blog: Using server instructions"
[S5]: https://blog.modelcontextprotocol.io/posts/2026-03-16-tool-annotations/ "MCP blog: Tool annotations"
[S6]: https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/seps/986-specify-format-for-tool-names.md "SEP-986: Specify format for tool names"
[S7]: https://modelcontextprotocol.io/community/working-groups/progressive-disclosure "MCP Progressive Disclosure Working Group"
[S8]: https://www.anthropic.com/engineering/writing-tools-for-agents "Anthropic: Writing effective tools for agents"
[S9]: https://www.anthropic.com/engineering/advanced-tool-use "Anthropic: Advanced tool use"
[S10]: https://www.anthropic.com/engineering/code-execution-with-mcp "Anthropic: Code execution with MCP"
[S11]: https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-search-tool "Claude docs: Tool search tool"
[S12]: https://platform.claude.com/docs/en/agents-and-tools/tool-use/define-tools "Claude docs: Define tools"
[S13]: https://code.claude.com/docs/en/mcp "Claude Code docs: MCP"
[S14]: https://developers.openai.com/plugins/reference "OpenAI: Plugins reference"
[S15]: https://developers.openai.com/plugins/guides/optimize-metadata "OpenAI: Optimize metadata"
[S16]: https://developers.openai.com/plugins/build/mcp-server "OpenAI: Build an MCP server"
[S17]: https://developers.openai.com/api/docs/guides/tools-tool-search "OpenAI: Tool search"
[S18]: https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create "OpenAI API reference: Create chat completion"
[S19]: https://learn.chatgpt.com/docs/extend/mcp?surface=cli "Codex docs: MCP"
[S20]: https://blog.cloudflare.com/code-mode-mcp/ "Cloudflare blog: Code Mode for MCP"
[S21]: https://docs.docker.com/ai/mcp-catalog-and-toolkit/dynamic-mcp/ "Docker docs: Dynamic MCP"
[S22]: https://engineering.block.xyz/blog/blocks-playbook-for-designing-mcp-servers "Block: Playbook for designing MCP servers"
[S23]: https://code.visualstudio.com/docs/agents/run/tools "VS Code docs: Agent tools"
[S24]: https://learn.microsoft.com/en-us/azure/developer/azure-mcp-server/concepts "Azure MCP Server concepts"
[S25]: https://github.com/github/github-mcp-server "GitHub MCP Server"
[S26]: https://github.com/getsentry/sentry-mcp/blob/main/packages/mcp-core/src/tools/catalog/get-issue-details.ts "Sentry MCP: get_issue_details"
[S27]: https://developers.notion.com/docs/mcp-supported-tools "Notion MCP supported tools"
[S28]: https://github.com/modelcontextprotocol/modelcontextprotocol/issues/1300 "MCP SEP-1300 (rejected)"
[S29]: https://github.com/modelcontextprotocol/modelcontextprotocol/issues/2084 "MCP SEP-2084: Primitive grouping (rejected)"
[S30]: https://github.com/modelcontextprotocol/modelcontextprotocol/issues/1821 "MCP SEP-1821: Search (closed)"
[S31]: https://github.com/modelcontextprotocol/modelcontextprotocol/issues/2640 "MCP SEP-2640: Skills extension"
[S32]: https://github.com/modelcontextprotocol/modelcontextprotocol/issues/1913 "MCP SEP-1913: Trust and sensitivity annotations (draft)"
[S33]: https://github.com/modelcontextprotocol/modelcontextprotocol/issues/3430 "MCP issue 3430: Routing text for lazily loaded tools"
[S34]: https://github.com/github/github-mcp-server/blob/main/docs/tool-renaming.md "GitHub MCP Server: Tool renaming"
[S35]: https://github.com/samanhappy/mcphub/blob/main/docs/features/smart-routing.mdx "mcphub: Smart routing"
[S36]: https://github.com/samanhappy/mcphub/blob/main/src/utils/toolPolicy.ts "mcphub: toolPolicy.ts"
[S37]: https://github.com/IBM/mcp-context-forge/blob/main/docs/docs/using/tool-annotations.md "IBM ContextForge: Tool annotations"
[S38]: https://github.com/speakeasy-api/gram/blob/main/server/design/shared/variations.go "Gram: Tool variations"
[S39]: https://github.com/speakeasy-api/gram/blob/main/server/internal/mcp/metamcp/discovery_mode.go "Gram: Discovery modes"
[S40]: https://developers.cloudflare.com/cloudflare-one/access-controls/ai-controls/mcp-portals/ "Cloudflare: MCP server portals"
[S41]: https://github.com/agentgateway/agentgateway/blob/main/examples/mcp-authorization/config.yaml "agentgateway: MCP authorization example"
[S42]: https://github.com/github/github-mcp-server/blob/main/docs/server-configuration.md "GitHub MCP Server: Server configuration"
[S43]: https://github.com/github/github-mcp-server/blob/main/pkg/github/toolset_instructions.go "GitHub MCP Server: Toolset instructions"
[S44]: https://executor.sh/docs/concepts/tools-and-approvals "Executor: Tools and approvals"
[S45]: https://github.com/docker/mcp-gateway/blob/main/docs/profiles.md "Docker MCP Gateway: Profiles"
[S46]: https://github.com/modelcontextprotocol/progressive-disclosure-wg/blob/main/docs/decisions.md "Progressive Disclosure WG: Decisions"
[S47]: https://github.com/1mcp-app/agent/blob/main/src/utils/core/toolNames.ts "1mcp: Tool name rules"
[S48]: https://github.com/theagentrouter/agent-router/blob/main/docs/proposals/012-mcp-tool-name-prefix-mode/proposal.md "agent-router: Tool name prefix mode"
[S49]: https://www.stainless.com/blog/sdk-code-mode/ "Stainless: SDK code mode"
[S50]: https://github.com/Kuadrant/mcp-gateway/blob/main/docs/guides/tool-discovery.md "Kuadrant MCP Gateway: Tool discovery"
[S51]: https://www.pomerium.com/docs/capabilities/mcp/limit-mcp-tools "Pomerium: Limit MCP tools"
[S52]: https://github.com/samanhappy/mcphub "mcphub"
[S53]: https://modelcontextprotocol.io/specification/2025-06-18/basic/security_best_practices "MCP specification: Security best practices"
[S54]: https://simonwillison.net/2025/Jun/16/the-lethal-trifecta/ "Simon Willison: The lethal trifecta for AI agents"
[S55]: https://cwe.mitre.org/data/definitions/214.html "CWE-214: Invocation of process using visible sensitive information"
[S56]: https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html "OWASP: Secrets management cheat sheet"
[S57]: https://docs.docker.com/reference/cli/docker/image/pull/#pull-an-image-by-digest-immutable-identifier "Docker docs: Pull an image by digest"
[S58]: https://sre.google/workbook/canarying-releases/ "Google SRE workbook: Canarying releases"
[S59]: https://www.w3.org/TR/trace-context/ "W3C Trace Context"
[S60]: https://sre.google/sre-book/data-integrity/ "Google SRE book: Data integrity"
[S61]: research/03-reference-deployment.md "Anonymized reference deployment (this repo)"
[S62]: https://modelcontextprotocol.io/specification/2025-11-25/server/tools "MCP specification 2025-11-25: Tools"
[S63]: https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle "MCP specification 2025-11-25: Lifecycle"
[S64]: https://www.rfc-editor.org/rfc/rfc2119 "RFC 2119"
[S65]: https://www.rfc-editor.org/rfc/rfc8174 "RFC 8174"
[S66]: https://semver.org/spec/v2.0.0.html "Semantic Versioning 2.0.0"

| ID | Source | Verified on |
|---|---|---|
| S1 | [MCP 2026-07-28: Tools][S1] | 2026-10-30 |
| S2 | [MCP 2026-07-28: Changelog][S2] | 2026-10-30 |
| S3 | [MCP 2026-07-28: Schema][S3] | 2026-10-30 |
| S4 | [MCP blog: Using server instructions][S4] | 2026-10-30 |
| S5 | [MCP blog: Tool annotations][S5] | 2026-10-30 |
| S6 | [SEP-986: Tool name format][S6] | 2026-10-30 |
| S7 | [MCP Progressive Disclosure WG][S7] | 2026-10-30 |
| S8 | [Anthropic: Writing effective tools for agents][S8] | 2026-10-30 |
| S9 | [Anthropic: Advanced tool use][S9] | 2026-10-30 |
| S10 | [Anthropic: Code execution with MCP][S10] | 2026-10-30 |
| S11 | [Claude docs: Tool search tool][S11] | 2026-10-30 |
| S12 | [Claude docs: Define tools][S12] | 2026-10-30 |
| S13 | [Claude Code docs: MCP][S13] | 2026-10-30 |
| S14 | [OpenAI: Plugins reference][S14] | 2026-10-30 |
| S15 | [OpenAI: Optimize metadata][S15] | 2026-10-30 |
| S16 | [OpenAI: Build an MCP server][S16] | 2026-10-30 |
| S17 | [OpenAI: Tool search][S17] | 2026-10-30 |
| S18 | [OpenAI API: Create chat completion][S18] | 2026-10-30 |
| S19 | [Codex docs: MCP][S19] | 2026-10-30 |
| S20 | [Cloudflare: Code Mode for MCP][S20] | 2026-10-30 |
| S21 | [Docker: Dynamic MCP][S21] | 2026-10-30 |
| S22 | [Block: Playbook for MCP servers][S22] | 2026-10-30 |
| S23 | [VS Code: Agent tools][S23] | 2026-10-30 |
| S24 | [Azure MCP Server concepts][S24] | 2026-10-30 |
| S25 | [GitHub MCP Server][S25] | 2026-10-30 |
| S26 | [Sentry MCP: get_issue_details][S26] | 2026-10-30 |
| S27 | [Notion MCP tools][S27] | 2026-10-30 |
| S28 | [SEP-1300][S28] | 2026-10-30 |
| S29 | [SEP-2084: Primitive grouping][S29] | 2026-10-30 |
| S30 | [SEP-1821: Search][S30] | 2026-10-30 |
| S31 | [SEP-2640: Skills][S31] | 2026-10-30 |
| S32 | [SEP-1913: Trust annotations][S32] | 2026-10-30 |
| S33 | [Issue 3430: Routing text][S33] | 2026-10-30 |
| S34 | [GitHub MCP Server: Tool renaming][S34] | 2026-10-30 |
| S35 | [mcphub: Smart routing][S35] | 2026-10-30 |
| S36 | [mcphub: Tool policy][S36] | 2026-10-30 |
| S37 | [ContextForge: Tool annotations][S37] | 2026-10-30 |
| S38 | [Gram: Variations][S38] | 2026-10-30 |
| S39 | [Gram: Discovery modes][S39] | 2026-10-30 |
| S40 | [Cloudflare: MCP server portals][S40] | 2026-10-30 |
| S41 | [agentgateway: MCP authorization][S41] | 2026-10-30 |
| S42 | [GitHub MCP Server: Configuration][S42] | 2026-10-30 |
| S43 | [GitHub MCP Server: Toolset instructions][S43] | 2026-10-30 |
| S44 | [Executor: Tools and approvals][S44] | 2026-10-30 |
| S45 | [Docker MCP Gateway: Profiles][S45] | 2026-10-30 |
| S46 | [Progressive Disclosure WG: Decisions][S46] | 2026-10-30 |
| S47 | [1mcp: Tool names][S47] | 2026-10-30 |
| S48 | [agent-router: Prefix mode][S48] | 2026-10-30 |
| S49 | [Stainless: SDK code mode][S49] | 2026-10-30 |
| S50 | [Kuadrant: Tool discovery][S50] | 2026-10-30 |
| S51 | [Pomerium: Limit MCP tools][S51] | 2026-10-30 |
| S52 | [mcphub][S52] | 2026-10-30 |
| S53 | [MCP: Security best practices][S53] | 2026-10-30 |
| S54 | [Simon Willison: The lethal trifecta][S54] | 2026-10-30 |
| S55 | [CWE-214][S55] | 2026-10-30 |
| S56 | [OWASP: Secrets management][S56] | 2026-10-30 |
| S57 | [Docker: Pull by digest][S57] | 2026-10-30 |
| S58 | [Google SRE: Canarying releases][S58] | 2026-10-30 |
| S59 | [W3C Trace Context][S59] | 2026-10-30 |
| S60 | [Google SRE: Data integrity][S60] | 2026-10-30 |
| S61 | [Anonymized reference deployment][S61] | this repo |
| S62 | [MCP 2025-11-25: Tools][S62] | 2026-10-30 |
| S63 | [MCP 2025-11-25: Lifecycle][S63] | 2026-10-30 |
| S64 | [RFC 2119][S64] | 2026-10-30 |
| S65 | [RFC 8174][S65] | 2026-10-30 |
| S66 | [Semantic Versioning][S66] | 2026-10-30 |
