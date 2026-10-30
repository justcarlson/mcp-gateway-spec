"""Lint the test fixtures: valid JSON, every file in the manifest, every manifest rule real and checked.

python3 scripts/lint_fixtures.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from mcp_gateway_check.rules import RULES  # noqa: E402

FIX = ROOT / "tests" / "fixtures"
UNLISTED = {"manifest.json"}  # files the manifest does not name
OWN_TESTS = {"upstream", "diff"}  # directories with their own tests


def lint() -> list[str]:
    problems = []
    for path in sorted(FIX.rglob("*.json")):
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            problems.append(f"{path.relative_to(ROOT)}: {exc}")
    manifest = json.loads((FIX / "manifest.json").read_text(encoding="utf-8"))
    used: set[Path] = set()
    for case in manifest["cases"]:
        target = FIX / case["input"]
        if not target.exists():
            problems.append(f"manifest: {case['input']} does not exist")
            continue
        used.update([target] if target.is_file() else target.rglob("*.json"))
        if not case.get("note"):
            problems.append(f"manifest: {case['input']} has no note")
        for rule in case["rules"]:
            if rule not in RULES:
                problems.append(f"manifest: {case['input']} names unknown rule {rule}")
            elif not RULES[rule].checked:
                problems.append(f"manifest: {case['input']} names {rule}, which the checker does not test")
        if case["exit"] == 0 and case["rules"] and case["input"].startswith("good/"):
            problems.append(f"manifest: good fixture {case['input']} expects findings")
    for path in sorted(FIX.rglob("*.json")):
        rel = path.relative_to(FIX)
        if rel.name in UNLISTED or rel.parts[0] in OWN_TESTS or path in used:
            continue
        problems.append(f"{path.relative_to(ROOT)}: not used by tests/fixtures/manifest.json")
    return problems


def main() -> int:
    problems = lint()
    for p in problems:
        print(p, file=sys.stderr)
    if not problems:
        print("fixtures ok")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
