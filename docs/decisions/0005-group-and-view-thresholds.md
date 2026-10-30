# ADR-0005: Tools per group and per flat view

**Status:** Accepted, 2026-10-30 · **Rules:** [GRP-4](../../SPEC.md#grp-4), [DISC-1](../../SPEC.md#disc-1), [DISC-2](../../SPEC.md#disc-2)

## Context

| Evidence | Source |
|---|---|
| Anthropic recommends tool search above 10 tools or 10K tokens of definitions; selection degrades past 30-50 tools | [S11](https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-search-tool) |
| Tool search cut a large tool set from ~77K to ~8.7K tokens and raised accuracy from 79.5% to 88.1% | [S9](https://www.anthropic.com/engineering/advanced-tool-use) |
| OpenAI targets fewer than 10 functions per namespace | [S17](https://developers.openai.com/api/docs/guides/tools-tool-search) |
| VS Code caps a request at 128 tools | [S23](https://code.visualstudio.com/docs/agents/run/tools) |
| The reference deployment had one 243-tool app and three over 100 | [research 03](../../research/03-reference-deployment.md) |

## Decision

| Measure | SHOULD | MUST NOT exceed (when flat) |
|---|---|---|
| Tools per group | 10 | none |
| Tools in a flat view | 10 | 50 |
| Tokens of definitions in a flat view | 10,000 | 25,000 |

Tokens are estimated as the length of the compact JSON of each tool definition, divided by 4. The estimate is rough on purpose; it needs no tokenizer and errs high for JSON.

Above the SHOULD line, use progressive or code mode ([section 9](../../SPEC.md#9-discovery-modes)). Above the MUST NOT line, flat mode is not allowed.

## Consequences

- Most real gateways must use progressive or code mode. Small single-purpose views stay flat.
- Large upstream servers are split or filtered per audience ([GRP-4](../../SPEC.md#grp-4)), or waived with a reason when the vendor owns them.

## Alternatives

- **Hard limit per group:** blocks importing large vendor servers that are only reached through search.
- **Limit by tokens only:** tool count also affects selection accuracy, independent of size.
