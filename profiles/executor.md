# Profile: Executor

How [SPEC.md](../SPEC.md) maps onto [Executor](https://executor.sh/docs/concepts/tools-and-approvals) ([S44]), a host that runs apps and serves them to agents through a few meta-tools. Based on Executor `2.0.0-beta.31` with the apps SDK at `0.0.1-beta.116`, verified on 2026-10-30 on a 38-app deployment (the [reference deployment](../research/03-reference-deployment.md)). Executor changes fast; check the version you run.

This profile maps rules to features. It does not claim that Executor conforms; run the checker on your own deployment.

## Mapping

| Spec term | Executor |
|---|---|
| Group | App |
| Slug | App slug; tools live at `tools.<slug>.<tool>` |
| Meta-tools | `skills`, `search`, `describe`, `call`, `execute`, `resume` |
| Discovery mode | Progressive (`search`, `describe`, `call`) and code (`execute`). No flat listing of app tools |
| View | App audience (`{kind: "groups", groups: [...]}`) per identity group |
| Group description | Second argument to `router()`: the app's title and description |
| Group instructions | The app's skill (each app's instructions become a skill read with `skills`) |
| Approval | Declared in app code per tool: `always()`, `never()`, or a custom function |
| Upstream | `mcpRouter` (an MCP server), `liveOpenapiRouter` (OpenAPI), or hand-written `query` / `mutation` tools |
| Edge | None built in. Put a portal or proxy in front; see [cloudflare-portals.md](cloudflare-portals.md) |

## Naming

