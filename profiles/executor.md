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
- **Version prefixes ([NAME-11]).** OpenAPI apps built from versioned paths get names such as `v1_twitter_tweet`. Strip the version with `renameTools` in authored apps; for catalog apps, see [Catalog apps](#catalog-apps).
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
- `kinds` sets the tool's kind and `kindConfirmed: true`. It does not change `annotations`, which keep the upstream hints. The checker treats `kindConfirmed: true` with `readOnly: true` as the gateway's review under [ANN-3]: it raises no [ANN-2] error and no [ANN-4] for that tool. If upstream sets `readOnlyHint` and `destructiveHint` both true, the checker gives info for the server owner. If upstream hints declare writes, it gives a warning to confirm the review.
- Every `never()` or custom exception is an [ANN-7] record: add a comment with the reason and reviewer.
- `readOnly` in the admin tools response is the tool's **kind** (`true` for a query, `false` for a mutation), not its approval. Approval comes from app code, so an app that uses `never()` runs mutations without approval. The checker fails [ANN-4] for a tool whose dump says `readOnly: false` and `approval: "none"`.

## Catalog apps

Catalog apps (installed with `apps.install`) belong to the Executor catalog. A catalog update overwrites local source edits, so you cannot fix their names or descriptions in place. Options, in order:

1. Leave them out of views that do not need them ([VIEW-8]).
2. Wrap the few tools you need in an authored app that follows the spec.
3. Record waivers with the catalog as the owner and a review date. The checker tags catalog findings `[catalog]`.

## Google Workspace remote MCP servers

Google serves Gmail, Drive, Docs, Sheets, Slides, and Calendar as remote MCP servers at `https://<product>mcp.googleapis.com/mcp/v1`, such as `https://gmailmcp.googleapis.com/mcp/v1`. Add one as an `mcpRouter` app. The server is untrusted third-party content ([SEC-3], [SEC-7]), and its tools are vendor-owned.

**OAuth.** Google has no dynamic client registration and matches the redirect URI exactly, so Executor needs a static client. Create a Web application OAuth client and select "Use this client for an AI-powered agent" (`is_agentic = true`); the servers reject other clients. Keep it separate from clients for non-agent features. Then:

```ts
oauth2({
  discover: "https://accounts.google.com",
  scopes: [/* least privilege, see below */],
  resource: null, // send no `resource` parameter
  authorizationParams: { access_type: "offline", prompt: "consent" }, // refresh token
})
```

- Request only the scopes the view needs ([SEC-5]). Name each scope in the app source.
- One client and one account per app, listed under [VIEW-10] when shared.

**Screening ([SEC-7]).** Screen server-side: Model Armor floor settings on the Google Cloud project, integrated service `GOOGLE_MCP_SERVER`, enforcement `INSPECT_AND_BLOCK`. Log detections only, with prompt and response payload logging off ([OBS-2]). Check the setting before you add the app to a view. If you cannot enable it, document a self-owned screening step and record the owner's written risk acceptance.

**Gmail posture.** Drafts only. Grant `gmail.readonly` and `gmail.compose`, never a send scope, so a person sends every message. Keep approval on every Gmail write ([ANN-4]). Gmail, Drive, and Calendar all carry untrusted content, so check each view with them against [SEC-1] and [SEC-2].

**Vendor waivers.** You cannot override the vendor's tool names, descriptions, or hints (see [Descriptions](#descriptions)). Waive each finding with Google as the owner, a review date, and an expiry at most 180 days away ([CONF-2]); the checker tags these `[catalog]` only for catalog apps, so say `vendor` in the reason. Re-review when the vendor's `tools/list` changes ([SEC-3]).

**Errors in unattended callers.** Treat two outcomes as stop conditions, not retries:

- *Model Armor block.* Depending on server and client, a block shows as an error or an empty response; the detail is in Cloud Logging under `model-armor_managed_service`. Log it as a security event with the tool and view, do not rephrase and resend, and do not read the same data from a mirror ([SEC-8]). Alert a person.
- *MCP elicitation.* An unattended caller cannot answer it. Fail the call, record that a human decision is pending, and never auto-accept.

**No local mirrors ([SEC-8]).** An agent must not read a calendar sync file, an `rclone gdrive:` mount, or a mailbox export in place of these servers. Google requires AI agent access to Workspace data to go through MCP (technical enforcement from 2027-02-01), and a mirror skips the screening. Keep derived data within the vendor's retention limits and redact it per session ([SEC-9]).

## Views

- New apps start private. Add them to views on purpose ([VIEW-6]).
- A group audience replaces the creator's own access to the app. If operators must reach every app, an admin group in every audience puts each new app in the operator view at once. That is a [VIEW-6] deviation: record it with a reason and an owner, limit the group to owners and admins, and keep host and service views opt-in.
- Generate audiences from one file in version control ([VIEW-7]).
- If each host has one operator and approvals gate every write, a read-only variant of each view adds little. Record that as a [VIEW-8] deviation rather than leaving it implicit.
- Accounts shared by several apps widen every view that holds one of them; list them ([VIEW-10]).
- `GET /apps/<id>/accounts/app/<requirement>` lists every account of that provider, from any app, each with a `linked` flag. To reuse one, link it with `PUT /apps/<id>/accounts/app/<requirement>/<account>`. Starting a new connection instead creates a new account, which stays after the app is deleted.
- Executor scopes by identity, so one URL with different credentials gives different views ([VIEW-1]).

## Deployment

- Pin the image by digest in a lock file ([DEP-1]).
- Back up the database and app sources before each deploy ([DEP-3]).
- Give code execution memory and time limits, and split large jobs into one `execute` per app ([DEP-9]).
- After deploy, run the checker on a dump of each changed app, and a canary call through a small read-only view ([DEP-8]).
- Executor has no route that builds an app without activating it. To check a change before it goes live ([DEP-6]), deploy the source as a private scratch app in no view, link the existing account to it (see above), dump its tools, run `check` and `diff` against the live app's dump, then delete the scratch app. The dump format, `--waivers`, and `--aliases` work unchanged on the scratch app.

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
[NAME-11]: ../SPEC.md#name-11
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
[SEC-1]: ../SPEC.md#sec-1
[SEC-2]: ../SPEC.md#sec-2
[SEC-3]: ../SPEC.md#sec-3
[SEC-5]: ../SPEC.md#sec-5
[SEC-7]: ../SPEC.md#sec-7
[SEC-8]: ../SPEC.md#sec-8
[SEC-9]: ../SPEC.md#sec-9
[OBS-2]: ../SPEC.md#obs-2
[CONF-2]: ../SPEC.md#conf-2
[CHG-1]: ../SPEC.md#chg-1
[CHG-2]: ../SPEC.md#chg-2
[VIEW-1]: ../SPEC.md#view-1
[VIEW-6]: ../SPEC.md#view-6
[VIEW-7]: ../SPEC.md#view-7
[VIEW-8]: ../SPEC.md#view-8
[VIEW-10]: ../SPEC.md#view-10
[DEP-1]: ../SPEC.md#dep-1
[DEP-3]: ../SPEC.md#dep-3
[DEP-6]: ../SPEC.md#dep-6
[DEP-8]: ../SPEC.md#dep-8
[DEP-9]: ../SPEC.md#dep-9
