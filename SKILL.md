---
name: mcp-gateway-spec
description: "Use when changing MCP gateway tools, apps, views, approvals, edge, or deployment; setting up a gateway for a client. Applies the MCP Gateway Specification (naming, grouping, descriptions, schemas, approvals, discovery, views, edge, change management, deployment, security) and runs its conformance checker."
---

# MCP gateway spec

Apply [SPEC.md](SPEC.md) to any change to an MCP gateway's surface or operations. The spec is product-neutral; [profiles/](profiles/) map it onto Executor, Cloudflare MCP server portals, and flat-list proxies.

## When this applies

- Adding, renaming, removing, or re-describing a tool or a group (app, server, namespace)
- Changing annotations, approvals, or approval exceptions
- Creating or changing a view (profile, audience, portal, virtual server)
- Changing edge exposure: prefixes, allowlists, adapters, metadata sync
- Deploying or upgrading a gateway
- Setting up a gateway for a new client or audience

## Workflow

1. **Find the profile.** Read the matching file in [profiles/](profiles/) for product terms. For a custom gateway, use [SPEC.md](SPEC.md) directly.
2. **Read the rules for the change.** Section map: naming 4, grouping 5, descriptions 6, schemas 7, approvals 8, discovery 9, views 10, edge 11, change management 12, deployment 13, observability 14, security 15, rule index 17. Each rule has an ID such as `NAME-5`; cite IDs in reviews and commits.
3. **Use the templates.**
   - New tool: [templates/tool-description.md](templates/tool-description.md)
   - New group: [templates/group.md](templates/group.md)
   - View as code: [templates/view.toml](templates/view.toml)
   - New client: [templates/new-client-setup-checklist.md](templates/new-client-setup-checklist.md)
4. **Run the checker** on the result (install below). Fix errors. Fix warnings or record a reason.
5. **For renames, removals, or schema changes,** run `diff` with an alias file, and list every caller before you merge (CHG-1, CHG-8).
6. **Fill in** [templates/change-review-checklist.md](templates/change-review-checklist.md) and attach the checker output (CHG-6). The checklist covers the rules the checker cannot test.

## Checker

Python 3.12+, no dependencies.

```sh
uvx --from git+https://github.com/justcarlson/mcp-gateway-spec@v0.1.0 mcp-gateway-check --help
# or: pipx install git+https://github.com/justcarlson/mcp-gateway-spec@v0.1.0
```

```sh
mcp-gateway-check check tools.json                    # tools/list result, JSON-RPC response, or tool array
mcp-gateway-check check dumps/ --namespace path       # one JSON file per group (Executor app dumps)
mcp-gateway-check check edge.json --namespace prefix  # flat list with <slug>_<tool> names
MCP_TOKEN=... mcp-gateway-check check https://gateway.example/mcp
mcp-gateway-check diff before.json after.json --aliases aliases.toml
mcp-gateway-check diff upstream.json edge.json --mode sync --strip-prefix gateway_
mcp-gateway-check check tools.json --mcp-revision 2025-11-25   # default: the target in upstream.json
mcp-gateway-check rules                               # every rule ID, level, test, and MCP revision window
```

- Rules apply to MCP revisions (`since`/`until`). The checker uses the target revision unless `--mcp-revision` says otherwise, skips rules outside the window, and lists them. Conformance profiles per revision: [conformance/](conformance/).
- `--format json` for machine output; `--waivers waivers.toml` for accepted findings (rule, target, reason, owner, expiry within 180 days).
- Exit 0: no errors. Exit 1: errors (or warnings with `--fail-on warning`). Exit 2: input error.
- The bearer token comes from `$MCP_TOKEN` (or `--token-env NAME`). Never put a token on the command line. Other headers: `--header-env Header=ENVVAR`.

## Hard rules to keep in mind

- Names: `[A-Za-z0-9_.-]`, 1-128 chars, unique; exposed names at most 64 (NAME-1, NAME-2, NAME-5).
- Slugs: `^[a-z][a-z0-9]{1,19}$` (GRP-2). Prefix: `<slug>_<tool>` (EDGE-2).
- Every tool and group has a description; tool descriptions at most 4,096 chars (DESC-1, DESC-3, DESC-9).
- Hints are untrusted. The gateway requires approval for anything not reviewed as read-only, on every call path (ANN-3, ANN-4, ANN-5).
- Never flat past 50 tools or 25,000 tokens (DISC-2).
- Views: selected by URL or credential, filter every operation, deny wins, fail closed (VIEW-1 to VIEW-4).
- Renames keep an alias for 30 days and one release; schema changes are additive (CHG-1 to CHG-3).
- Approval loosening needs a second reviewer (CHG-9).
- Secrets live in a secret manager, never in git, images, argv, or logs (DEP-2).