- **Slugs ([GRP-2]).** Executor accepts `^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$`. The spec is narrower: `^[a-z][a-z0-9]{1,19}$`, no `-`. A kebab slug forces bracket syntax in code mode (`tools["media-requests"]`) and breaks the single-`_` edge prefix ([ADR-0003](../docs/decisions/0003-group-slug-charset.md)). Pick compound slugs for new apps; rename existing ones through [change management](../SPEC.md#12-change-management).
- **Tool names ([NAME-3]).** A tool's name is its router key. For `mcpRouter` and OpenAPI apps it comes from upstream. Rename with `renameTools(router, name => newName)`; returning `undefined` drops the tool, which also makes `renameTools` the filter for [GRP-4].
- **Renames are one to one.** `renameTools` maps each name to one exposed name, and when two names map to the same one, the first wins. It cannot serve the old and the new name together, so a [CHG-1] alias or a [CHG-2] deprecation window needs a hand-written wrapper tool under the old name that calls the new one.
- **Nested names.** Some catalog apps use dotted names (`messages.list`). The checker turns `.` into `_` when it computes the exposed name for [NAME-5].
- **Meta-tool clashes ([NAME-8]).** Rename upstream tools called `search`, `describe`, `call`, `execute`, `resume`, or `skills`. If callers already use the old name, each rename needs a [CHG-1] alias, which costs one wrapper tool per alias. Plan these renames before an app goes into a view.

## Descriptions

- Write the app description as *when* to use the app ([DESC-9], [DESC-10]); keep `package.json`'s `executor.title` and description in step with it.
- Put *how* text in the app's skill, not in the description ([DESC-11], [DESC-14]).
- For `mcpRouter` apps, descriptions and annotations pass through. The apps SDK has no per-tool override (no `withDescription` or `withAnnotations`); only re-wrapping the tools with `dynamicRouter` could change them. Fix them upstream if you own the server; otherwise waive the finding with the vendor as the owner.

## Approvals ([section 8](../SPEC.md#8-annotations-and-approvals))

Approvals live in app code, which is the right place: the gateway, not the client, enforces them on `call` and inside `execute` ([ANN-5]).

```ts
// mcpRouter: approve anything the upstream does not mark read-only (ANN-4)
withApprovals(router, tool => toolAnnotations(tool)?.readOnlyHint ? undefined : always())

// OpenAPI: approve every mutation
tool => tool.kind === "mutation" ? always() : undefined
```

- Upstream hints are untrusted ([ANN-3]). Use `kinds` (second argument to `mcpRouter`) to mark the tools you reviewed as `"query"`, rather than relying on `readOnlyHint` alone.
- `kinds` sets the tool's kind and `kindConfirmed: true`. It does not change `annotations`, which keep the upstream hints. The checker treats `kindConfirmed: true` with `readOnly: true` as the gateway's review under [ANN-3]: it raises no [ANN-2] error and no [ANN-4] for that tool, and notes an upstream hint conflict (for example `readOnlyHint` and `destructiveHint` both true) as info for the server owner.
- Every `never()` or custom exception is an [ANN-7] record: add a comment with the reason and reviewer.
- `readOnly` in the admin tools response is the tool's **kind** (`true` for a query, `false` for a mutation), not its approval. Approval comes from app code, so an app that uses `never()` runs mutations without approval. The checker fails [ANN-4] for a tool whose dump says `readOnly: false` and `approval: "none"`.

## Catalog apps

Catalog apps (installed with `apps.install`) belong to the Executor catalog. A catalog update overwrites local source edits, so you cannot fix their names or descriptions in place. Options, in order:

1. Leave them out of views that do not need them ([VIEW-8]).
2. Wrap the few tools you need in an authored app that follows the spec.
3. Record waivers with the catalog as the owner and a review date. The checker tags catalog findings `[catalog]`.

## Views

- New apps start private. Add them to views on purpose ([VIEW-6]).
- Generate audiences from one file in version control ([VIEW-7]).
- Accounts shared by several apps widen every view that holds one of them; list them ([VIEW-10]).
- Executor scopes by identity, so one URL with different credentials gives different views ([VIEW-1]).

## Deployment

- Pin the image by digest in a lock file ([DEP-1]).
- Back up the database and app sources before each deploy ([DEP-3]).
- Give code execution memory and time limits, and split large jobs into one `execute` per app ([DEP-9]).
- After deploy, run the checker on a dump of each changed app, and a canary call through a small read-only view ([DEP-8]).

## Checking an Executor deployment

Export each app as JSON: `{slug, name, source, routers: [{path, title, description}], tools: [...]}`, one file per app, where `source` is `authored` or `catalog`. Each tool carries the admin tools fields plus one field you derive:

| Field | From | Meaning |
|---|---|---|
| `name`, `title`, `description`, `annotations`, `inputSchema`, `outputSchema` | Admin tools response | As served |
| `readOnly` | Admin tools response | Kind: `true` query, `false` mutation |
| `kindConfirmed` | Admin tools response | `true` when `kinds` set the kind |
| `approval` | **Your dump script**, from app source | `"required"` or `"none"`: the policy the app's `withApprovals` gives the tool |

The dump script must emit `approval`, because the admin response does not have it: read each app's approval function (`always()`, `never()`, or a custom function) and apply it to the tool. If a tool has no `approval` field, the checker reports its approval as unknown and lists [ANN-4] under "not checked" instead of guessing. Then:

```sh
mcp-gateway-check check dumps/ --namespace path
```

The checker treats a directory of app files as a path-namespaced, progressive view. It skips files that do not contain tools, such as an `index.json`.

### Limitations

- **Instructions.** The admin tools response lists an app's skill names, not the instruction text, so a dump has no `instructions`. The checker lists [DESC-11] and [DESC-12] under "not checked" for such groups; they have not passed. Check skill length by hand, or add the skill text to the dump as `instructions`.
- **Approval.** Only as good as the dump script's reading of app source. Review custom approval functions by hand.

For the live endpoint, the meta-tools are the only tools listed, so a live check tests the meta-tool surface, not the apps:

```sh
MCP_TOKEN=... mcp-gateway-check check https://gateway.example/mcp
```

[S44]: https://executor.sh/docs/concepts/tools-and-approvals "Executor: Tools and approvals"
[GRP-2]: ../SPEC.md#grp-2
[GRP-4]: ../SPEC.md#grp-4
[NAME-3]: ../SPEC.md#name-3
[NAME-5]: ../SPEC.md#name-5
[NAME-8]: ../SPEC.md#name-8
[DESC-9]: ../SPEC.md#desc-9
[DESC-10]: ../SPEC.md#desc-10
[DESC-11]: ../SPEC.md#desc-11
[DESC-12]: ../SPEC.md#desc-12
[DESC-14]: ../SPEC.md#desc-14
[ANN-2]: ../SPEC.md#ann-2
[ANN-3]: ../SPEC.md#ann-3
[ANN-4]: ../SPEC.md#ann-4
[ANN-5]: ../SPEC.md#ann-5
[ANN-7]: ../SPEC.md#ann-7
[CHG-1]: ../SPEC.md#chg-1
[CHG-2]: ../SPEC.md#chg-2
[VIEW-1]: ../SPEC.md#view-1
[VIEW-6]: ../SPEC.md#view-6
[VIEW-7]: ../SPEC.md#view-7
[VIEW-8]: ../SPEC.md#view-8
[VIEW-10]: ../SPEC.md#view-10
[DEP-1]: ../SPEC.md#dep-1
[DEP-3]: ../SPEC.md#dep-3
[DEP-8]: ../SPEC.md#dep-8
[DEP-9]: ../SPEC.md#dep-9
