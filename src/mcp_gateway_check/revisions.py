"""MCP revisions: read upstream.json and decide which rules apply to a revision.

The spec has its own SemVer version. The MCP revision is data, kept in
upstream.json at the repo root (packaged into the wheel as a copy).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import cache
from importlib import resources
from pathlib import Path
from typing import Any

from .model import InputError

DRAFT = "draft"
TARGET = "target"


@dataclass(frozen=True)
class Upstream:
    target: str
    supported: tuple[str, ...]
    revisions: dict[str, Any]

    def resolve(self, value: str) -> str:
        """Map a --mcp-revision value to a supported revision or "draft"."""
        if value == TARGET:
            return self.target
        if value == DRAFT or value in self.supported:
            return value
        known = ", ".join([f"{self.target} (target)"] + [r for r in self.supported if r != self.target])
        hint = "a known revision this spec version does not support" if value in self.revisions else "unknown"
        raise InputError(f"MCP revision {value!r} is {hint}; use one of: {known}, draft, target")

    def protocol(self, revision: str) -> str:
        """Protocol version string to send on the wire. Draft uses the target."""
        return self.target if revision == DRAFT else revision


def order(revision: str) -> str:
    """Sort key: dated revisions sort as strings; draft sorts after every dated one."""
    return "9999-99-99" if revision == DRAFT else revision


def applies(since: str, until: str | None, revision: str) -> bool:
    """True when `revision` is inside [since, until]. `until` is inclusive."""
    key = order(revision)
    if key < order(since):
        return False
    return until is None or key <= order(until)


def _read() -> str:
    packaged = resources.files(__package__).joinpath("upstream.json")
    if packaged.is_file():
        return packaged.read_text(encoding="utf-8")
    # Running from a source checkout: the file lives at the repo root.
    return (Path(__file__).resolve().parents[2] / "upstream.json").read_text(encoding="utf-8")


def parse(text: str) -> Upstream:
    try:
        doc = json.loads(text)
        mcp = doc["mcp"]
        up = Upstream(mcp["target"], tuple(mcp["supported"]), dict(mcp["revisions"]))
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise InputError(f"upstream.json is malformed: {exc}") from exc
    if up.target not in up.supported:
        raise InputError("upstream.json: target must be listed in supported")
    missing = [r for r in up.supported if r not in up.revisions]
    if missing:
        raise InputError(f"upstream.json: no revision entry for {', '.join(missing)}")
    return up


@cache
def load() -> Upstream:
    return parse(_read())
