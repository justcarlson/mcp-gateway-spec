# Architecture decision records

Each record explains one choice in [SPEC.md](../../SPEC.md) that had a real alternative. Format: context, decision, consequences, alternatives.

| ADR | Decision | Rules |
|---|---|---|
| [0001](0001-prefix-separator.md) | Gateway prefixes use a single `_` | EDGE-2 |
| [0002](0002-verb-noun-order.md) | Verb first, then noun | NAME-4 |
| [0003](0003-group-slug-charset.md) | Slugs match `^[a-z][a-z0-9]{1,19}$` | GRP-2 |
| [0004](0004-name-length-budget.md) | 64 hard, 48 target, 32 per tool | NAME-5, NAME-6 |
| [0005](0005-group-and-view-thresholds.md) | 10 tools per group; flat views 10 tools / 10k tokens, never past 50 / 25k | GRP-4, DISC-1, DISC-2 |
| [0006](0006-description-length-budget.md) | Description and instruction length budgets | DESC-2, DESC-3, DESC-4, DESC-10, DESC-11, DESC-12 |

To change a decision, add a new record that supersedes the old one, and change the status line of the old one. Do not edit the decision in place.
