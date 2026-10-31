"""Inventory model and loaders for tools/list files, group documents, and directories."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DEFAULT_META_TOOLS = ("search", "describe", "call", "execute", "resume", "skills")
DEFAULT_SEPARATOR = "_"


class InputError(Exception):
    """Input could not be read or understood."""


@dataclass
class Tool:
    raw: dict[str, Any]
    group: str | None
    name: str  # name inside its group (path or unprefixed name)
    exposed: str  # name a flat client would see
    source: str | None = None  # where the tool comes from, e.g. "catalog"

    @property
    def leaf(self) -> str:
        return self.name.rsplit(".", 1)[-1]

    @property
    def ref(self) -> str:
        return f"{self.group}/{self.name}" if self.group else self.name

    @property
    def description(self) -> str:
        value = self.raw.get("description")
        return value if isinstance(value, str) else ""

    @property
    def annotations(self) -> dict[str, Any]:
        value = self.raw.get("annotations")
        return value if isinstance(value, dict) else {}

    @property
    def input_schema(self) -> Any:
        return self.raw.get("inputSchema")

    @property
    def approval(self) -> str | None:
        """Effective approval policy: "required", "none", or None when the input does not say."""
        value = self.raw.get("approval")
        return value if value in ("required", "none") else None

    @property
    def kind(self) -> str | None:
        """The gateway's tool kind, "query" or "mutation", when the input records it.

        Executor admin dumps carry it as `readOnly`. It is the kind, not the approval:
        an app can run a mutation without approval.
        """
        value = self.raw.get("kind")
        if value in ("query", "mutation"):
            return value
        if isinstance(self.raw.get("readOnly"), bool):
            return "query" if self.raw["readOnly"] else "mutation"
        return None

    @property
    def reviewed_read_only(self) -> bool:
        """The gateway's own review classed the tool as a read (ANN-3), e.g. Executor `kinds`."""
        return self.raw.get("kindConfirmed") is True and self.kind == "query"


@dataclass
class Group:
    slug: str
    title: str | None = None
    description: str | None = None
    instructions: str | None = None
    source: str | None = None
    has_metadata: bool = False  # False when the group was inferred from names or files
    instructions_known: bool = True  # False when the input format leaves instructions out (Executor dumps)
    tools: list[Tool] = field(default_factory=list)


@dataclass
class Inventory:
    namespace: str  # "path", "prefix", "file", or "none"
    discovery: str  # "flat", "progressive", or "code"
    tools: list[Tool] = field(default_factory=list)
    groups: dict[str, Group] = field(default_factory=dict)
    meta_tools: tuple[str, ...] = DEFAULT_META_TOOLS
    separator: str = DEFAULT_SEPARATOR
    skipped: list[str] = field(default_factory=list)
    live: list[dict[str, Any]] = field(default_factory=list)  # one entry per live URL: protocol, mode, cache

    def add(self, tool: Tool) -> None:
        self.tools.append(tool)
        if tool.group is not None:
            group = self.groups.setdefault(tool.group, Group(slug=tool.group))
            group.tools.append(tool)

    def is_meta(self, tool: Tool) -> bool:
        # In a flat view, a tool named search or execute is an ordinary tool.
        return self.discovery != "flat" and tool.group is None and tool.name in self.meta_tools


def extract_tools(doc: Any) -> list[dict[str, Any]] | None:
    """Return the tool list from a tools/list result, JSON-RPC response, or bare list."""
    if isinstance(doc, list):
        # A bare list counts only if every item looks like a tool definition.
        looks_like_tool = all(
            isinstance(t, dict) and "name" in t and ({"inputSchema", "description", "annotations"} & t.keys())
            for t in doc
        )
        return doc if doc and looks_like_tool else None
    if not isinstance(doc, dict):
        return None
    if "result" in doc and isinstance(doc["result"], dict):
        doc = doc["result"]
    tools = doc.get("tools")
    if isinstance(tools, list) and all(isinstance(t, dict) for t in tools):
        return tools
    return None


