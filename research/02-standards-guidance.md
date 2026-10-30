# MCP spec, SEPs and first-party tool guidance (2026-10-30)

Source: research agent pass. Bracketed numbers point to the source list at the end.
Items marked "inference" or "unverified" were not confirmed.

## Spec and SEP status

- Current revision 2026-07-28; 2025-11-25 is Final [2].
- Tool fields: name, title, description, icons, inputSchema, outputSchema,
  annotations, `_meta` [1].
- Server `instructions` now come from `server/discover` [2].
- tools/list: must not vary per connection, may vary by authorization; SHOULD return
  a fixed order; results carry `ttlMs` and `cacheScope`; cursor pagination [2].
  Claude Code honours `list_changed` [13].
- SEP-986 tool name format: Final [6]. Spec text: 1-128 chars, `[A-Za-z0-9_.-]`, no `/`
  (the SEP abstract says 1-64 and allows `/`; follow the spec) [1][6].
- Groups/namespaces: none accepted. SEP-1300 rejected [28]; SEP-993 superseded;
  SEP-1292 closed; SEP-2084 rejected ("the ecosystem around searching tools is quickly
  evolving") [29]. Progressive Disclosure WG drafting "Grouping Convention v0.1" as a
  pattern, not spec text [7].
- Search: SEP-1821 and SEP-1881 closed dormant June 2026 [30]. Skills extension
  SEP-2640 Final [31].
- Annotations: SEP-1913 (trust/sensitivity) open draft [32]. agencyHint, secretHint,
  trustedHint rejected or closed. Do not depend on new hints.
- Open issue #3430: require server-level routing text when tools load lazily [33].

## Checklist

### Naming
1. snake_case, `[a-z0-9_]` only. MCP allows `.` and `-` [1], but Claude API and OpenAI
   function-name patterns reject dots [12][18]; Claude Code rewrites other chars to `_` [13].
2. Stable group prefix per tool in flat lists (e.g. `linear_search_issues`). Spec:
   aggregators SHOULD prefix with a server ID, not `serverInfo.name` [1]. A shared
   prefix lets one search find the whole group [11][8].
3. Verb first by default (`search_issues`, `list_projects`) [16][26]. Evidence split:
   Anthropic says choose prefix/suffix order by eval [8]; GitHub uses noun first
   (`issue_read`) [25]. Pick one order everywhere.
4. <= 64 chars including prefix (OpenAI limit [18]; MCP 128 [1]). Inference: aim <= 48
   because clients add their own prefix (`mcp__<server>__`) [13].
5. Specific, non-lookalike names (`search_customer_orders`, not `query_db_orders`) [9].
6. Never rename without an alias for the old name [34]; additive schema changes only [16].
7. `title` = human label ("Get issue details") [1][16].

### Grouping
1. Group = one app: one prefix, one `instructions` block, one auth boundary. No protocol
   primitive exists [7].
2. < 10 tools per group (OpenAI namespace target [17]).
3. Merge tools always called in a chain into one workflow tool [8]; one tool per user
   goal [16].
4. `action`/`method` enum is fine within one resource [12], but not "many unrelated
   modes" [16] and not mixed risk levels ("Build tools with one risk level only" [22]).
   Split reads from writes (`issue_read` / `issue_write`) [25].
5. Split a group past 10 tools, on mixed risk, or on different scopes. Offer a read-only
   subset [25].
6. Group instructions: scope, when to search, call order, cross-tool rules, limits [4].
   No repeated tool descriptions, no marketing, never security-by-instructions [4].
   Critical text in first 512 chars [16][19]; Claude Code truncates at 4,096 [13].
   Longer workflow guidance -> a Skill [31].

### Description template
1. First sentence: verb, object, scope, in the words a user would type. Search matches
   names and descriptions [11]; truncation cuts the end [13].
2. "Use this when ..." [15].
3. "Do not use for ... (use `<other_tool>`)" [15][26].
4. Inputs: format, units, where IDs come from, defaults [12].
5. Returns: shape, page size, truncation behaviour [9].
6. Optional 1-3 example calls for complex inputs; examples raised accuracy 72% -> 90% [9].
   MCP has no `input_examples`, so put them in the description (Sentry does) [26].
7. Length: >= 3-4 sentences [12]; inference 300-1,200 chars. Hard limits: 4,096 chars
   for tools loaded at startup, 16,384 via search (Claude Code) [13].
8. Write for a new hire: explicit, no internal jargon [8].

### Schema
1. inputSchema always an object; no-arg tools use
   `{"type":"object","additionalProperties":false}` [1].
2. Clear parameter names (`user_id`, not `user`) [8]; describe every parameter; enums
   for closed sets [15].
3. Only the true minimum required; sensible defaults for pagination and filters [8].
   Inference: flat, inline, no `$ref` (2026-07-28 allows JSON Schema 2020-12 and `$ref`
   [2], client support varies, unverified).
4. outputSchema for structured results; server must conform and should also send the
   same data as text [1]. Stable IDs for follow-ups [16]; readable names over UUIDs in
   prose [8]. `_meta` is hidden from the model [14].
5. Responses < 10k tokens (Claude Code warns 10k, caps 25k, spills > 50k chars to file
   [13]; Codex per-tool `output_token_limit` [19]).
6. Paginate (cursor, or page+limit max 100 [25]), filter, truncate; on truncation say how
   to narrow [8][22]. Offer `response_format: concise|detailed` (72 vs 206 tokens) [8].
7. Errors: `isError: true` with a fix hint so the model can retry [1][8]; rate limits give
   `retry_after_seconds` [27].
8. Stateful handles: state lifetime in the creating tool's description; actionable expiry
   errors [1].

### Annotations and approvals
1. Set all four hints explicitly. OpenAI requires readOnlyHint, destructiveHint,
   openWorldHint [14]. Missing hints default to worst case [3][5].
2. `readOnlyHint: true` only with no side effects; `destructiveHint` only meaningful when
   not read-only [3]; `openWorldHint: false` for a bounded private workspace [15];
   `idempotentHint: true` when a repeat is safe.
3. Client behaviour: Claude Code runs read-only tools in parallel and may retry
   read-only/idempotent once [13]; Codex `writes` mode asks on every non-read-only tool
   [19]; ChatGPT uses hints only to frame the call [14].
4. Hints are untrusted and enforce nothing [1][5]; the gateway must enforce approval and
   authorization [14]. Clients SHOULD confirm sensitive operations [1].
5. Judge risk across the app set: private data + untrusted content + outbound write is
   the "lethal trifecta" [5].

### Discovery
1. Flat list: < 10 tools and < 10k tokens of definitions [11].
2. Defer + search: >= 10 tools or > 10k tokens [9][11]. Selection accuracy degrades past
   30-50 tools [11]. Claude Code defers MCP tools by default; `ENABLE_TOOL_SEARCH=auto`
   defers past 10% of context [13]. VS Code caps a request at 128 tools [23]. Azure MCP
   defaults to namespace mode because `all` exposes 200+ tools [24].
3. Search/describe/call + code execution for ~40 apps: tool search ~77K -> ~8.7K tokens,
   Opus 4.5 accuracy 79.5% -> 88.1% [9]; code execution 150K -> 2K tokens [10];
   Cloudflare ~2,500 endpoints via 2 tools in ~1,000 tokens [20]; Docker says its code
   mode is early [21].
4. Search results at three detail levels: name; name + description; full schema [10].
5. Keep the 3-5 most-used tools always loaded [9]; Claude Code `_meta["anthropic/alwaysLoad"]` [13].

## Exemplary servers

- GitHub `issue_read` [25]: "Get information about a specific issue in a GitHub
  repository."; title "Get issue details"; readOnlyHint true; outputSchema; required
  `method` enum `get|get_comments|get_sub_issues|get_parent|get_labels`; `perPage` <= 100.
  Toolsets with a 5-toolset default, `--read-only`, aliases for renamed tools [34].
- Sentry `get_issue_details` [26]: one-line summary, then "USE THIS TOOL WHEN USERS:",
  "DO NOT USE for: ... (use search_issues)", "TRIGGER PATTERNS", `<examples>`, `<hints>`.
  Tagged by skill (`inspect`, `triage`, `seer`) with required scopes. readOnly true,
  destructive false, openWorld true.
- Notion [27]: 70 kebab-case tools prefixed `notion-` (e.g. `notion-search`: "Searches
  Notion pages and databases, or looks up a workspace user by name or email.").
  Workspace connections get a 24-tool subset; delete tools set destructiveHint.

## Conflicts and unverified

- OpenAI metadata guide shows `calendar.create_event` [15] but OpenAI's function-name
  pattern rejects dots [18].
- Whether OpenAI annotations need written justification: unverified.
- Cloudflare blog says 1.17M tokens without code mode; repo says ~244K [20].
- Codex parallel read-only execution: third-party claim only, unverified.
- Gemini 64-char name limit: not confirmed from a primary source.
- Executor (inference): inside `execute`, tools are JS paths `tools.<slug>.<tool>`;
  snake_case works as plain properties, kebab-case needs bracket access.

## Sources
Each link was opened and checked against the claim it supports on the date shown. The weekly link check reopens them.

[1] https://modelcontextprotocol.io/specification/2026-07-28/server/tools (verified on 2026-10-30)
[2] https://modelcontextprotocol.io/specification/2026-07-28/changelog (verified on 2026-10-30)
[3] https://modelcontextprotocol.io/specification/2026-07-28/schema (verified on 2026-10-30)
[4] https://blog.modelcontextprotocol.io/posts/2025-11-03-using-server-instructions/ (verified on 2026-10-30)
[5] https://blog.modelcontextprotocol.io/posts/2026-03-16-tool-annotations/ (verified on 2026-10-30)
[6] https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/seps/986-specify-format-for-tool-names.md (verified on 2026-10-30)
[7] https://modelcontextprotocol.io/community/working-groups/progressive-disclosure (verified on 2026-10-30)
[8] https://www.anthropic.com/engineering/writing-tools-for-agents (verified on 2026-10-30)
[9] https://www.anthropic.com/engineering/advanced-tool-use (verified on 2026-10-30)
[10] https://www.anthropic.com/engineering/code-execution-with-mcp (verified on 2026-10-30)
[11] https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-search-tool (verified on 2026-10-30)
[12] https://platform.claude.com/docs/en/agents-and-tools/tool-use/define-tools (verified on 2026-10-30)
[13] https://code.claude.com/docs/en/mcp (verified on 2026-10-30)
[14] https://developers.openai.com/plugins/reference (verified on 2026-10-30)
[15] https://developers.openai.com/plugins/guides/optimize-metadata (verified on 2026-10-30)
[16] https://developers.openai.com/plugins/build/mcp-server (verified on 2026-10-30)
[17] https://developers.openai.com/api/docs/guides/tools-tool-search (verified on 2026-10-30)
[18] https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create (verified on 2026-10-30)
[19] https://learn.chatgpt.com/docs/extend/mcp?surface=cli (verified on 2026-10-30)
[20] https://blog.cloudflare.com/code-mode-mcp/ (verified on 2026-10-30)
[21] https://docs.docker.com/ai/mcp-catalog-and-toolkit/dynamic-mcp/ (verified on 2026-10-30)
[22] https://engineering.block.xyz/blog/blocks-playbook-for-designing-mcp-servers (verified on 2026-10-30)
[23] https://code.visualstudio.com/docs/agents/run/tools (verified on 2026-10-30)
[24] https://learn.microsoft.com/en-us/azure/developer/azure-mcp-server/concepts (verified on 2026-10-30)
[25] https://github.com/github/github-mcp-server (verified on 2026-10-30)
[26] https://github.com/getsentry/sentry-mcp/blob/main/packages/mcp-core/src/tools/catalog/get-issue-details.ts (verified on 2026-10-30)
[27] https://developers.notion.com/docs/mcp-supported-tools (verified on 2026-10-30)
[28] https://github.com/modelcontextprotocol/modelcontextprotocol/issues/1300 (verified on 2026-10-30)
[29] https://github.com/modelcontextprotocol/modelcontextprotocol/issues/2084 (verified on 2026-10-30)
[30] https://github.com/modelcontextprotocol/modelcontextprotocol/issues/1821 (verified on 2026-10-30)
[31] https://github.com/modelcontextprotocol/modelcontextprotocol/issues/2640 (verified on 2026-10-30)
[32] https://github.com/modelcontextprotocol/modelcontextprotocol/issues/1913 (verified on 2026-10-30)
[33] https://github.com/modelcontextprotocol/modelcontextprotocol/issues/3430 (verified on 2026-10-30)
[34] https://github.com/github/github-mcp-server/blob/main/docs/tool-renaming.md (verified on 2026-10-30)
