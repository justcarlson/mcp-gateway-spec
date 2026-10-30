# ADR-0001: Gateway prefixes use a single underscore

**Status:** Accepted, 2026-10-30 · **Rules:** [EDGE-2](../../SPEC.md#edge-2), [NAME-1](../../SPEC.md#name-1)

## Context

A flat client sees one list of tools. When a gateway or edge merges groups into that list, it adds the group slug to each name. Products differ on the separator ([research 01](../../research/01-gateway-survey.md#common-2026-shape)):

| Separator | Used by |
|---|---|
| `__` | Docker MCP gateway (optional), metamcp, agent-router |
| `_` | Cloudflare MCP server portals, agentgateway |
| `-` | ContextForge, mcphub, Bifrost |
| `.` | Executor (paths, not flat names) |

MCP allows `[A-Za-z0-9_.-]` ([S1](https://modelcontextprotocol.io/specification/2026-07-28/server/tools)). The Claude API and OpenAI function names reject `.`, and Claude Code rewrites other characters to `_` ([S12](https://platform.claude.com/docs/en/agents-and-tools/tool-use/define-tools), [S13](https://code.claude.com/docs/en/mcp), [S18](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create)).

## Decision

The prefix is `<slug>_<tool>`, with one `_`. Slugs contain no `_` ([ADR-0003](0003-group-slug-charset.md)), so the first `_` always ends the slug. The checker splits on it with `--namespace prefix`.

## Consequences

- Matches the edge most likely to sit in front of a gateway (Cloudflare portals) and agentgateway, so their output passes without a rename map.
- Spends one character, not two, of the 64-character budget ([ADR-0004](0004-name-length-budget.md)).
- Leaves `.` and `-` out of exposed names, so every client accepts them.
- A gateway that uses `__` or `-` still conforms if it can be configured to `_`; if not, record a waiver for EDGE-2.

## Alternatives

- **`__`:** unambiguous even with `_` in slugs, and common. Costs a character, and Claude Code already uses `__` for its own `mcp__<server>__` prefix, so names get hard to read: `mcp__portal__tracker__search_issues`.
- **`-`:** readable, but mixes kebab and snake case in one name.
- **`.`:** natural for paths, rejected by two major function-calling APIs.
