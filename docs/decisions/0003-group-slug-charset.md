# ADR-0003: Group slugs are short lowercase identifiers

**Status:** Accepted, 2026-10-30 · **Rules:** [GRP-2](../../SPEC.md#grp-2)

## Context

The slug appears in four places, each with its own rules:

| Place | Constraint |
|---|---|
| Executor app slug | `^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$`: lowercase, digits, and `-`; no `_` ([S44](https://executor.sh/docs/concepts/tools-and-approvals)) |
| Code-mode paths (`tools.<slug>.<tool>`) | A JavaScript or Python identifier, or the program needs bracket syntax: `tools["media-requests"]` |
| Flat prefix (`<slug>_<tool>`) | No `_`, or the split is ambiguous ([ADR-0001](0001-prefix-separator.md)) |
| Hostnames, URL paths, metric labels | DNS label rules |

The reference deployment had 22 kebab-case slugs, and its edge adapters had to use bracket syntax for them ([research 03](../../research/03-reference-deployment.md)).

## Decision

Slugs match `^[a-z][a-z0-9]{1,19}$`: a lowercase letter, then 1 to 19 lowercase letters or digits. This is the intersection of the four constraints above, with a length cap from [ADR-0004](0004-name-length-budget.md).

Use compound words without separators: `dnsfilter`, `mediarequests`, `homeassist`.

## Consequences

- Every slug works unchanged as an Executor slug, a code identifier, a prefix, and a DNS label.
- Some slugs read less well (`mediarequests`). Put the readable name in the group `title`.
- Existing kebab slugs need a rename through [change management](../../SPEC.md#12-change-management), or a waiver. Catalog groups whose slug the gateway vendor owns get a waiver with the vendor as the reason.

## Alternatives

- **Allow `-`:** matches Executor's own pattern and reads better, but breaks code-mode identifiers.
- **Allow `_`:** reads well and is a valid identifier, but Executor rejects it and the `_` prefix split becomes ambiguous.
- **No length cap:** a 40-character slug leaves 23 characters for the tool name under the 64 limit.
