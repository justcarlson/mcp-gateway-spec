# Tool description template

Use for each tool. Rules: [section 4](../SPEC.md#4-naming), [section 6](../SPEC.md#6-descriptions-and-group-instructions), [section 7](../SPEC.md#7-schemas-responses-and-errors), [section 8](../SPEC.md#8-annotations-and-approvals).

## Template

```text
name:   <verb>_<object>[_<qualifier>]          snake_case, verb first, no group slug, <= 32 chars
title:  <Verb> <object>                        short human label for approval prompts

description:
  <One sentence: verb, object, scope, in words a user would type. <= 160 chars.>
  Use this when <situation>. Do not use it for <other situation>; use `<other_tool>`.
  Inputs: <format, units, defaults, where IDs come from>.
  Returns: <shape, page size, what truncation looks like>.
  Example: <one realistic call, for complex inputs only>.

inputSchema:   object; every property described; enums for closed sets; no credentials
outputSchema:  when the result is structured
annotations:   readOnlyHint, destructiveHint, idempotentHint, openWorldHint (all four)
approval:      required unless reviewed as read-only
```

Keep the whole description between 80 and 1,024 characters.

## Example

```json
{
  "name": "search_issues",
  "title": "Search issues",
  "description": "Search issues in the tracker by text, state, label, or assignee. Use this when the user describes an issue but has no ID; use `get_issue` when you have one. Inputs: `query` is free text; `state` defaults to open. Returns up to 50 issues with id, title, state, and URL, newest first; use `cursor` for the next page.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "query": {"type": "string", "description": "Words to match in the title or body."},
      "state": {"type": "string", "enum": ["open", "closed", "all"], "description": "Issue state. Default: open."},
      "cursor": {"type": "string", "description": "Cursor from the previous page."}
    },
    "required": ["query"],
    "additionalProperties": false
  },
  "annotations": {"readOnlyHint": true, "destructiveHint": false, "idempotentHint": true, "openWorldHint": false}
}
```

## Review

- [ ] Name: snake_case, verb first, no slug, no meta-tool name, no API version prefix, 32 characters or fewer (NAME-3, NAME-4, NAME-6, NAME-7, NAME-8, NAME-11)
- [ ] Title set (NAME-10)
- [ ] First sentence says what, in 160 characters or fewer (DESC-4)
- [ ] When to use, and the alternative when tools overlap (DESC-5)
- [ ] Names the usual follow-up tool, if there is one (DISC-13)
- [ ] Inputs and returns described; example for complex inputs (DESC-6)
- [ ] No hidden directives, secrets, or private hosts (DESC-7)
- [ ] No safety claims the gateway does not enforce (DESC-8)
- [ ] Schema: object, every property described, no `$ref`, no credentials (SCHEMA-1, SCHEMA-3, SCHEMA-5, SCHEMA-7)
- [ ] All four hints set and true to behavior (ANN-1, ANN-2, ANN-8)
- [ ] Approval required unless reviewed as read-only (ANN-4)
- [ ] Errors return `isError: true` with a fix hint (SCHEMA-10)
