# ADR-0006: Description length budget

**Status:** Accepted, 2026-10-30 · **Rules:** [DESC-2](../../SPEC.md#desc-2), [DESC-3](../../SPEC.md#desc-3), [DESC-4](../../SPEC.md#desc-4), [DESC-10](../../SPEC.md#desc-10), [DESC-11](../../SPEC.md#desc-11), [DESC-12](../../SPEC.md#desc-12)

## Context

| Evidence | Source |
|---|---|
| Anthropic asks for at least 3-4 sentences per tool description | [S12](https://platform.claude.com/docs/en/agents-and-tools/tool-use/define-tools) |
| Claude Code truncates tool descriptions and server instructions at 4,096 characters | [S13](https://code.claude.com/docs/en/mcp) |
| Examples raised accuracy from 72% to 90% in Anthropic's tests | [S9](https://www.anthropic.com/engineering/advanced-tool-use) |
| ContextForge allows overrides up to 8,192 characters | [S37](https://github.com/IBM/mcp-context-forge/blob/main/docs/docs/using/tool-annotations.md) |
| The Progressive Disclosure WG splits group text into description (when) and instructions (how) | [S46](https://github.com/modelcontextprotocol/progressive-disclosure-wg/blob/main/docs/decisions.md) |
| The reference deployment had one-word descriptions and one of 11,620 characters | [research 03](../../research/03-reference-deployment.md) |

## Decision

| Text | Target | Hard limit |
|---|---|---|
| Tool description | 80-1,024 characters (SHOULD) | 4,096 (MUST) |
| First sentence of a tool description | 160 characters (SHOULD) | none |
| Group description | 300 characters (SHOULD) | none; must be present (MUST) |
| Group instructions | 2,048 characters, critical text in the first 512 (SHOULD) | 4,096 (MUST) |

80 characters is about one full sentence, the least that says what a tool does and when to use it. 1,024 fits the template's six parts with one example.

## Consequences

- One-line descriptions get warnings, which is the point: they are the most common reason a model picks the wrong tool.
- Guidance longer than 2,048 characters moves into a skill ([DESC-14](../../SPEC.md#desc-14)).

## Alternatives

- **Token limits instead of characters:** more accurate, but depends on the tokenizer. Characters are easy to check in any tool.
- **8,192 like ContextForge:** Claude Code would truncate the second half.
