"""Command line: mcp-gateway-check [check|diff|rules] ..."""

from __future__ import annotations

import argparse
import datetime as dt
import os
import sys
import tomllib
from pathlib import Path
from typing import Any

from . import __version__
from .checks import Finding, run_checks
from .diff import diff_change, diff_sync
from .live import fetch_tools
from .model import DEFAULT_META_TOOLS, DEFAULT_SEPARATOR, InputError, Inventory, build_inventory, load_path
from .report import to_json, to_text
from .revisions import TARGET, load
from .rules import RULES
from .waivers import apply_waivers, load_waivers

EXIT_OK, EXIT_FINDINGS, EXIT_INPUT = 0, 1, 2


def _add_revision_arg(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--mcp-revision",
        default=TARGET,
        metavar="REV",
        help="MCP revision to check against: a dated revision, 'draft', or 'target' (default: target, "
        "from upstream.json)",
    )


def _add_input_args(p: argparse.ArgumentParser) -> None:
    _add_revision_arg(p)
    p.add_argument(
        "--namespace",
        choices=("auto", "path", "prefix", "file", "none"),
        default="auto",
        help="how tools map to groups (default: auto)",
    )
    p.add_argument(
        "--separator",
        default=DEFAULT_SEPARATOR,
        help=f"gateway prefix separator for --namespace prefix (default: {DEFAULT_SEPARATOR!r})",
    )
    p.add_argument(
        "--discovery",
        choices=("auto", "flat", "progressive", "code"),
        default="auto",
        help="how the view is served to clients (default: auto)",
    )
    p.add_argument("--meta-tools", default=",".join(DEFAULT_META_TOOLS), help="comma-separated meta-tool names")
    p.add_argument(
        "--token-env",
        default="MCP_TOKEN",
        help="environment variable that holds the bearer token for URLs (default: MCP_TOKEN)",
    )
    p.add_argument(
        "--header-env",
        action="append",
        default=[],
        metavar="HEADER=ENVVAR",
        help="send HEADER with the value of ENVVAR (repeatable)",
    )


def _add_output_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--format", choices=("text", "json"), default="text")
    p.add_argument("--waivers", type=Path, help="TOML waiver file")
    p.add_argument(
        "--fail-on",
        choices=("error", "warning"),
        default="error",
        help="lowest unwaived severity that exits 1 (default: error)",
    )
    p.add_argument("--all", action="store_true", help="show every finding in text output")
    p.add_argument("--today", type=dt.date.fromisoformat, default=None, help=argparse.SUPPRESS)


def build_parser() -> argparse.ArgumentParser:
    # allow_abbrev=False: "--token" must not silently match "--token-env".
    parser = argparse.ArgumentParser(
        prog="mcp-gateway-check",
        allow_abbrev=False,
        description="Check MCP gateway tool surfaces against mcp-gateway-spec.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command")
    kw = {"allow_abbrev": False}

    check = sub.add_parser("check", **kw, help="check a tools/list file, a directory, or a live URL")
    check.add_argument("inputs", nargs="+", help="JSON file, directory of JSON files, or http(s) URL")
    _add_input_args(check)
    _add_output_args(check)

    diff = sub.add_parser("diff", **kw, help="compare two snapshots (change review or edge sync)")
    diff.add_argument("old", help="baseline or upstream snapshot")
    diff.add_argument("new", help="candidate or edge snapshot")
    diff.add_argument("--mode", choices=("change", "sync"), default="change")
    diff.add_argument("--aliases", type=Path, help='TOML file with an [aliases] table: old = "new"')
    diff.add_argument("--strip-prefix", default="", help="edge prefix to remove before matching (sync mode)")
    _add_input_args(diff)
    _add_output_args(diff)

    rules = sub.add_parser("rules", **kw, help="list every rule ID")
    rules.add_argument("--format", choices=("text", "json"), default="text")
    rules.add_argument(
        "--mcp-revision", metavar="REV", help="list only rules that apply to this revision (or 'draft', 'target')"
    )
    return parser


