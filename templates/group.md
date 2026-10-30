# Group template

Use when adding a group (an app, server, target, or namespace). Rules: [section 5](../SPEC.md#5-grouping), [DESC-9 to DESC-14](../SPEC.md#desc-9).

The description says **when** to use the group. The instructions say **how**. This split follows the Progressive Disclosure Working Group decision.

## Template

```text
slug:         <lowercase letters and digits, starts with a letter, 2-20 chars>   GRP-2
title:        <Readable name>
owner:        <person or team>                                                    GRP-1
upstream:     <MCP server, OpenAPI spec, or code>
credential:   <account name; list other groups that share it>                     VIEW-10, SEC-5
risk:         <read-only | writes | destructive | sends data out>                SEC-1

description (<= 300 chars, when):
  <Domain and the questions it answers>. Use it for <tasks>. Not for <nearby tasks> (use <other group>).

instructions (<= 2,048 chars, how; critical text first):
  - <Call order: "Search first, then get by ID.">
  - <Cross-tool rules: "Preview before you request; request only after the user confirms.">
  - <Limits: "Results are capped at 50; narrow the query instead of paging past 200.">
  - <When to search for more tools.>
```

Instructions do not repeat tool descriptions and do not act as a security control. Longer workflows go in a skill (DESC-14).

## Example

```json
{
  "group": {
    "slug": "tracker",
    "title": "Issue tracker",
    "description": "Issues and comments in the team tracker. Use it to find, read, file, or close issues. Not for code review (use the code host group).",
    "instructions": "Search before you create, to avoid duplicates. Get an issue by ID before you close it, and quote its title back to the user. Results are capped at 50."
  },
  "tools": []
}
```

The checker reads this shape directly: `{"group": {...}, "tools": [...]}`.

## Review

- [ ] Slug matches `^[a-z][a-z0-9]{1,19}$` (GRP-2)
- [ ] One owner (GRP-1), one domain (GRP-5)
- [ ] 10 tools or fewer, or a filter or split plan (GRP-4)
- [ ] Reads and writes are separate tools (GRP-6)
- [ ] Description present, says when, 300 characters or fewer (DESC-9, DESC-10)
- [ ] Instructions say how, 2,048 characters or fewer (DESC-11, DESC-12)
- [ ] Added to no view yet; views added on purpose (VIEW-6)
- [ ] Cross-app risk review for each view it joins (SEC-2)
