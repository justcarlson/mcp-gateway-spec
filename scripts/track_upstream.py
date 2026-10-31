"""Compare upstream MCP releases with upstream.json and open one tracking issue per new revision.

A new release candidate or final revision opens (or updates) one issue titled
"Track MCP <rev>" with the label "mcp-upstream". The body links the release and
the revision's changelog.mdx and lists its major changes. When the issue moves
to a new upstream tag (an RC becomes final), the label is applied again, so the
"labeled" webhook fires once per stage. This script never edits the repo; the
agent in docs/upstream-agent.md does.

    GITHUB_TOKEN=... GITHUB_REPOSITORY=owner/repo python3 scripts/track_upstream.py
    python3 scripts/track_upstream.py --dry-run --releases-file r.json --changelog-dir dir/ --issues-file i.json

Stdlib only. The token comes from $GITHUB_TOKEN, never from argv.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
API = "https://api.github.com"
_TAG = re.compile(r"^(\d{4}-\d{2}-\d{2})(-RC\d*)?$")
_MARKER = "<!-- track-upstream {rev} {tag} -->"
MAX_ITEMS = 12
LABEL = "mcp-upstream"


@dataclass
class Release:
    rev: str
    tag: str
    rc: bool
    url: str
    published_at: str


class GitHub:
    def __init__(self, token: str | None) -> None:
        self.token = token

    def request(self, method: str, path: str, body: Any = None, raw: bool = False) -> Any:
        headers = {
            "Accept": "application/vnd.github.raw" if raw else "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "mcp-gateway-spec-track-upstream",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(f"{API}{path}", data=data, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=30) as resp:
            text = resp.read().decode("utf-8")
        return text if raw else json.loads(text)


def parse_releases(items: list[dict[str, Any]]) -> list[Release]:
    out = []
    for item in items:
        m = _TAG.match(item.get("tag_name", ""))
        if not m or item.get("draft"):
            continue
        out.append(
            Release(m.group(1), item["tag_name"], bool(m.group(2)), item["html_url"], item.get("published_at", ""))
        )
    return out


def new_revisions(upstream: dict[str, Any], releases: list[Release]) -> list[Release]:
    """One release per revision that upstream.json does not yet track at that stage.

    A final release beats an RC of the same revision. Revisions older than the
    newest tracked one are ignored: the spec does not add support backwards.
    """
    revisions = upstream["mcp"]["revisions"]
    newest = max(revisions)
    best: dict[str, Release] = {}
    for rel in releases:
        known = revisions.get(rel.rev)
        if known is None:
            if rel.rev < newest:
                continue
        elif rel.rc or known.get("status") == "final":
            continue  # RC of a tracked revision, or final already tracked
        current = best.get(rel.rev)
        if current is None or (current.rc and not rel.rc) or (current.rc and rel.rc and rel.tag > current.tag):
            best[rel.rev] = rel
    return [best[r] for r in sorted(best)]


def changelog_path(rev: str) -> str:
    return f"docs/specification/{rev}/changelog.mdx"


def summarize(mdx: str) -> list[str]:
    """Top-level items under "## Major changes", plain text, one line each."""
    section = re.split(r"^## Major changes\s*$", mdx, maxsplit=1, flags=re.M)
    if len(section) < 2:
        return []
    body = re.split(r"^## ", section[1], maxsplit=1, flags=re.M)[0]
    items = []
    for line in body.splitlines():
        m = re.match(r"^(?:\d+\.|[-*])\s+(.*)", line)
        if not m:
            continue
        text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", m.group(1))  # links -> text
        text = re.sub(r"\s+", " ", text).strip()
        sentence = re.split(r"(?<=[.!?])\s", text, maxsplit=1)[0]
        items.append(sentence if len(sentence) <= 200 else sentence[:197] + "...")
    return items[:MAX_ITEMS]


def issue_title(rev: str) -> str:
    return f"Track MCP {rev}"


def issue_body(own_repo: str, upstream_repo: str, rel: Release, items: list[str]) -> str:
    stage = "release candidate" if rel.rc else "final revision"
    changelog = f"https://github.com/{upstream_repo}/blob/{rel.tag}/{changelog_path(rel.rev)}"
    lines = [
        _MARKER.format(rev=rel.rev, tag=rel.tag),
        f"Upstream published MCP {rel.rev} as a **{stage}** (`{rel.tag}`, {rel.published_at[:10]}).",
        "",
        f"- Release: {rel.url}",
        f"- Changelog: {changelog}",
        f"- Agent: the `{LABEL}` label starts the [upstream agent](https://github.com/{own_repo}/blob/main/docs/upstream-agent.md)",
        "",
        "## Major changes (from the changelog)",
        "",
    ]
    lines += [f"- {item}" for item in items] or ['- (no "Major changes" section found; read the changelog)']
    lines += [
        "",
        f"## Next steps ([docs/versioning.md](https://github.com/{own_repo}/blob/main/docs/versioning.md))",
        "",
    ]
    if rel.rc:
        lines += [
            "- [ ] Open a draft PR that adds the RC to `upstream.json` (status `rc`) and drafts rule changes",
            "- [ ] Set `since`/`until` on new or changed rules; run the checker with `--mcp-revision draft`",
            "- [ ] Keep the PR in draft until the final revision ships",
        ]
    else:
        lines += [
            f"- [ ] Add {rel.rev} to `upstream.json` (status `final`, tag, commit, `verified_on`); make it the target",
            "- [ ] Keep the previous target in `supported`",
            f"- [ ] Write `conformance/mcp-{rel.rev}.yaml` with `scripts/conformance.py --write {rel.rev}`",
            "- [ ] Update the README badge and compatibility table; add an Upstream note to CHANGELOG",
            "- [ ] Release a minor version",
        ]
    return "\n".join(lines) + "\n"


def plan(
    own_repo: str,
    upstream_repo: str,
    upstream: dict[str, Any],
    releases: list[Release],
    issues: list[dict[str, Any]],
    changelog: Any,
) -> list[dict[str, Any]]:
    """Actions to take: create or update an issue per new revision. `changelog(rel)` returns mdx text."""
    actions = []
    for rel in new_revisions(upstream, releases):
        title = issue_title(rel.rev)
        body = issue_body(own_repo, upstream_repo, rel, summarize(changelog(rel)))
        existing = next((i for i in issues if i.get("title") == title and "pull_request" not in i), None)
        if existing is None:
            actions.append({"action": "create", "title": title, "body": body})
            continue
        if existing.get("state", "open") != "open":
            continue  # a maintainer closed it; do not reopen it or start the agent again
        labeled = any(label.get("name") == LABEL for label in existing.get("labels") or [])
        new_tag = _MARKER.format(rev=rel.rev, tag=rel.tag) not in (existing.get("body") or "")
        new_body = existing.get("body") != body
        # Relabel on a new upstream tag, and repair a label that an earlier failed run left off.
        relabel = new_tag or not labeled
        if new_body or relabel:
            actions.append(
                {
                    "action": "update",
                    "number": existing["number"],
                    "title": title,
                    "body": body if new_body else None,
                    "labeled": labeled,
                    "relabel": relabel,
                }
            )
    return actions


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--upstream", type=Path, default=ROOT / "upstream.json")
    ap.add_argument("--dry-run", action="store_true", help="print actions; change nothing")
    ap.add_argument("--releases-file", type=Path, help="read upstream releases from this JSON file")
    ap.add_argument("--changelog-dir", type=Path, help="read <rev>.mdx changelogs from this directory")
    ap.add_argument("--issues-file", type=Path, help="read this repo's tracking issues from this JSON file")
    args = ap.parse_args(argv)

    upstream = json.loads(args.upstream.read_text(encoding="utf-8"))
    upstream_repo = upstream["mcp"]["repo"]
    own_repo = os.environ.get("GITHUB_REPOSITORY", "justcarlson/mcp-gateway-spec")
    gh = GitHub(os.environ.get("GITHUB_TOKEN"))

    if args.releases_file:
        raw = json.loads(args.releases_file.read_text(encoding="utf-8"))
    else:
        raw = gh.request("GET", f"/repos/{upstream_repo}/releases?per_page=100")
    releases = parse_releases(raw)

    if args.issues_file:
        issues = json.loads(args.issues_file.read_text(encoding="utf-8"))
    elif args.dry_run and not gh.token:
        issues = []
    else:
        # Closed issues too, so a closed tracking issue is not opened again. Only the bot's issues.
        issues = gh.request("GET", f"/repos/{own_repo}/issues?state=all&creator=github-actions%5Bbot%5D&per_page=100")

    def changelog(rel: Release) -> str:
        if args.changelog_dir:
            path = args.changelog_dir / f"{rel.rev}.mdx"
            return path.read_text(encoding="utf-8") if path.is_file() else ""
        quoted = urllib.parse.quote(changelog_path(rel.rev))
        try:
            return gh.request("GET", f"/repos/{upstream_repo}/contents/{quoted}?ref={rel.tag}", raw=True)
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return ""
            raise

    actions = plan(own_repo, upstream_repo, upstream, releases, issues, changelog)
    if not actions:
        print("upstream.json is current; no new MCP revisions")
        return 0
    for act in actions:
        verb = {"create": "create", "update": f"update #{act.get('number')}"}[act["action"]]
        relabel = f" and re-apply {LABEL!r}" if act.get("relabel") else ""
        print(f"{'would ' if args.dry_run else ''}{verb} issue {act['title']!r}{relabel}")
        if args.dry_run:
            if act["body"] is not None:
                print(act["body"])
            continue
        if act["action"] == "create":
            gh.request(
                "POST", f"/repos/{own_repo}/issues", {"title": act["title"], "body": act["body"], "labels": [LABEL]}
            )
            continue
        # Order: remove the label, update the body, add the label. If a step fails,
        # the next run sees a new tag or a missing label and finishes the job.
        number = act["number"]
        if act["relabel"] and act["labeled"]:
            try:
                gh.request("DELETE", f"/repos/{own_repo}/issues/{number}/labels/{LABEL}")
            except urllib.error.HTTPError as exc:
                if exc.code != 404:  # 404: the label is already off
                    raise
        if act["body"] is not None:
            gh.request("PATCH", f"/repos/{own_repo}/issues/{number}", {"body": act["body"]})
        if act["relabel"]:
            gh.request("POST", f"/repos/{own_repo}/issues/{number}/labels", {"labels": [LABEL]})
    return 0


if __name__ == "__main__":
    sys.exit(main())