def group_metadata(doc: Any) -> Group | None:
    """Read group metadata from a group document.

    Two shapes are accepted:
    - spec-native: {"group": {"slug", "title", "description", "instructions"}, "tools": [...]}
    - Executor app dump: {"slug", "name", "source", "routers": [{"path": "", ...}], "tools": [...]}
    """
    if not isinstance(doc, dict) or not isinstance(doc.get("tools"), list):
        return None
    if isinstance(doc.get("group"), dict) and isinstance(doc["group"].get("slug"), str):
        g = doc["group"]
        return Group(
            slug=g["slug"],
            title=g.get("title"),
            description=g.get("description"),
            instructions=g.get("instructions"),
            source=g.get("source"),
            has_metadata=True,
        )
    if isinstance(doc.get("slug"), str):
        root = next(
            (r for r in doc.get("routers", []) if isinstance(r, dict) and r.get("path") == ""),
            {},
        )
        return Group(
            slug=doc["slug"],
            title=root.get("title") or doc.get("name"),
            description=root.get("description"),
            instructions=doc.get("instructions"),
            source=doc.get("source"),
            has_metadata=True,
            instructions_known="instructions" in doc,
        )
    return None


def _tool_name(raw: dict[str, Any], where: str) -> str:
    name = raw.get("name")
    if not isinstance(name, str):
        raise InputError(f"{where}: tool without a string name")
    return name


def build_inventory(
    docs: list[tuple[str, Any]],
    namespace: str = "auto",
    separator: str = DEFAULT_SEPARATOR,
    meta_tools: tuple[str, ...] = DEFAULT_META_TOOLS,
    discovery: str = "auto",
) -> Inventory:
    """Build one inventory (one view) from parsed documents.

    `docs` holds (label, parsed JSON) pairs. The label is a file stem or URL and
    names the group in "file" mode.
    """
    parsed: list[tuple[str, Group | None, list[dict[str, Any]]]] = []
    skipped: list[str] = []
    for label, doc in docs:
        meta = group_metadata(doc)
        tools = extract_tools(doc)
        if tools is None:
            skipped.append(label)
            continue
        parsed.append((label, meta, tools))
    if not parsed:
        raise InputError("no tools/list data found in the input")

    if namespace == "auto":
        if all(meta is not None for _, meta, _ in parsed):
            namespace = "path"
        elif len(parsed) > 1:
            namespace = "file"
        else:
            namespace = "none"

    inv = Inventory(namespace=namespace, discovery="flat", meta_tools=meta_tools, separator=separator)
    inv.skipped = skipped
    for label, meta, tools in parsed:
        group_slug: str | None = None
        if namespace == "path":
            if meta is None:
                raise InputError(f"{label}: path mode needs group documents (slug + tools)")
            group_slug = meta.slug
            inv.groups.setdefault(group_slug, meta)  # later documents with the same slug add tools
        elif namespace == "file":
            group_slug = label
            inv.groups.setdefault(label, Group(slug=label))
        for raw in tools:
            name = _tool_name(raw, label)
            source = raw.get("source") or (meta.source if meta else None)
            if namespace in ("path", "file"):
                flat = name.replace(".", separator)
                tool = Tool(raw, group_slug, name, f"{group_slug}{separator}{flat}", source)
            elif namespace == "prefix" and separator in name:
                prefix, rest = name.split(separator, 1)
                inv.groups.setdefault(prefix, Group(slug=prefix))
                tool = Tool(raw, prefix, rest, name, source)
            else:
                tool = Tool(raw, None, name, name, source)
            inv.add(tool)

    if discovery == "auto":
        if namespace == "path":
            discovery = "progressive"
        else:
            top = {t.name for t in inv.tools if t.group is None}
            discovery = "progressive" if len(top & {"search", "describe", "call", "execute"}) >= 2 else "flat"
    inv.discovery = discovery
    return inv


def load_path(path: Path) -> list[tuple[str, Any]]:
    """Load one JSON file, or every *.json file under a directory, sorted by path."""
    if path.is_dir():
        files = sorted(p for p in path.rglob("*.json") if p.is_file())
        if not files:
            raise InputError(f"{path}: no .json files")
    elif path.is_file():
        files = [path]
    else:
        raise InputError(f"{path}: not found")
    stems = [f.stem for f in files]
    docs = []
    for f in files:
        label = f.stem
        if stems.count(label) > 1:
            # a/tools.json and b/tools.json are different groups.
            label = "-".join(f.relative_to(path).with_suffix("").parts)
        try:
            docs.append((label, json.loads(f.read_text(encoding="utf-8"))))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise InputError(f"{f}: {exc}") from exc
    return docs
