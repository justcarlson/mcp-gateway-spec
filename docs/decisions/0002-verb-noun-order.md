# ADR-0002: Verb first, then noun

**Status:** Accepted, 2026-10-30 · **Rules:** [NAME-4](../../SPEC.md#name-4)

## Context

Tool names in the wild use both orders: `search_issues` and `issue_search`. Within the reference deployment, edge adapters used `<domain>_<verb>` while most upstream servers used verb first ([research 03](../../research/03-reference-deployment.md)). Mixed order in one view makes names hard to guess and to scan.

Evidence for verb first: OpenAI's MCP server guide and Anthropic's tool guidance use verb-first examples (`search_customer_orders`, `get_issue`) ([S8](https://www.anthropic.com/engineering/writing-tools-for-agents), [S16](https://developers.openai.com/plugins/build/mcp-server)); Block's playbook and the GitHub MCP server mostly do the same ([S22](https://engineering.block.xyz/blog/blocks-playbook-for-designing-mcp-servers), [S25](https://github.com/github/github-mcp-server)).

Evidence for noun first: it sorts tools by object, and the group slug already gives the domain. GitHub uses it for consolidated tools (`issue_read`, `issue_write`).

## Decision

Tool names put the verb first: `<verb>_<object>[_<qualifier>]`. The group slug supplies the domain, so the tool name does not repeat it ([NAME-7](../../SPEC.md#name-7)).

Exception: a consolidated tool that takes an action parameter may use `<object>_read` / `<object>_write`, because its verb is in the parameter ([GRP-6](../../SPEC.md#grp-6)).

## Consequences

- With prefixes, names read as `<domain>_<verb>_<object>`: `tracker_search_issues`. The domain sorts first; the verb follows.
- The checker's verb list is a heuristic. Names it does not recognize get a warning, not an error, and a reviewer decides.

## Alternatives

- **Noun first everywhere:** groups tools by object in sorted lists, but fights the published examples models were tuned on.
- **No rule:** the reference deployment shows the result: four styles in one view.
