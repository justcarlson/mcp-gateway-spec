"""Static checks over one inventory. Each check maps to a rule in SPEC.md."""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from .model import Group, Inventory, Tool
from .rules import RULES

# Thresholds come from the ADRs in docs/decisions/.
MAX_NAME = 128  # MCP 2026-07-28
MAX_EXPOSED = 64  # ADR-0004
TARGET_EXPOSED = 48  # ADR-0004
TARGET_LEAF = 32  # ADR-0004
MAX_GROUP_TOOLS = 10  # ADR-0005
FLAT_TOOLS, FLAT_TOKENS = 10, 10_000  # ADR-0005
HARD_FLAT_TOOLS, HARD_FLAT_TOKENS = 50, 25_000  # ADR-0005
DESC_MIN, DESC_TARGET, DESC_MAX = 80, 1_024, 4_096  # ADR-0006
FIRST_SENTENCE_MAX = 160  # ADR-0006
GROUP_DESC_MAX = 300  # ADR-0006
INSTR_TARGET, INSTR_MAX = 2_048, 4_096  # ADR-0006

MCP_NAME = re.compile(r"^[A-Za-z0-9_.-]{1,128}$")
SNAKE = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
SLUG = re.compile(r"^[a-z][a-z0-9]{1,19}$")  # ADR-0003
HINTS = ("readOnlyHint", "destructiveHint", "idempotentHint", "openWorldHint")

READ_VERBS = frozenset(
    [
        "get",
        "list",
        "search",
        "find",
        "read",
        "query",
        "fetch",
        "lookup",
        "resolve",
        "check",
        "count",
        "describe",
        "show",
        "browse",
        "preview",
        "inspect",
        "view",
        "summarize",
        "analyze",
        "compare",
        "validate",
        "verify",
        "status",
        "ping",
        "download",
        "export",
        "explain",
        "diff",
        "watch",
        "poll",
        "estimate",
        "calculate",
        "convert",
        "render",
        "translate",
        "transcribe",
        "extract",
        "scrape",
        "crawl",
        "map",
        "discover",
        "recommend",
        "suggest",
        "test",
    ]
)
WRITE_VERBS = frozenset(
    [
        "create",
        "add",
        "insert",
        "update",
        "set",
        "edit",
        "modify",
        "patch",
        "rename",
        "move",
        "copy",
        "upsert",
        "delete",
        "remove",
        "cancel",
        "archive",
        "unarchive",
        "restore",
        "send",
        "post",
        "reply",
        "publish",
        "upload",
        "import",
        "sync",
        "run",
        "execute",
        "start",
        "stop",
        "restart",
        "pause",
        "resume",
        "enable",
        "disable",
        "toggle",
        "approve",
        "reject",
        "request",
        "subscribe",
        "unsubscribe",
        "confirm",
        "schedule",
        "trigger",
        "install",
        "uninstall",
        "deploy",
        "build",
        "write",
        "append",
        "clear",
        "reset",
        "apply",
        "submit",
        "grant",
        "revoke",
        "invite",
        "assign",
        "unassign",
        "merge",
        "lock",
        "unlock",
        "block",
        "unblock",
        "purge",
        "drop",
        "destroy",
        "kill",
        "reboot",
        "shutdown",
        "wipe",
        "play",
        "queue",
        "skip",
        "mark",
        "accept",
        "decline",
        "like",
        "follow",
        "unfollow",
        "star",
        "unstar",
        "pin",
        "unpin",
        "save",
        "store",
        "push",
        "commit",
        "close",
        "reopen",
        "tag",
        "label",
        "comment",
        "transfer",
        "click",
        "type",
        "press",
        "fill",
        "drag",
    ]
)
# Verbs that are fine as a first word but say nothing about side effects.
OTHER_VERBS = frozenset(
    [
        "open",
        "refresh",
        "scan",
        "generate",
        "take",
        "capture",
        "select",
        "navigate",
        "hover",
        "evaluate",
        "review",
        "wait",
    ]
)
DESTRUCTIVE = frozenset(
    ["delete", "remove", "purge", "drop", "destroy", "kill", "wipe", "revoke", "uninstall", "reset", "clear"]
)
VERBS = READ_VERBS | WRITE_VERBS | OTHER_VERBS
ACTION_PARAMS = frozenset({"action", "method", "operation", "op", "mode", "command", "cmd"})