def _load(source: str, args: argparse.Namespace) -> list[tuple[str, Any]]:
    if source.startswith(("http://", "https://")):
        headers = {}
        for item in args.header_env:
            header, sep, env = item.partition("=")
            if not sep:
                raise InputError(f"--header-env {item!r}: use HEADER=ENVVAR")
            headers[header] = env
        doc = fetch_tools(source, args.token_env, headers, protocol=load().protocol(args.mcp_revision))
        doc["live"]["url"] = source
        return [(source, doc)]
    return load_path(Path(source))


def _inventory(sources: list[str], args: argparse.Namespace) -> Inventory:
    docs: list[tuple[str, Any]] = []
    for source in sources:
        docs.extend(_load(source, args))
    meta = tuple(m.strip() for m in args.meta_tools.split(",") if m.strip())
    inv = build_inventory(docs, args.namespace, args.separator, meta, args.discovery)
    inv.live = [doc["live"] for _, doc in docs if isinstance(doc, dict) and isinstance(doc.get("live"), dict)]
    return inv


def _finish(inv: Inventory | None, findings: list[Finding], args: argparse.Namespace) -> int:
    today = args.today or dt.date.today()
    revision = args.mcp_revision
    # Rules outside the revision's window are skipped, before waivers, so a waiver
    # for a skipped rule is not reported as unused.
    skipped = [r.id for r in RULES.values() if not r.applies_to(revision)]
    findings = [f for f in findings if f.rule not in skipped]
    if args.waivers:
        findings = apply_waivers(findings, load_waivers(args.waivers, today), today)
    if args.format == "json":
        print(to_json(inv, findings, revision, skipped))
    else:
        color = sys.stdout.isatty() and "NO_COLOR" not in os.environ
        print(to_text(inv, findings, revision, skipped, limit=0 if args.all else 5, color=color))
    failing = {"error"} if args.fail_on == "error" else {"error", "warning"}
    return EXIT_FINDINGS if any(f.severity in failing and not f.waived for f in findings) else EXIT_OK


def _aliases(path: Path | None) -> dict[str, str]:
    if path is None:
        return {}
    try:
        doc = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise InputError(f"{path}: {exc}") from exc
    table = doc.get("aliases", {})
    if not isinstance(table, dict) or not all(isinstance(v, str) for v in table.values()):
        raise InputError(f"{path}: [aliases] must map old names to new names")
    return table


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    # `mcp-gateway-check tools.json` is shorthand for `check tools.json`.
    if argv and argv[0] not in ("check", "diff", "rules") and not argv[0].startswith("-"):
        argv.insert(0, "check")
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if getattr(args, "mcp_revision", None):
            args.mcp_revision = load().resolve(args.mcp_revision)
        if args.command == "rules":
            listed = [r for r in RULES.values() if not args.mcp_revision or r.applies_to(args.mcp_revision)]
            if args.format == "json":
                import json

                print(json.dumps([r.as_dict() for r in listed], indent=2))
            else:
                for r in listed:
                    window = f"{r.since}..{r.until or ''}"
                    print(f"{r.id:<10} {r.level:<10} {'checked' if r.checked else 'manual ':<8} {window:<23} {r.title}")
            return EXIT_OK
        if args.command == "check":
            inv = _inventory(args.inputs, args)
            return _finish(inv, run_checks(inv), args)
        if args.command == "diff":
            old = _inventory([args.old], args)
            new = _inventory([args.new], args)
            if args.mode == "sync":
                findings = diff_sync(old, new, args.strip_prefix)
            else:
                findings = diff_change(old, new, _aliases(args.aliases))
            return _finish(None, findings, args)
        parser.print_help()
        return EXIT_INPUT
    except InputError as exc:
        print(f"mcp-gateway-check: {exc}", file=sys.stderr)
        return EXIT_INPUT
