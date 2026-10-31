import contextlib
import io
import json
import os
import re
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from mcp_gateway_check.checks import run_checks, words
from mcp_gateway_check.cli import main
from mcp_gateway_check.model import build_inventory
from mcp_gateway_check.rules import RULES

ROOT = Path(__file__).resolve().parent.parent
FIX = ROOT / "tests" / "fixtures"
TODAY = "2026-10-30"


def run(*argv: str) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(list(argv))
    return code, out.getvalue(), err.getvalue()


def run_json(*argv: str) -> tuple[int, dict]:
    code, out, _ = run(*argv, "--format", "json")
    return code, json.loads(out)


def rules_of(doc: dict) -> set[str]:
    return {f["rule"] for f in doc["findings"] if not f.get("waived")}


def tool(name: str, **extra) -> dict:
    base = {
        "name": name,
        "title": name.replace("_", " ").title(),
        "description": "Get a thing from the test service and return it with its ID, name, and status fields.",
        "inputSchema": {"type": "object", "additionalProperties": False},
        "annotations": {"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
    }
    base.update(extra)
    return base


def write_json(directory: Path, name: str, doc) -> Path:
    path = directory / name
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


class FixtureManifest(unittest.TestCase):
    def test_each_fixture_yields_exactly_the_expected_rules(self):
        manifest = json.loads((FIX / "manifest.json").read_text())
        for case in manifest["cases"]:
            with self.subTest(case["input"]):
                code, doc = run_json("check", str(FIX / case["input"]), *case["args"])
                self.assertEqual(code, case["exit"])
                self.assertEqual(sorted(rules_of(doc)), case["rules"])

    def test_good_fixtures_have_no_findings(self):
        manifest = json.loads((FIX / "manifest.json").read_text())
        for case in manifest["cases"]:
            if case["input"].startswith("good/"):
                _, doc = run_json("check", str(FIX / case["input"]), *case["args"])
                self.assertEqual(doc["findings"], [], case["input"])
                self.assertTrue(doc["conformance"]["level2"])


class Naming(unittest.TestCase):
    def test_words_split_every_style(self):
        self.assertEqual(words("cmd_album_addPhotos"), ["cmd", "album", "add", "photos"])
        self.assertEqual(words("resolve-library-id"), ["resolve", "library", "id"])
        self.assertEqual(
            words("api.users.gmailUsersDraftsCreate"), ["api", "users", "gmail", "users", "drafts", "create"]
        )
        self.assertEqual(words("HTTPRouters"), ["http", "routers"])

    def test_prefix_mode_splits_on_first_separator(self):
        inv = build_inventory([("x", {"tools": [tool("tracker_get_issue")]})], namespace="prefix")
        self.assertEqual(inv.tools[0].group, "tracker")
        self.assertEqual(inv.tools[0].name, "get_issue")

    def test_slug_repeated_in_name(self):
        doc = {"group": {"slug": "pihole", "description": "DNS blocking."}, "tools": [tool("pi_hole_get_stats")]}
        inv = build_inventory([("x", doc)])
        self.assertIn("NAME-7", {f.rule for f in run_checks(inv)})

    def test_path_mode_exposed_name_includes_slug(self):
        doc = {"group": {"slug": "docs", "description": "Docs."}, "tools": [tool("a" * 60)]}
        inv = build_inventory([("x", doc)])
        self.assertEqual(inv.tools[0].exposed, "docs_" + "a" * 60)
        self.assertIn("NAME-5", {f.rule for f in run_checks(inv)})

    def test_upstream_version_prefix(self):
        flagged = ["v1_twitter_tweet", "v2beta_get_user", "v1alpha2_list_items", "api.v1.list_users", "v3GetUser"]
        clean = ["get_v1_config", "vault_get_secret", "v_get_item", "verify_token", "get_issue"]
        for name, expected in [(n, True) for n in flagged] + [(n, False) for n in clean]:
            with self.subTest(name):
                inv = build_inventory([("x", {"tools": [tool(name)]})], namespace="none")
                self.assertEqual("NAME-11" in {f.rule for f in run_checks(inv)}, expected)

    def test_version_prefix_is_not_also_a_noun_first_name(self):
        inv = build_inventory([("x", {"tools": [tool("v1_get_tweet")]})], namespace="none")
        self.assertEqual({f.rule for f in run_checks(inv)}, {"NAME-11"})


class Discovery(unittest.TestCase):
    def test_flat_thresholds(self):
        with tempfile.TemporaryDirectory() as d:
            twelve = write_json(Path(d), "twelve.json", {"tools": [tool(f"get_item_{i}") for i in range(12)]})
            sixty = write_json(Path(d), "sixty.json", {"tools": [tool(f"get_item_{i}") for i in range(60)]})
            self.assertIn("DISC-1", rules_of(run_json("check", str(twelve))[1]))
            code, doc = run_json("check", str(sixty))
            self.assertIn("DISC-2", rules_of(doc))
            self.assertEqual(code, 1)
            # The same tools behind meta-tools are not a flat view.
            code, doc = run_json("check", str(sixty), "--discovery", "progressive")
            self.assertNotIn("DISC-2", rules_of(doc))

    def test_meta_tools_switch_to_progressive(self):
        tools = [tool(n) for n in ("search", "describe", "call", "execute")]
        inv = build_inventory([("x", {"tools": tools})])
        self.assertEqual(inv.discovery, "progressive")
        self.assertNotIn("NAME-8", {f.rule for f in run_checks(inv)})

    def test_group_size(self):
        doc = {
            "group": {"slug": "big", "description": "Big group."},
            "tools": [tool(f"get_item_{i}") for i in range(11)],
        }
        self.assertIn("GRP-4", {f.rule for f in run_checks(build_inventory([("x", doc)]))})


class Hazards(unittest.TestCase):
    def test_secret_in_description_is_an_error(self):
        fake = "gh" + "p_" + "A1b2C3d4" * 5  # assembled so secret scanners skip the source
        inv = build_inventory([("x", {"tools": [tool("get_repo", description=f"Get a repo. Token {fake}.")]})])
        found = [f for f in run_checks(inv) if f.rule == "DESC-7"]
        self.assertTrue(any(f.severity == "error" for f in found))

    def test_private_hostname(self):
        inv = build_inventory(
            [("x", {"tools": [tool("get_nas", description="Get NAS status from nas.home.arpa now.")]})]
        )
        self.assertIn("DESC-7", {f.rule for f in run_checks(inv)})


class Waivers(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def waiver(self, body: str) -> Path:
        path = self.dir / "waivers.toml"
        path.write_text(body, encoding="utf-8")
        return path

    def test_waiver_clears_error_and_exit(self):
        path = self.waiver(
            '[[waiver]]\nrule = "GRP-2"\ntarget = "web-crawl"\nreason = "Slug owned upstream."\n'
            'owner = "gateway-team"\nexpires = 2027-01-31\n'
            '[[waiver]]\nrule = "DESC-9"\ntarget = "web-crawl"\nreason = "Upstream fix pending."\n'
            'owner = "gateway-team"\nexpires = 2027-01-31\n'
        )
        code, doc = run_json(
            "check", str(FIX / "bad/executor-meta-clash.json"), "--waivers", str(path), "--today", TODAY
        )
        self.assertEqual(code, 0)
        waived = [f for f in doc["findings"] if f.get("waived")]
        self.assertEqual({f["rule"] for f in waived}, {"GRP-2", "DESC-9"})
        self.assertIn("Slug owned upstream.", waived[0]["waiver_reason"] + waived[1]["waiver_reason"])

    def test_glob_targets(self):
        path = self.waiver(
            '[[waiver]]\nrule = "NAME-*"\ntarget = "web-crawl/*"\nreason = "Vendor names."\n'
            'owner = "gateway-team"\nexpires = 2027-01-31\n'
        )
        _, doc = run_json("check", str(FIX / "bad/executor-meta-clash.json"), "--waivers", str(path), "--today", TODAY)
        self.assertFalse({"NAME-7", "NAME-8"} & rules_of(doc))

    def test_expired_waiver_reinstates_finding(self):
        path = self.waiver(
            '[[waiver]]\nrule = "GRP-2"\ntarget = "web-crawl"\nreason = "Old."\nowner = "x"\nexpires = 2026-01-01\n'
        )
        code, doc = run_json(
            "check", str(FIX / "bad/executor-meta-clash.json"), "--waivers", str(path), "--today", TODAY
        )
        self.assertEqual(code, 1)
        self.assertIn("GRP-2", rules_of(doc))
        self.assertIn("CONF-3", rules_of(doc))

    def test_unused_waiver_is_reported(self):
        path = self.waiver(
            '[[waiver]]\nrule = "ANN-2"\ntarget = "nothing"\nreason = "Stale."\nowner = "x"\nexpires = 2027-01-01\n'
        )
        _, doc = run_json("check", str(FIX / "good/executor-app.json"), "--waivers", str(path), "--today", TODAY)
        self.assertEqual(rules_of(doc), {"CONF-3"})

    def test_invalid_waivers_are_input_errors(self):
        head = '[[waiver]]\nrule = "GRP-2"\ntarget = "a"\nowner = "x"\n'
        bad = {
            "no reason": head + "expires = 2027-01-01\n",
            "empty reason": head + 'reason = " "\nexpires = 2027-01-01\n',
            "no expiry": head + 'reason = "r"\n',
            "too far": head + 'reason = "r"\nexpires = 2028-01-01\n',
            "string date": head + 'reason = "r"\nexpires = "soon"\n',
            "unknown rule": head.replace("GRP-2", "NOPE-1") + 'reason = "r"\nexpires = 2027-01-01\n',
        }
        for label, body in bad.items():
            with self.subTest(label):
                code, _, err = run(
                    "check", str(FIX / "good/executor-app.json"), "--waivers", str(self.waiver(body)), "--today", TODAY
                )
                self.assertEqual(code, 2)
                self.assertIn("waiver #1", err)


class Diff(unittest.TestCase):
    def test_change_mode(self):
        code, doc = run_json(
            "diff", str(FIX / "diff/old.json"), str(FIX / "diff/new.json"), "--aliases", str(FIX / "diff/aliases.toml")
        )
        self.assertEqual(code, 1)
        messages = {(f["rule"], f["message"]) for f in doc["findings"]}
        self.assertIn(("CHG-1", "'tracker_list_labels' was removed with no alias"), messages)
        self.assertNotIn("tracker_create_issue", json.dumps([m for r, m in messages if r == "CHG-1"]))
        breaks = sorted(m for r, m in messages if r == "CHG-3")
        self.assertEqual(len(breaks), 3)
        self.assertIn("CHG-9", rules_of(doc))

    def test_change_mode_without_aliases_flags_rename(self):
        _, doc = run_json("diff", str(FIX / "diff/old.json"), str(FIX / "diff/new.json"))
        removed = [f for f in doc["findings"] if f["rule"] == "CHG-1"]
        self.assertEqual(len(removed), 2)

    def test_identical_snapshots_pass(self):
        code, doc = run_json("diff", str(FIX / "diff/old.json"), str(FIX / "diff/old.json"))
        self.assertEqual((code, doc["findings"]), (0, []))

    def test_sync_mode(self):
        code, doc = run_json(
            "diff",
            str(FIX / "diff/upstream.json"),
            str(FIX / "diff/edge.json"),
            "--mode",
            "sync",
            "--strip-prefix",
            "tracker_",
        )
        self.assertEqual(code, 1)
        self.assertEqual([(f["rule"], f["tool"]) for f in doc["findings"]], [("EDGE-3", "tracker_search_issues")])


class Cli(unittest.TestCase):
    def test_shorthand_and_text_output(self):
        code, out, _ = run(str(FIX / "bad/annotations.json"))
        self.assertEqual(code, 1)
        self.assertIn("ANN-4", out)
        self.assertIn("Level 1 FAIL", out)

    def test_fail_on_warning(self):
        path = FIX / "bad/executor-meta-clash.json"
        waivers = Path(tempfile.mkdtemp()) / "w.toml"
        waivers.write_text(
            '[[waiver]]\nrule = "GRP-2"\ntarget = "*"\nreason = "r"\nowner = "x"\nexpires = 2027-01-01\n'
            '[[waiver]]\nrule = "DESC-9"\ntarget = "*"\nreason = "r"\nowner = "x"\nexpires = 2027-01-01\n'
        )
        self.assertEqual(run("check", str(path), "--waivers", str(waivers), "--today", TODAY)[0], 0)
        self.assertEqual(
            run("check", str(path), "--waivers", str(waivers), "--today", TODAY, "--fail-on", "warning")[0], 1
        )

    def test_missing_input(self):
        code, _, err = run("check", "/nonexistent/tools.json")
        self.assertEqual(code, 2)
        self.assertIn("not found", err)

    def test_directory_skips_non_tool_files(self):
        with tempfile.TemporaryDirectory() as d:
            write_json(Path(d), "index.json", [{"slug": "a", "name": "A", "tools": 3}])
            write_json(
                Path(d),
                "a.json",
                {
                    "slug": "weather",
                    "routers": [{"path": "", "description": "Weather."}],
                    "tools": [tool("get_forecast")],
                },
            )
            _, doc = run_json("check", d)
            self.assertEqual(doc["inventory"]["skipped_inputs"], ["index"])
            self.assertEqual(doc["inventory"]["namespace"], "path")

    def test_rules_command_lists_registry(self):
        code, out, _ = run("rules")
        self.assertEqual(code, 0)
        self.assertEqual(len(out.strip().splitlines()), len(RULES))


class Live(unittest.TestCase):
    """A tiny streamable-HTTP server: stateless first, then the initialize fallback."""

    def start(self, stateless: bool, sse: bool, cache: bool = True, junk: bool = False):
        calls = []
        pages = [{"tools": [tool("get_a")], "nextCursor": "p2"}, {"tools": [tool("get_b")]}]
        if cache:
            pages = [{**p, "ttlMs": 60000, "cacheScope": "private"} for p in pages]
        self.requests = []

        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                outer.requests.append((self.headers, body))
                calls.append(
                    (body.get("method"), self.headers.get("Authorization"), self.headers.get("Mcp-Session-Id"))
                )
                if self.headers.get("Authorization") != "Bearer s3cret":
                    self.send_response(401)
                    self.end_headers()
                    return
                method = body.get("method")
                if method == "notifications/initialized":
                    self.send_response(202)
                    self.end_headers()
                    return
                if method == "tools/list" and not stateless and self.headers.get("Mcp-Session-Id") != "sess-1":
                    # junk: answer 200 with a body that is not JSON-RPC
                    self.send_response(200 if junk else 400)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", "5")
                    self.end_headers()
                    self.wfile.write(b"hello")
                    return
                if method == "initialize":
                    result = {
                        "protocolVersion": "2025-11-25",
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": "t", "version": "1"},
                    }
                else:
                    cursor = (body.get("params") or {}).get("cursor")
                    result = pages[1] if cursor == "p2" else pages[0]
                payload = json.dumps({"jsonrpc": "2.0", "id": body["id"], "result": result})
                self.send_response(200)
                if method == "initialize":
                    self.send_header("Mcp-Session-Id", "sess-1")
                if sse:
                    self.send_header("Content-Type", "text/event-stream")
                    data = f"event: message\ndata: {payload}\n\n".encode()
                else:
                    self.send_header("Content-Type", "application/json")
                    data = payload.encode()
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        return f"http://127.0.0.1:{server.server_address[1]}/mcp", calls

    def test_stateless_json_with_pagination(self):
        url, calls = self.start(stateless=True, sse=False)
        os.environ["TEST_MCP_TOKEN"] = "s3cret"
        self.addCleanup(os.environ.pop, "TEST_MCP_TOKEN")
        code, doc = run_json("check", url, "--token-env", "TEST_MCP_TOKEN")
        self.assertEqual(code, 0, doc)
        self.assertEqual(doc["inventory"]["tools"], 2)
        self.assertEqual([c[0] for c in calls], ["tools/list", "tools/list"])

    def test_stateless_request_shape(self):
        url, _ = self.start(stateless=True, sse=False)
        self.token()
        run_json("check", url, "--token-env", "TEST_MCP_TOKEN")
        headers, body = self.requests[0]
        self.assertEqual(headers.get("Mcp-Method"), "tools/list")
        self.assertEqual(headers.get("MCP-Protocol-Version"), "2026-07-28")
        meta = body["params"]["_meta"]
        self.assertEqual(meta["io.modelcontextprotocol/protocolVersion"], "2026-07-28")
        self.assertIn("io.modelcontextprotocol/clientInfo", meta)

    def test_missing_cache_fields_fail_chg11_only_for_stateless(self):
        url, _ = self.start(stateless=True, sse=False, cache=False)
        self.token()
        code, doc = run_json("check", url, "--token-env", "TEST_MCP_TOKEN")
        self.assertEqual(code, 1)
        self.assertEqual(rules_of(doc), {"CHG-11"})
        code, doc = run_json("check", url, "--token-env", "TEST_MCP_TOKEN", "--mcp-revision", "2025-11-25")
        self.assertEqual(code, 0, doc)
        self.assertIn("CHG-11", doc["skipped_rules"])

    def test_older_revision_uses_initialize_directly(self):
        url, calls = self.start(stateless=False, sse=False)
        self.token()
        code, doc = run_json("check", url, "--token-env", "TEST_MCP_TOKEN", "--mcp-revision", "2025-11-25")
        self.assertEqual(code, 0, doc)
        methods = [c[0] for c in calls]
        self.assertEqual(methods, ["initialize", "notifications/initialized", "tools/list", "tools/list"])
        self.assertEqual(doc["inventory"]["live"][0]["mode"], "session")

    def test_two_urls_get_slug_shaped_groups(self):
        url, _ = self.start(stateless=True, sse=False)
        self.token()
        code, doc = run_json("check", url, url, "--token-env", "TEST_MCP_TOKEN")
        self.assertNotIn("GRP-2", rules_of(doc), doc)
        self.assertNotIn("NAME-5", rules_of(doc), doc)

    def test_junk_stateless_answer_falls_back_to_handshake(self):
        url, calls = self.start(stateless=False, sse=False, junk=True)
        self.token()
        code, doc = run_json("check", url, "--token-env", "TEST_MCP_TOKEN")
        self.assertEqual(doc["inventory"]["live"][0]["mode"], "session", doc)
        self.assertIn("initialize", [c[0] for c in calls])

    def test_default_user_agent(self):
        url, _ = self.start(stateless=True, sse=False)
        self.token()
        run_json("check", url, "--token-env", "TEST_MCP_TOKEN")
        self.assertRegex(self.requests[0][0].get("User-Agent"), r"^mcp-gateway-check/\d+\.\d+\.\d+$")

    def test_user_agent_flag_and_header_env_precedence(self):
        url, _ = self.start(stateless=True, sse=False)
        self.token()
        run_json("check", url, "--token-env", "TEST_MCP_TOKEN", "--user-agent", "probe/1")
        self.assertEqual(self.requests[-1][0].get_all("User-Agent"), ["probe/1"])
        os.environ["TEST_UA"] = "edge-check/2"
        self.addCleanup(os.environ.pop, "TEST_UA")
        args = ("--token-env", "TEST_MCP_TOKEN", "--user-agent", "probe/1", "--header-env", "user-agent=TEST_UA")
        run_json("check", url, *args)
        self.assertEqual(self.requests[-1][0].get_all("User-Agent"), ["edge-check/2"])

    def token(self):
        os.environ["TEST_MCP_TOKEN"] = "s3cret"
        self.addCleanup(os.environ.pop, "TEST_MCP_TOKEN")

    def test_initialize_fallback_with_sse(self):
        url, calls = self.start(stateless=False, sse=True)
        os.environ["TEST_MCP_TOKEN"] = "s3cret"
        self.addCleanup(os.environ.pop, "TEST_MCP_TOKEN")
        code, doc = run_json("check", url, "--token-env", "TEST_MCP_TOKEN")
        self.assertEqual(code, 0, doc)
        self.assertEqual(doc["inventory"]["tools"], 2)
        methods = [c[0] for c in calls]
        self.assertEqual(methods, ["tools/list", "initialize", "notifications/initialized", "tools/list", "tools/list"])
        self.assertEqual(calls[-1][2], "sess-1")

    def test_missing_token_is_a_clear_input_error(self):
        url, _ = self.start(stateless=True, sse=False)
        code, _, err = run("check", url, "--token-env", "UNSET_TOKEN_VAR_FOR_TEST")
        self.assertEqual(code, 2)
        self.assertIn("UNSET_TOKEN_VAR_FOR_TEST", err)

    def test_no_token_flag_exists(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            main(["check", "http://127.0.0.1:1/mcp", "--token", "x"])


class SpecConsistency(unittest.TestCase):
    def test_every_rule_has_a_spec_heading_and_back(self):
        spec = (ROOT / "SPEC.md").read_text(encoding="utf-8")
        headings = re.findall(r"^#### ([A-Z]+-\d+)$", spec, re.M)
        self.assertEqual(len(headings), len(set(headings)), "duplicate rule heading")
        self.assertEqual(set(headings), set(RULES))
        for rule_id, rule in RULES.items():
            block = spec.split(f"#### {rule_id}\n", 1)[1].split("\n#### ", 1)[0]
            with self.subTest(rule_id):
                if rule.until is None:
                    window = f"MCP {rule.since}+"
                elif rule.until == rule.since:
                    window = f"MCP {rule.since} only"
                else:
                    window = f"MCP {rule.since} to {rule.until}"
                test = "checked" if rule.checked else "manual"
                self.assertTrue(block.startswith(f"**{rule.level}** · {test} · {window} · "), block[:120])
                self.assertIn("*Why:*", block)
                self.assertRegex(block, r"\*Source:\*.*\[S\d+\]")

    def test_rule_index_matches_registry(self):
        spec = (ROOT / "SPEC.md").read_text(encoding="utf-8")
        index = spec.split("## 17. Rule index", 1)[1].split("\n## ", 1)[0]
        rows = re.findall(
            r"^\| \[([A-Z]+-\d+)\]\(#[a-z]+-\d+\) \| ([A-Z ]+) \| (\w+) \| ([\d-]+) \| ([\d-]*) \| (.+) \|$",
            index,
            re.M,
        )
        expected = [
            (r.id, r.level, "checked" if r.checked else "manual", r.since, r.until or "", r.title)
            for r in RULES.values()
        ]
        self.assertEqual(rows, expected)

    def test_spec_sources_resolve(self):
        spec = (ROOT / "SPEC.md").read_text(encoding="utf-8")
        cited = set(re.findall(r"\[(S\d+)\](?!:)", spec))
        defined = set(re.findall(r"^\[(S\d+)\]: ", spec, re.M))
        self.assertFalse(cited - defined, "cited but undefined")
        self.assertFalse(defined - cited, "defined but unused")


if __name__ == "__main__":
    unittest.main()