HIDDEN_DIRECTIVES = [
    re.compile(p, re.I)
    for p in (
        r"ignore (?:all |any )?(?:previous|prior|above|earlier) (?:instructions|messages)",
        r"<\s*/?\s*(?:important|system|instructions?)\s*>",
        r"do not (?:tell|inform|mention|show)(?: this)? (?:to )?the user",
        r"\bsystem prompt\b",
        r"before (?:using|calling) any other tool",
    )
]
SECRET_PATTERNS = [
    re.compile(p)
    for p in (
        r"\b(?:sk|pk|rk)-[A-Za-z0-9_-]{20,}",
        r"\bgh[pousr]_[A-Za-z0-9]{30,}",
        r"\bAKIA[0-9A-Z]{16}\b",
        r"\bxox[abpr]-[A-Za-z0-9-]{10,}",
        r"(?i)\bbearer\s+[A-Za-z0-9._~+/-]{24,}",
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    )
]
PRIVATE_ENDPOINTS = re.compile(
    r"\b(?:10\.\d{1,3}|192\.168|172\.(?:1[6-9]|2\d|3[01])|100\.(?:6[4-9]|[7-9]\d|1[01]\d|12[0-7]))"
    r"\.\d{1,3}\.\d{1,3}\b"
    r"|\b[a-z0-9-]+(?:\.[a-z0-9-]+)*\.(?:internal|lan|home\.arpa|corp)\b",
    re.I,
)
READ_ONLY_CLAIM = re.compile(r"\bread[- ]only\b", re.I)
APPROVAL_CLAIM = re.compile(
    r"\b(?:writes?|changes?|mutations?)\b[^.]{0,30}\b(?:ask|need|require)s?\b[^.]{0,15}\bapproval", re.I
)
CREDENTIAL_PARAM = re.compile(
    r"^(?:api[_-]?key|apikey|access[_-]?token|oauth[_-]?token|refresh[_-]?token|id[_-]?token|"
    r"token|password|passwd|secret|client[_-]?secret|private[_-]?key|authorization|bearer)$",
    re.I,
)


@dataclass
class Finding:
    rule: str
    severity: str  # error, warning, info
    message: str
    group: str | None = None
    tool: str | None = None
    source: str | None = None
    heuristic: bool = False
    waived: bool = False
    waiver_reason: str | None = None

    @property
    def target(self) -> str:
        if self.group and self.tool:
            return f"{self.group}/{self.tool}"
        return self.tool or self.group or "*"

    def as_dict(self) -> dict[str, Any]:
        rule = RULES[self.rule]
        out: dict[str, Any] = {
            "rule": self.rule,
            "level": rule.level,
            "severity": self.severity,
            "target": self.target,
            "group": self.group,
            "tool": self.tool,
            "message": self.message,
            "heuristic": self.heuristic,
            "url": rule.url,
        }
        if self.source:
            out["source"] = self.source
        if self.waived:
            out["waived"] = True
            out["waiver_reason"] = self.waiver_reason
        return out


def finding(
    rule_id: str,
    message: str,
    *,
    tool: Tool | None = None,
    group: str | None = None,
    heuristic: bool = False,
    source: str | None = None,
) -> Finding:
    """Make a finding. Severity follows the rule level; heuristics drop one step."""
    rule = RULES[rule_id]
    if rule.mandatory:
        severity = "warning" if heuristic else "error"
    elif rule.level.startswith("SHOULD"):
        severity = "info" if heuristic else "warning"
    else:
        severity = "info"
    return Finding(
        rule=rule_id,
        severity=severity,
        message=message,
        group=tool.group if tool else group,
        tool=tool.name if tool else None,
        source=(tool.source if tool else source),
        heuristic=heuristic,
    )


def words(name: str) -> list[str]:
    """Split snake, kebab, dotted, and camelCase names into lowercase words."""
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", name)
    spaced = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", spaced)
    return [w.lower() for w in re.split(r"[\s_.\-]+", spaced) if w]


def first_sentence(text: str) -> str:
    text = text.strip()
    match = re.search(r"(?<=[.!?])\s|\n", text)
    return text[: match.start()].strip() if match else text


def tokens(tool: Tool) -> int:
    """Rough token count for a definition: compact JSON length divided by four."""
    keep = {
        k: v
        for k, v in tool.raw.items()
        if k in ("name", "title", "description", "inputSchema", "outputSchema", "annotations")
    }
    return len(json.dumps(keep, separators=(",", ":"), ensure_ascii=False)) // 4


def _properties(schema: Any) -> dict[str, Any]:
    if isinstance(schema, dict) and isinstance(schema.get("properties"), dict):
        return schema["properties"]
    return {}


