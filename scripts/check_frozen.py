"""Fail if a released conformance profile changed after the tag that froze it.

Each profile names its tag in `frozen_in:`. If that tag exists in the repo,
the file must match the tagged copy byte for byte. Profiles whose tag does not
exist yet (the release in progress) may still change.

    python3 scripts/check_frozen.py [--repo PATH]

CI runs this with full history (fetch-depth: 0) so tags are present.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

_FROZEN_IN = re.compile(r"^frozen_in: (\S+)$", re.M)


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=False)


def check(repo: Path) -> list[str]:
    problems = []
    for path in sorted((repo / "conformance").glob("mcp-*.yaml")):
        rel = path.relative_to(repo).as_posix()
        m = _FROZEN_IN.search(path.read_text(encoding="utf-8"))
        if not m:
            problems.append(f"{rel}: no frozen_in line")
            continue
        tag = m.group(1)
        if _git(repo, "rev-parse", "-q", "--verify", f"refs/tags/{tag}").returncode != 0:
            continue  # not released yet
        tagged = _git(repo, "show", f"{tag}:{rel}")
        if tagged.returncode != 0:
            problems.append(f"{rel}: frozen_in {tag}, but the file is not in that tag")
        elif tagged.stdout != path.read_text(encoding="utf-8"):
            problems.append(f"{rel}: changed after {tag}; released profiles are frozen. Add a new profile instead.")
    return problems


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", type=Path, default=Path(__file__).resolve().parent.parent)
    args = ap.parse_args(argv)
    problems = check(args.repo)
    for p in problems:
        print(p, file=sys.stderr)
    if not problems:
        print("frozen profiles unchanged")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
