# Changelog

All notable changes to this spec and its checker. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow [SemVer](https://semver.org/) as described in [docs/versioning.md](docs/versioning.md).

## [0.1.1] - 2026-10-30

Checker and profile fixes from a live check of a 38-app deployment and its edge. No rule changes; the conformance profiles stay as frozen in 0.1.0.

### Fixed

- The checker no longer reads Executor's `readOnly` field as the approval state. It is the tool's kind. Approval now comes only from an `approval` field (`"required"` or `"none"`); a tool without one has unknown approval. ANN-4 now fails a mutation that runs without approval, such as a tool under `never()`.
- A tool with `kindConfirmed: true` and kind `query` counts as reviewed under ANN-3. Its upstream hints no longer give ANN-2 or ANN-4 errors; a hint conflict is an info finding for the server owner.
- NAME-8 no longer flags a group whose tools are all meta-tools, such as a gateway behind an edge. It still flags a meta-tool name in an ordinary group.
- `diff --mode sync --waivers` no longer reports CONF-3 "matched nothing" for waivers on rules that `diff` does not check. The same holds for `check` and the change rules.
- Live checks send `User-Agent: mcp-gateway-check/<version>`. Requests without one got a 403 from Cloudflare's browser integrity check.

### Added

- `--user-agent VALUE`. A `--header-env User-Agent=ENV` header wins over it.
- A "not checked" list in text and JSON reports: rules that had no data, such as ANN-4 for tools with no `approval` field and DESC-11 and DESC-12 for groups with no instruction text. These rules have not passed.
- [profiles/executor.md](profiles/executor.md): the dump fields and where each comes from, what `kinds` changes, no per-tool description or annotation override in the apps SDK, one-to-one `renameTools` and the wrapper cost of CHG-1 aliases, and a Limitations section.
- [profiles/cloudflare-portals.md](profiles/cloudflare-portals.md): portals drop server instructions (DISC-10 and DISC-11 cannot pass at a portal edge) and keep `title` and `outputSchema` after sync, verified on 2026-10-30. Also the User-Agent note, NAME-8 at a gateway edge, and a NAME-4 waiver example.

### Upstream

- No change. Supported MCP revisions: **2026-07-28** (target), 2025-11-25.

## [0.1.0] - 2026-10-30

First release.

### Added

- [SPEC.md](SPEC.md): 116 rules in 13 families, each with an ID, a level, a reason, sources, and an MCP revision window. Conformance levels 1 to 3 and a waiver format.
- Six decision records in [docs/decisions/](docs/decisions/).
- Profiles for Executor, Cloudflare MCP server portals, and flat-list proxies.
- Templates: tool description, group, view, change review checklist, new-client setup checklist.
- `mcp-gateway-check`: checks files, directories, and live endpoints (stateless 2026-07-28 requests with an initialize fallback). Text and JSON output, waivers with expiry, `diff` for change review and edge sync, `--mcp-revision`.
- Frozen conformance profiles [conformance/mcp-2026-07-28.yaml](conformance/mcp-2026-07-28.yaml) and [conformance/mcp-2025-11-25.yaml](conformance/mcp-2025-11-25.yaml).
- Research notes with a "verified on" date for each source.
- Agent skill: [SKILL.md](SKILL.md).
- Weekly workflows that track upstream MCP releases and check links.

### Upstream

- Supported MCP revisions: **2026-07-28** (target), 2025-11-25. Pinned by tag and commit in [upstream.json](upstream.json).
- Rules new in 2026-07-28: DISC-8, DISC-10, VIEW-1, VIEW-5, CHG-11. DISC-11 applies to 2025-11-25 only.

[0.1.1]: https://github.com/justcarlson/mcp-gateway-spec/releases/tag/v0.1.1
[0.1.0]: https://github.com/justcarlson/mcp-gateway-spec/releases/tag/v0.1.0