SCHEMA_MAPS = {"properties", "patternProperties", "$defs", "definitions", "dependentSchemas"}
SCHEMA_DATA = {"enum", "const", "default", "examples"}


def _walk_schema(schema: Any) -> Iterator[tuple[str, Any]]:
    """Yield (keyword, value) pairs for every nested schema node.

    Property names and literal values (enum, default) are data, not keywords.
    """
    stack = [schema]
    while stack:
        node = stack.pop()
        if isinstance(node, dict):
            for key, value in node.items():
                yield key, value
                if key in SCHEMA_MAPS and isinstance(value, dict):
                    stack.extend(value.values())
                elif key not in SCHEMA_DATA:
                    stack.append(value)
        elif isinstance(node, list):
            stack.extend(node)


def _name_style(name: str) -> str | None:
    if "_" in name and name == name.lower():
        return "snake_case"
    if "-" in name:
        return "kebab-case"
    if re.search(r"[a-z][A-Z]", name) and name[0].islower():
        return "camelCase"
    return None  # one word: compatible with every style


# --- tool checks -------------------------------------------------------------


def check_tool(inv: Inventory, tool: Tool) -> Iterator[Finding]:
    yield from _naming(inv, tool)
    yield from _description(tool)
    yield from _schema(tool)
    yield from _annotations(tool)


def _naming(inv: Inventory, tool: Tool) -> Iterator[Finding]:
    raw_name = tool.raw.get("name", "")
    if not MCP_NAME.match(raw_name):
        yield finding("NAME-1", f"name {raw_name!r} is not 1-128 characters of [A-Za-z0-9_.-]", tool=tool)
    if inv.is_meta(tool):
        return
    segments = tool.name.split(".")
    if not SNAKE.match(tool.leaf):
        yield finding("NAME-3", f"{tool.leaf!r} is not snake_case", tool=tool)
    for seg in segments[:-1]:
        if not IDENT.match(seg):
            yield finding("NAME-3", f"namespace segment {seg!r} is not an identifier", tool=tool)
    leaf_words = words(tool.leaf)
    if tool.group:
        # Compare without separators so "pi_hole_get_stats" matches slug "pihole" or "pi-hole".
        slug_joined = "".join(words(tool.group))
        for k in range(1, len(leaf_words)):
            if "".join(leaf_words[:k]) == slug_joined:
                leaf_words = leaf_words[k:]
                yield finding("NAME-7", f"{tool.leaf!r} starts with the group slug {tool.group!r}", tool=tool)
                break
    if leaf_words and leaf_words[0] not in VERBS and len(leaf_words) > 1:
        yield finding("NAME-4", f"{tool.leaf!r} does not start with a known verb", tool=tool, heuristic=True)
    if tool.leaf in inv.meta_tools or (tool.group and tool.leaf.lower() in inv.meta_tools):
        yield finding("NAME-8", f"{tool.leaf!r} reuses a meta-tool name ({', '.join(inv.meta_tools)})", tool=tool)
    if len(tool.exposed) > MAX_EXPOSED:
        yield finding(
            "NAME-5", f"exposed name {tool.exposed!r} is {len(tool.exposed)} characters (max {MAX_EXPOSED})", tool=tool
        )
    elif len(tool.exposed) > TARGET_EXPOSED:
        yield finding(
            "NAME-6",
            f"exposed name {tool.exposed!r} is {len(tool.exposed)} characters (target {TARGET_EXPOSED})",
            tool=tool,
        )
    elif len(tool.leaf) > TARGET_LEAF:
        yield finding(
            "NAME-6", f"tool name {tool.leaf!r} is {len(tool.leaf)} characters (target {TARGET_LEAF})", tool=tool
        )
    title = tool.raw.get("title") or tool.annotations.get("title")
    if not (isinstance(title, str) and title.strip()):
        yield finding("NAME-10", "no title", tool=tool)


def _description(tool: Tool) -> Iterator[Finding]:
    desc = tool.description.strip()
    if not desc:
        yield finding("DESC-1", "no description", tool=tool)
    else:
        n = len(desc)
        if n > DESC_MAX:
            yield finding("DESC-3", f"description is {n} characters (max {DESC_MAX})", tool=tool)
        elif n > DESC_TARGET or n < DESC_MIN:
            yield finding("DESC-2", f"description is {n} characters (target {DESC_MIN}-{DESC_TARGET})", tool=tool)
        first = first_sentence(desc)
        if len(first) > FIRST_SENTENCE_MAX:
            yield finding("DESC-4", f"first sentence is {len(first)} characters (max {FIRST_SENTENCE_MAX})", tool=tool)
    yield from _text_hazards(tool.description + " " + str(tool.raw.get("title") or ""), tool=tool)
    if READ_ONLY_CLAIM.search(desc):
        ann = tool.annotations
        if ann.get("readOnlyHint") is False or ann.get("destructiveHint") is True:
            yield finding("DESC-8", "description says read-only but readOnlyHint is false", tool=tool, heuristic=True)
        elif tool.approval == "required" and ann.get("readOnlyHint") is not True:
            yield finding(
                "DESC-8", "description says read-only but the gateway requires approval", tool=tool, heuristic=True
            )


