"""Compare two snapshots of one view.

- "change" mode checks that NEW is a compatible successor of OLD (CHG rules).
- "sync" mode checks that an edge copy (NEW) matches its upstream (OLD) (EDGE-3).
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

from .checks import Finding, finding
from .model import Inventory, Tool


def _types(schema: dict[str, Any]) -> set[str]:
    t = schema.get("type")
    if isinstance(t, str):
        return {t}
    if isinstance(t, list):
        return {x for x in t if isinstance(x, str)}
    return set()


def schema_breaks(old: Any, new: Any, path: str = "") -> Iterator[str]:
    """Yield reasons why `new` would reject input that `old` accepted."""
    if not isinstance(old, dict) or not isinstance(new, dict):
        return
    where = path or "input"
    old_t, new_t = _types(old), _types(new)
    if old_t and new_t and not old_t <= new_t and not (old_t == {"integer"} and "number" in new_t):
        yield f"{where}: type {sorted(old_t)} became {sorted(new_t)}"
    elif new_t and not old_t and not {"enum", "const", "$ref", "anyOf", "oneOf", "allOf"} & old.keys():
        yield f"{where}: new type restriction {sorted(new_t)}"
    if isinstance(old.get("enum"), list) and isinstance(new.get("enum"), list):
        lost = [v for v in old["enum"] if v not in new["enum"]]
        if lost:
            yield f"{where}: enum values removed: {', '.join(map(str, lost[:5]))}"
    elif "enum" in new and "enum" not in old:
        yield f"{where}: new enum restriction"
    old_props = old.get("properties") if isinstance(old.get("properties"), dict) else {}
    new_props = new.get("properties") if isinstance(new.get("properties"), dict) else {}
    old_req = set(old.get("required") or [])
    new_req = set(new.get("required") or [])
    for key in old_props:
        if key not in new_props:
            yield f"{where}.{key}: property removed"
    for key in sorted(new_req - old_req):
        yield f"{where}.{key}: now required"
    if old.get("additionalProperties") is not False and new.get("additionalProperties") is False and old_props:
        yield f"{where}: additionalProperties became false"
    for key in old_props:
        if key in new_props:
            yield from schema_breaks(old_props[key], new_props[key], f"{where}.{key}")
    if isinstance(old.get("items"), dict) and isinstance(new.get("items"), dict):
        yield from schema_breaks(old["items"], new["items"], f"{where}[]")


def output_breaks(old: Any, new: Any, path: str = "") -> Iterator[str]:
    """Yield reasons why `new` output would break a consumer of `old` output."""
    if not isinstance(old, dict):
        return
    if not isinstance(new, dict):
        yield "outputSchema removed"
        return
    where = path or "output"
    old_props = old.get("properties") if isinstance(old.get("properties"), dict) else {}
    new_props = new.get("properties") if isinstance(new.get("properties"), dict) else {}
    for key in old_props:
        if key not in new_props:
            yield f"{where}.{key}: field removed"
        else:
            o, n = _types(old_props[key]), _types(new_props[key])
            if o and n and o != n:
                yield f"{where}.{key}: type {sorted(o)} became {sorted(n)}"
            yield from output_breaks(old_props[key], new_props[key], f"{where}.{key}")
    for key in sorted(set(old.get("required") or []) - set(new.get("required") or [])):
        yield f"{where}.{key}: no longer guaranteed"


def _index(inv: Inventory, strip_prefix: str = "", by_exposed: bool = False) -> dict[str, Tool]:
    out = {}
    for t in inv.tools:
        key = t.ref if inv.namespace == "path" and not by_exposed else t.exposed
        if strip_prefix and key.startswith(strip_prefix):
            key = key[len(strip_prefix) :]
        out[key] = t
    return out


def _deprecated(tool: Tool) -> bool:
    return tool.description.lstrip().lower().startswith("deprecated")


def diff_change(old: Inventory, new: Inventory, aliases: dict[str, str]) -> list[Finding]:
    # Snapshots read in different namespace modes share only the exposed name.
    by_exposed = old.namespace != new.namespace
    before, after = _index(old, by_exposed=by_exposed), _index(new, by_exposed=by_exposed)
    out: list[Finding] = []
    for name, tool in before.items():
        if name not in after:
            target = aliases.get(name)
            if target is None:
                out.append(finding("CHG-1", f"{name!r} was removed with no alias", tool=tool))
            elif target not in after:
                out.append(finding("CHG-1", f"alias {name!r} -> {target!r} points to a missing tool", tool=tool))
            continue
        cur = after[name]
        for reason in schema_breaks(tool.input_schema, cur.input_schema):
            out.append(finding("CHG-3", reason, tool=cur))
        for reason in output_breaks(tool.raw.get("outputSchema"), cur.raw.get("outputSchema")):
            out.append(finding("CHG-4", reason, tool=cur))
        oa, na = tool.annotations, cur.annotations
        if oa.get("readOnlyHint") is not True and na.get("readOnlyHint") is True:
            out.append(
                finding("CHG-9", "readOnlyHint became true; confirm the reviewer signed off", tool=cur, heuristic=True)
            )
        if (
            oa.get("destructiveHint") is not False
            and na.get("destructiveHint") is False
            and na.get("readOnlyHint") is not True
        ):
            out.append(
                finding(
                    "CHG-9", "destructiveHint became false; confirm the reviewer signed off", tool=cur, heuristic=True
                )
            )
        if tool.approval == "required" and cur.approval == "none":
            out.append(finding("CHG-9", "approval changed from required to none", tool=cur, heuristic=True))
        if _deprecated(cur) and not _deprecated(tool):
            out.append(
                finding(
                    "CHG-2", "tool is now deprecated; keep it for 30 days and one release", tool=cur, heuristic=True
                )
            )
    return out


def _canon(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def diff_sync(upstream: Inventory, edge: Inventory, strip_prefix: str) -> list[Finding]:
    up, ed = _index(upstream), _index(edge, strip_prefix)
    out: list[Finding] = []
    for name, tool in ed.items():
        src = up.get(name)
        if src is None:
            out.append(finding("EDGE-3", f"edge serves {tool.exposed!r}, which upstream no longer has", tool=tool))
            continue
        for field in ("description", "inputSchema", "outputSchema", "annotations", "title"):
            if _canon(src.raw.get(field)) != _canon(tool.raw.get(field)):
                out.append(
                    finding("EDGE-3", f"edge copy of {field} differs from upstream; run the edge sync", tool=tool)
                )
    return out
