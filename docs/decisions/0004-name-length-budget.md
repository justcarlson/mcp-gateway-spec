# ADR-0004: Name length budget

**Status:** Accepted, 2026-10-30 · **Rules:** [NAME-5](../../SPEC.md#name-5), [NAME-6](../../SPEC.md#name-6)

## Context

| Limit | Source |
|---|---|
| MCP tool names: 1-128 characters | [S1](https://modelcontextprotocol.io/specification/2026-07-28/server/tools), [S6](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/seps/986-specify-format-for-tool-names.md) |
| OpenAI function names: at most 64 characters | [S18](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create) |
| Claude Code adds `mcp__<server>__` to every MCP tool name | [S13](https://code.claude.com/docs/en/mcp) |
| 1mcp caps prefixed names at 64 and hashes longer ones | [S47](https://github.com/1mcp-app/agent/blob/main/src/utils/core/toolNames.ts) |

A name that some clients reject breaks the view for those clients. The reference deployment had 23 catalog tools whose prefixed names passed 64 characters ([research 03](../../research/03-reference-deployment.md)).

## Decision

| Part | Limit | Level |
|---|---|---|
| Exposed name (`<slug>_<tool>`) | 64 | MUST (NAME-5) |
| Exposed name | 48 | SHOULD (NAME-6) |
| Tool name without prefix | 32 | SHOULD (NAME-6) |
| Slug | 20 | MUST (GRP-2) |

Path-namespaced gateways have no exposed name on the wire. The checker still computes `<slug>_<tool>`, with `.` in nested names replaced by `_`, because edges and adapters create that name.

## Consequences

- 48 leaves 16 characters for a client prefix such as `mcp__gateway__` within 64.
- A 20-character slug plus `_` plus a 32-character tool name is 53, over the 48 target. Long slugs and long tool names together need a shorter one of the two.

## Alternatives

- **128 (MCP's limit):** OpenAI rejects the names.
- **64 only:** leaves no room for client prefixes.