def _text_hazards(
    text: str, *, tool: Tool | None = None, group: str | None = None, source: str | None = None
) -> Iterator[Finding]:
    for pattern in HIDDEN_DIRECTIVES:
        if m := pattern.search(text):
            yield finding(
                "DESC-7",
                f"possible hidden directive: {m.group(0)!r}",
                tool=tool,
                group=group,
                heuristic=True,
                source=source,
            )
    for pattern in SECRET_PATTERNS:
        if pattern.search(text):
            yield finding("DESC-7", "possible secret in metadata", tool=tool, group=group, source=source)
    if m := PRIVATE_ENDPOINTS.search(text):
        yield finding(
            "DESC-7",
            f"private endpoint in metadata: {m.group(0)!r}",
            tool=tool,
            group=group,
            heuristic=True,
            source=source,
        )


def _schema(tool: Tool) -> Iterator[Finding]:
    schema = tool.input_schema
    if not isinstance(schema, dict) or schema.get("type") != "object":
        yield finding("SCHEMA-1", 'inputSchema is missing or its type is not "object"', tool=tool)
        return
    props = _properties(schema)
    if (
        not props
        and not schema.get("anyOf")
        and not schema.get("oneOf")
        and schema.get("additionalProperties") is not False
    ):
        yield finding("SCHEMA-2", "no-argument tool does not set additionalProperties: false", tool=tool)
    undocumented = [k for k, v in props.items() if not (isinstance(v, dict) and v.get("description"))]
    if undocumented:
        shown = ", ".join(undocumented[:5]) + (" ..." if len(undocumented) > 5 else "")
        yield finding(
            "SCHEMA-3", f"{len(undocumented)} of {len(props)} properties lack a description: {shown}", tool=tool
        )
    if any(k in ("$ref", "$defs", "definitions") for k, _ in _walk_schema(schema)):
        yield finding("SCHEMA-5", "inputSchema uses $ref or $defs", tool=tool)
    creds = sorted(
        key
        for node_key, node in _walk_schema(schema)
        if node_key == "properties" and isinstance(node, dict)
        for key in node
        if CREDENTIAL_PARAM.match(key)
    )
    if creds:
        yield finding("SCHEMA-7", f"input exposes credential parameters: {', '.join(creds)}", tool=tool, heuristic=True)
    for key, spec in props.items():
        if key.lower() in ACTION_PARAMS and isinstance(spec, dict) and isinstance(spec.get("enum"), list):
            values = [str(v) for v in spec["enum"]]
            reads = [v for v in values if words(v) and words(v)[0] in READ_VERBS]
            writes = [v for v in values if words(v) and words(v)[0] in WRITE_VERBS]
            if reads and writes:
                yield finding(
                    "GRP-6",
                    f"{key!r} mixes reads ({', '.join(reads[:3])}) and writes ({', '.join(writes[:3])})",
                    tool=tool,
                    heuristic=True,
                )


def _annotations(tool: Tool) -> Iterator[Finding]:
    ann = tool.annotations
    missing = [h for h in HINTS if not isinstance(ann.get(h), bool)]
    if missing:
        yield finding("ANN-1", f"missing hints: {', '.join(missing)}", tool=tool)
    read_only = ann.get("readOnlyHint") is True
    leaf_words = words(tool.leaf)
    verb = leaf_words[0] if leaf_words else ""
    if read_only and ann.get("destructiveHint") is True:
        yield finding("ANN-2", "readOnlyHint and destructiveHint are both true", tool=tool)
    elif read_only and (verb in WRITE_VERBS - READ_VERBS or DESTRUCTIVE & set(leaf_words)):
        yield finding(
            "ANN-2", f"readOnlyHint is true but the name suggests a write ({verb!r})", tool=tool, heuristic=True
        )
    if tool.approval == "none":
        if ann.get("destructiveHint") is True or ann.get("readOnlyHint") is False:
            yield finding("ANN-4", "runs without approval but its hints declare writes", tool=tool)
        elif not read_only and (verb in WRITE_VERBS - READ_VERBS or DESTRUCTIVE & set(leaf_words)):
            yield finding(
                "ANN-4", f"runs without approval but the name suggests a write ({verb!r})", tool=tool, heuristic=True
            )


