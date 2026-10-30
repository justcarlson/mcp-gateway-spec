# Profiles

A profile maps [SPEC.md](../SPEC.md) onto one product: which feature carries each spec term, which settings meet the rules, and how to run the checker against it. A profile never claims that a product conforms. Conformance is a property of a deployment, shown by a checker report and a completed checklist ([CONF-1](../SPEC.md#conf-1)).

| Profile | Products | Namespace | Discovery |
|---|---|---|---|
| [executor.md](executor.md) | Executor | Paths: `tools.<slug>.<tool>` | Progressive and code |
| [cloudflare-portals.md](cloudflare-portals.md) | Cloudflare MCP server portals | Prefix: `<server_id>_<tool>` | Flat; code mode by policy |
| [flat-proxy.md](flat-proxy.md) | agentgateway, mcphub, ContextForge, Docker MCP gateway | Prefix | Mostly flat |

Custom gateways use the spec directly. To add a profile, see [CONTRIBUTING.md](../CONTRIBUTING.md#add-a-profile).
