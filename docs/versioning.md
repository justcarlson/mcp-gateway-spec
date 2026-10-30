# Versioning and release policy

This repo has two version numbers. They never mix.

| What | Format | Where it lives | Example |
|---|---|---|---|
| Spec version | [SemVer 2.0.0](https://semver.org/spec/v2.0.0.html) | `SPEC.md` header, `pyproject.toml`, git tags | `0.1.0` |
| MCP revision | Upstream date tag | [`upstream.json`](../upstream.json) | `2026-07-28` |

The spec version says what *this* repo promises. The MCP revision is data: which upstream protocol revisions the rules cover. The revision never appears in the version number.

## upstream.json

[`upstream.json`](../upstream.json) is the single source of truth for MCP revisions. The checker, CI, and the README all read it.

- `mcp.target`: the revision new gateways should build for. The checker uses it when `--mcp-revision` is not given.
- `mcp.supported`: every revision this spec version has rules for. The target is always in the list.
- `mcp.revisions.<rev>`: the upstream tag, commit SHA, release URL, changelog URL, and the date a person last checked it (`verified_on`).

[`upstream.schema.json`](../upstream.schema.json) describes the file. CI validates it on every push.

## Rule windows

Each rule has `since` and an optional `until` MCP revision. Both are inclusive. A rule with no `until` applies to every later revision, including `draft`. SPEC.md shows the window on each rule line and in the [rule index](../SPEC.md#17-rule-index).

```sh
mcp-gateway-check check tools.json                         # target revision
mcp-gateway-check check tools.json --mcp-revision 2025-11-25
mcp-gateway-check check tools.json --mcp-revision draft    # upstream main; uses the target's wire format
mcp-gateway-check rules --mcp-revision 2025-11-25          # rules that apply to one revision
```

The checker skips rules outside the window and lists them in the report. It rejects a revision that is not in `supported`.

## Conformance profiles

`conformance/mcp-<rev>.yaml` lists the rule IDs and levels for one revision, as frozen by one spec release. A claim such as "conforms to `mcp-2026-07-28` at Level 1" points at that file.

- Write a profile with `python3 scripts/conformance.py --write <rev>`. Before the release, CI checks that it matches the registry.
- After the tag in `frozen_in:` exists, the file never changes. `scripts/check_frozen.py` fails CI if it does.
- Later spec versions that add rules for the same revision do not edit the old profile. If a frozen profile needs a correction, release a new revision-specific profile and note it in CHANGELOG.

## Tracking upstream

[`.github/workflows/track-upstream.yml`](../.github/workflows/track-upstream.yml) runs every Monday and on demand. It compares upstream releases, including RC tags, with `upstream.json`. For each new release candidate or final revision it opens or updates one issue titled `Track MCP <rev>`, with the release link, the `docs/specification/<rev>/changelog.mdx` link, and a summary of its major changes. It never edits the repo or merges anything. It uses the workflow's `GITHUB_TOKEN` with `contents: read` and `issues: write` only.

Run it locally without changing anything:

```sh
python3 scripts/track_upstream.py --dry-run
```

**Alternative: Renovate.** Dependabot cannot watch arbitrary GitHub releases. [Renovate](https://docs.renovatebot.com/) can, with a [`customManagers`](https://docs.renovatebot.com/modules/manager/regex/) regex entry that matches `"target": "<rev>"` in `upstream.json` and the [`github-releases`](https://docs.renovatebot.com/modules/datasource/github-releases/) datasource for `modelcontextprotocol/modelcontextprotocol`. That opens a PR instead of an issue. This repo uses the issue workflow because a revision bump always needs rule work that a bot cannot write.

## Release policy

| Event | Release | What happens |
|---|---|---|
| Upstream publishes an RC | none | The tracking issue appears. Open a **draft** PR that adds the RC to `upstream.json` with `status: rc` and drafts rule changes. Keep it in draft. |
| Upstream publishes a final revision | **minor** | Add the revision as final, make it the `target`, keep the previous target in `supported`, write its conformance profile, update the README badge and table. |
| Drop a supported revision | **major** (minor while on 0.x) | Remove it from `supported`. Its frozen profile stays in the repo. |
| New SHOULD or SHOULD NOT rule | **minor** | |
| New MUST or MUST NOT rule, or a SHOULD raised to MUST | **major** (minor while on 0.x, flagged **Breaking** in CHANGELOG) | |
| Rule wording only, no change in meaning | **patch** | |
| Checker fix with no rule change | **patch** | |

While the spec is on 0.x, changes that would be major are released as minor. CHANGELOG marks them **Breaking** so readers can find them. Rule IDs are never reused; a retired rule keeps its ID with an `until` revision.

Each CHANGELOG release has an **Upstream** subsection: which MCP revisions are supported, which is the target, and what changed upstream since the last release (or "no change").

## Release steps

1. Update `CHANGELOG.md`, including **Upstream**.
2. Bump the version in `pyproject.toml`, `src/mcp_gateway_check/__init__.py`, and the SPEC.md header.
3. For a new revision: `python3 scripts/conformance.py --write <rev>`.
4. Merge with CI green, then tag `vX.Y.Z` on the merge commit and publish a GitHub release.
