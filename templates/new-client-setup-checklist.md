# New-client gateway setup checklist

Use when a new client, agent, or audience needs gateway access. The goal: one view, at one URL or credential, holding only what the client needs, checked before first use.

## 1. Define the audience

- [ ] Who or what uses it: a person, an unattended agent, or both. Separate views for automation and people (SEC-6)
- [ ] The tasks it must do, as a short list
- [ ] Owner of the view

## 2. Pick the client's limits

| Client trait | Where to look | Affects |
|---|---|---|
| Name pattern and length (for example, 64 for OpenAI) | Client docs | NAME-5, NAME-6 |
| Client prefix (for example, `mcp__<server>__`) | Client docs | NAME-6 |
| Tool search or deferred loading | Client docs | Discovery mode |
| Max tools per request (for example, 128 in VS Code) | Client docs | DISC-2 |
| Description and instruction truncation (for example, 4,096 in Claude Code) | Client docs | DESC-3, DESC-12 |
| Per-tool approval prompts | Client docs | ANN-5 |

## 3. Build the view

- [ ] Start from the smallest set of groups that covers the tasks (VIEW-8)
- [ ] Copy [view.toml](view.toml) and fill it in; commit it (VIEW-7)
- [ ] Selector: a dedicated URL path or credential, never a session toggle (VIEW-1)
- [ ] Discovery mode: flat only at 10 tools and 10,000 tokens or fewer; progressive or code above; never flat past 50 tools or 25,000 tokens (DISC-1, DISC-2)
- [ ] Up to 5 pinned tools for the most common calls (DISC-5)
- [ ] Read-only variant if the view can write (VIEW-8)
- [ ] Server instructions name the groups and say when to search (DISC-7)
- [ ] Meta-tool-only view: one short capability line in the search tool description and the server instructions (DISC-12)
- [ ] One entry tool or routing skill for tasks that start from a URL (DISC-14)

## 4. Credentials

- [ ] A new credential for this client, stored in a secret manager (DEP-2)
- [ ] Delivered to the client through its secret store or an environment variable, never in chat, git, or a command line
- [ ] Upstream accounts scoped to this view's groups; shared ones listed (VIEW-10, SEC-5)
- [ ] If an edge sits in front: the edge has its own credential, and does not pass the client's token through (EDGE-4, SEC-4)

## 5. Security review

- [ ] Lethal trifecta: private data ☐ untrusted content ☐ outbound ☐. All three: approval on every outbound tool, or split the view (SEC-1)
- [ ] Cross-app review of the group combination (SEC-2)
- [ ] Approval policy confirmed for every write tool in the view (ANN-4, ANN-5)
- [ ] Policy fails closed: test with a wrong credential and expect no tools (VIEW-4)

## 6. Check before first use

```sh
export MCP_TOKEN=...   # from the secret manager; never pass it as an argument
mcp-gateway-check check https://gateway.example/views/<name> --format json > report.json
```

- [ ] No errors, or waivers with reason, owner, and expiry (CONF-2)
- [ ] `tools/list` with this credential shows only the expected tools
- [ ] A hidden tool fails when called by name (VIEW-2)
- [ ] One read call and one approval-gated call work end to end from the client
- [ ] Calls appear in the gateway log with identity and view (OBS-1)

## 7. Hand over

- [ ] Client configured with the URL and the secret reference
- [ ] Probe added for the new endpoint (OBS-4)
- [ ] Conformance claim recorded: spec version, level, view, report, and this checklist (CONF-1)