# --- group and view checks ---------------------------------------------------


def check_group(inv: Inventory, group: Group) -> Iterator[Finding]:
    src = group.source
    if not SLUG.match(group.slug):
        yield finding("GRP-2", f"slug {group.slug!r} does not match {SLUG.pattern}", group=group.slug, source=src)
    if len(group.tools) > MAX_GROUP_TOOLS:
        yield finding("GRP-4", f"{len(group.tools)} tools (target <= {MAX_GROUP_TOOLS})", group=group.slug, source=src)
    if group.has_metadata:
        desc = (group.description or "").strip()
        if not desc:
            yield finding("DESC-9", "group has no description", group=group.slug, source=src)
        elif len(desc) > GROUP_DESC_MAX:
            yield finding(
                "DESC-10",
                f"group description is {len(desc)} characters (max {GROUP_DESC_MAX})",
                group=group.slug,
                source=src,
            )
        yield from _text_hazards(desc + " " + (group.instructions or ""), group=group.slug, source=src)
        if (
            desc
            and APPROVAL_CLAIM.search(desc)
            and group.tools
            and all(t.annotations.get("readOnlyHint") is True or t.approval == "none" for t in group.tools)
        ):
            yield finding(
                "DESC-8",
                "group description mentions approval for writes, but no tool needs approval",
                group=group.slug,
                heuristic=True,
                source=src,
            )
        instr = (group.instructions or "").strip()
        if len(instr) > INSTR_MAX:
            yield finding(
                "DESC-12", f"instructions are {len(instr)} characters (max {INSTR_MAX})", group=group.slug, source=src
            )
        elif len(instr) > INSTR_TARGET:
            yield finding(
                "DESC-11",
                f"instructions are {len(instr)} characters (target {INSTR_TARGET})",
                group=group.slug,
                source=src,
            )
    styles: Counter[str] = Counter()
    for tool in group.tools:
        for key in _properties(tool.input_schema):
            if style := _name_style(key):
                styles[style] += 1
    if len(styles) > 1:
        mix = ", ".join(f"{s} x{n}" for s, n in styles.most_common())
        yield finding("SCHEMA-4", f"parameter names mix styles: {mix}", group=group.slug, source=src)


def check_view(inv: Inventory) -> Iterator[Finding]:
    seen: dict[str, list[Tool]] = defaultdict(list)
    for tool in inv.tools:
        key = (f"{tool.group}.{tool.name}" if inv.namespace == "path" else tool.exposed).lower()
        seen[key].append(tool)
    for dupes in seen.values():
        if len(dupes) > 1:
            names = ", ".join(sorted({t.ref for t in dupes}))
            yield finding("NAME-2", f"{len(dupes)} tools share a name (ignoring case): {names}", tool=dupes[0])
    if inv.discovery == "flat":
        count = len(inv.tools)
        total = sum(tokens(t) for t in inv.tools)
        if count > HARD_FLAT_TOOLS or total > HARD_FLAT_TOKENS:
            yield finding(
                "DISC-2",
                f"flat view has {count} tools and ~{total:,} tokens of definitions "
                f"(limit {HARD_FLAT_TOOLS} tools / {HARD_FLAT_TOKENS:,} tokens)",
            )
        elif count > FLAT_TOOLS or total > FLAT_TOKENS:
            yield finding(
                "DISC-1",
                f"flat view has {count} tools and ~{total:,} tokens of definitions "
                f"(target {FLAT_TOOLS} tools / {FLAT_TOKENS:,} tokens)",
            )


def check_live(inv: Inventory) -> Iterator[Finding]:
    """Rules only a live endpoint can show: cache hints on a stateless tools/list."""
    for entry in inv.live:
        if entry.get("mode") != "stateless":
            continue
        cache = entry.get("cache") or {}
        missing = [k for k in ("ttlMs", "cacheScope") if cache.get(k) is None]
        if missing:
            yield finding("CHG-11", f"{entry['url']}: tools/list result has no {' or '.join(missing)}")


def run_checks(inv: Inventory) -> list[Finding]:
    out: list[Finding] = []
    for tool in inv.tools:
        out.extend(check_tool(inv, tool))
    for group in inv.groups.values():
        out.extend(check_group(inv, group))
    out.extend(check_view(inv))
    out.extend(check_live(inv))
    return out
