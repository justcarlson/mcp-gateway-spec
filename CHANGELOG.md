# Changelog

All notable changes to this spec and its checker. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow [SemVer](https://semver.org/) as described in [docs/versioning.md](docs/versioning.md).

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

[0.1.0]: https://github.com/justcarlson/mcp-gateway-spec/releases/tag/v0.1.0
