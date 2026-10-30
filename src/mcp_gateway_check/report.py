"""Human and JSON reports."""

from __future__ import annotations

import json
from collections import defaultdict
from typing import Any

from . import SPEC_VERSION, __version__
from .checks import Finding
from .model import Inventory
from .rules import RULES

SEVERITIES = ("error", "warning", "info")
_ORDER = {s: i for i, s in enumerate(SEVERITIES)}


def _rule_key(rule_id: str) -> tuple[str, int]:
    family, _, num = rule_id.partition("-")
    return family, int(num) if num.isdigit() else 0


def summary(findings: list[Finding]) -> dict[str, int]:
    counts = {s: 0 for s in SEVERITIES}
    counts["waived"] = 0
    for f in findings:
        if f.waived:
            counts["waived"] += 1
        else:
            counts[f.severity] += 1
    return counts


def level_status(findings: list[Finding]) -> dict[str, bool]:
    """Checked-rule status for Level 1 (all MUST) and Level 2 (all MUST and SHOULD)."""
    active = [f for f in findings if not f.waived and not f.heuristic and f.rule != "CONF-3"]
    must = any(RULES[f.rule].mandatory for f in active)
    should = any(not RULES[f.rule].mandatory for f in active)
    return {"level1": not must, "level2": not must and not should}


def to_json(inv: Inventory | None, findings: list[Finding], revision: str, skipped: list[str]) -> str:
    doc: dict[str, Any] = {
        "checker": {"name": "mcp-gateway-check", "version": __version__, "spec_version": SPEC_VERSION},
        "mcp_revision": revision,
        "skipped_rules": skipped,
        "summary": summary(findings),
        "conformance": level_status(findings),
        "findings": [f.as_dict() for f in sort_findings(findings)],
    }
    if inv is not None:
        doc["inventory"] = {
            "namespace": inv.namespace,
            "discovery": inv.discovery,
            "groups": len(inv.groups),
            "tools": len(inv.tools),
            "skipped_inputs": inv.skipped,
            "live": inv.live,
        }
    return json.dumps(doc, indent=2)


def sort_findings(findings: list[Finding]) -> list[Finding]:
    return sorted(findings, key=lambda f: (f.waived, _ORDER[f.severity], _rule_key(f.rule), f.target))


def to_text(
    inv: Inventory | None,
    findings: list[Finding],
    revision: str,
    skipped: list[str],
    limit: int = 5,
    color: bool = False,
) -> str:
    def paint(text: str, code: str) -> str:
        return f"\033[{code}m{text}\033[0m" if color else text

    tags = {"error": paint("error", "31;1"), "warning": paint("warn ", "33"), "info": paint("info ", "36")}
    lines = []
    if inv is not None:
        lines.append(
            f"{len(inv.tools)} tools in {len(inv.groups)} groups "
            f"(namespace: {inv.namespace}, discovery: {inv.discovery})"
        )
        if inv.skipped:
            lines.append(f"skipped {len(inv.skipped)} non-tool inputs: {', '.join(inv.skipped[:5])}")
        for entry in inv.live:
            lines.append(f"live: {entry['url']} answered over MCP {entry['protocol']} ({entry['mode']})")
    lines.append(f"MCP revision {revision}")
    if skipped:
        noun = "rule" if len(skipped) == 1 else "rules"
        lines.append(f"skipped {len(skipped)} {noun} outside MCP {revision}: {', '.join(skipped)}")
    lines.append("")

    by_rule: dict[str, list[Finding]] = defaultdict(list)
    for f in sort_findings([f for f in findings if not f.waived]):
        by_rule[f.rule].append(f)
    rules = sorted(by_rule, key=lambda r: (min(_ORDER[f.severity] for f in by_rule[r]), _rule_key(r)))
    for rule_id in rules:
        items = by_rule[rule_id]
        rule = RULES[rule_id]
        lines.append(f"{tags[items[0].severity]} {paint(rule_id, '1')} {rule.level}: {rule.title} ({len(items)})")
        shown = items if limit <= 0 else items[:limit]
        for f in shown:
            note = " [catalog]" if f.source == "catalog" else ""
            guess = " (heuristic)" if f.heuristic else ""
            lines.append(f"      {f.target}{note}: {f.message}{guess}")
        if len(items) > len(shown):
            lines.append(f"      ... {len(items) - len(shown)} more (use --all)")
    waived = [f for f in findings if f.waived]
    if waived:
        lines.append(f"{paint('waived', '2')} {len(waived)} findings")
    counts = summary(findings)
    status = level_status(findings)
    if lines and lines[-1]:
        lines.append("")
    lines.append(
        f"{counts['error']} errors, {counts['warning']} warnings, {counts['info']} info, {counts['waived']} waived"
    )
    lines.append(
        "checked rules: Level 1 "
        + ("pass" if status["level1"] else "FAIL")
        + ", Level 2 "
        + ("pass" if status["level2"] else "FAIL")
        + " (manual rules need the review checklist)"
    )
    return "\n".join(lines)
