"""Fetch tools/list from a live streamable-HTTP MCP endpoint.

The bearer token comes from an environment variable, never from argv.
"""

from __future__ import annotations

import contextlib
import json
import os
import urllib.error
import urllib.request
from typing import Any

from . import __version__
from .model import InputError
from .rules import STATELESS

HANDSHAKE_PROTOCOL = "2025-11-25"
CLIENT_INFO = {"name": "mcp-gateway-check", "version": __version__}
_META = "io.modelcontextprotocol/"


class _Client:
    def __init__(self, url: str, headers: dict[str, str], timeout: float, protocol: str) -> None:
        self.url = url
        self.headers = headers
        self.timeout = timeout
        self.session: str | None = None
        self.protocol = protocol
        self.stateless = protocol >= STATELESS
        self.next_id = 1

    def post(self, method: str, params: dict[str, Any] | None = None, notify: bool = False) -> Any:
        body: dict[str, Any] = {"jsonrpc": "2.0", "method": method}
        if self.stateless:
            # 2026-07-28: no session; each request carries protocol, capabilities, and client in _meta.
            params = dict(params or {})
            params["_meta"] = {
                f"{_META}protocolVersion": self.protocol,
                f"{_META}clientCapabilities": {},
                f"{_META}clientInfo": CLIENT_INFO,
            }
        if params is not None:
            body["params"] = params
        msg_id = None
        if not notify:
            msg_id = self.next_id
            self.next_id += 1
            body["id"] = msg_id
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "MCP-Protocol-Version": self.protocol,
            **self.headers,
        }
        if self.stateless:
            headers["Mcp-Method"] = method
        if self.session:
            headers["Mcp-Session-Id"] = self.session
        req = urllib.request.Request(self.url, data=json.dumps(body).encode(), headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                self.session = resp.headers.get("Mcp-Session-Id") or self.session
                ctype = resp.headers.get("Content-Type", "")
                text = resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            raise _RpcError(f"HTTP {exc.code} for {method}", http=exc.code) from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise InputError(f"{self.url}: {exc}") from exc
        if notify:
            return None
        for message in _messages(text, ctype):
            if message.get("id") == msg_id:
                if "error" in message:
                    err = message["error"]
                    raise _RpcError(f"{method}: {err.get('message', err)}")
                return message.get("result")
        raise InputError(f"{self.url}: no response to {method}")


class _RpcError(Exception):
    def __init__(self, message: str, http: int | None = None) -> None:
        super().__init__(message)
        self.http = http


def _messages(text: str, ctype: str) -> list[dict[str, Any]]:
    """Parse a JSON body or a text/event-stream body into JSON-RPC messages."""
    if "text/event-stream" in ctype:
        out, data = [], []
        for line in text.splitlines() + [""]:
            if line.startswith("data:"):
                data.append(line[5:].lstrip())
            elif line == "" and data:
                with contextlib.suppress(json.JSONDecodeError):
                    out.append(json.loads("\n".join(data)))
                data = []
        return [m for m in out if isinstance(m, dict)]
    try:
        doc = json.loads(text)
    except json.JSONDecodeError as exc:
        raise InputError(f"invalid JSON from server: {exc}") from exc
    if isinstance(doc, list):
        return [m for m in doc if isinstance(m, dict)]
    return [doc] if isinstance(doc, dict) else []


def _list_all(client: _Client) -> dict[str, Any]:
    """All pages of tools/list, plus what the first page said about caching."""
    tools: list[dict[str, Any]] = []
    cache: dict[str, Any] = {}
    cursor = None
    for page in range(1000):
        result = client.post("tools/list", {"cursor": cursor} if cursor else {})
        if not isinstance(result, dict) or not isinstance(result.get("tools"), list):
            raise InputError("tools/list returned no tools array")
        if page == 0:
            cache = {k: result.get(k) for k in ("ttlMs", "cacheScope")}
        tools.extend(result["tools"])
        cursor = result.get("nextCursor")
        if not cursor:
            mode = "stateless" if client.stateless else "session"
            return {"tools": tools, "live": {"protocol": client.protocol, "mode": mode, "cache": cache}}
    raise InputError("tools/list pagination did not end after 1000 pages")


def fetch_tools(
    url: str,
    token_env: str = "MCP_TOKEN",
    header_envs: dict[str, str] | None = None,
    timeout: float = 30.0,
    protocol: str = STATELESS,
) -> dict[str, Any]:
    """Return {"tools": [...], "live": {...}} from a live endpoint.

    For 2026-07-28 and later, tries a stateless tools/list first. If the
    server refuses, or for earlier revisions, it uses the initialize handshake.
    "live" records the protocol and mode used and the first page's cache fields.
    """
    headers: dict[str, str] = {}
    token = os.environ.get(token_env)
    if token:
        headers["Authorization"] = f"Bearer {token}"
    for header, env in (header_envs or {}).items():
        value = os.environ.get(env)
        if value is None:
            raise InputError(f"environment variable {env} for header {header} is not set")
        headers[header] = value
    client = _Client(url, headers, timeout, protocol)
    if client.stateless:
        try:
            return _list_all(client)
        except _RpcError as first:
            if first.http in (401, 403):
                raise InputError(f"{url}: {first} (set ${token_env} to a bearer token)") from first
        client = _Client(url, headers, timeout, min(protocol, HANDSHAKE_PROTOCOL))
    try:
        init = client.post(
            "initialize",
            {"protocolVersion": client.protocol, "capabilities": {}, "clientInfo": CLIENT_INFO},
        )
        if isinstance(init, dict) and isinstance(init.get("protocolVersion"), str):
            client.protocol = init["protocolVersion"]
        client.post("notifications/initialized", notify=True)
        return _list_all(client)
    except _RpcError as exc:
        if exc.http in (401, 403):
            raise InputError(f"{url}: {exc} (set ${token_env} to a bearer token)") from exc
        raise InputError(f"{url}: {exc}") from exc
