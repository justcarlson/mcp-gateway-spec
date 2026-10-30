"""Regressions found on a live 38-app Executor deployment and a Cloudflare portal edge in front of it."""

import tempfile
import unittest
from pathlib import Path

from mcp_gateway_check.checks import run_checks
from mcp_gateway_check.model import build_inventory
from test_checker import TODAY, rules_of, run, run_json, tool, write_json

BOTH = {"readOnlyHint": True, "destructiveHint": True, "idempotentHint": True, "openWorldHint": False}
WRITE = {"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False, "openWorldHint": False}


def app(*tools: dict, instructions: str | None = None) -> dict:
    doc = {"slug": "home", "name": "Home", "source": "authored", "tools": list(tools)}
    doc["routers"] = [{"path": "", "title": "Home", "description": "Smart home device state and control."}]
    if instructions is not None:
        doc["instructions"] = instructions
    return doc


def check(doc: dict, *extra: str) -> tuple[int, dict]:
    with tempfile.TemporaryDirectory() as tmp:
        return run_json("check", str(write_json(Path(tmp), "home.json", doc)), *extra)


class Approval(unittest.TestCase):
    def test_readonly_is_the_kind_not_the_approval(self):
        inv = build_inventory([("home", app(tool("set_light", readOnly=False, annotations=WRITE)))])
        t = inv.tools[0]
        self.assertEqual(t.kind, "mutation")
        self.assertIsNone(t.approval)

    def test_never_mutation_fails_ann4(self):
        code, doc = check(app(tool("set_light", readOnly=False, approval="none", annotations=WRITE)))
        self.assertEqual(code, 1)
        ann4 = [f for f in doc["findings"] if f["rule"] == "ANN-4"]
        self.assertEqual(len(ann4), 1)
        self.assertIn("mutation", ann4[0]["message"])
        self.assertEqual(ann4[0]["severity"], "error")

    def test_missing_approval_is_unknown_not_required(self):
        _, doc = check(app(tool("set_light", readOnly=False, annotations=WRITE), instructions="Use it."))
        self.assertNotIn("ANN-4", rules_of(doc))
        self.assertEqual(doc["not_checked"][0]["rules"], ["ANN-4"])
        self.assertEqual(doc["not_checked"][0]["count"], 1)


class ReviewedKind(unittest.TestCase):
    def reviewed(self, **extra):
        return tool("get_live_context", readOnly=True, approval="none", annotations=BOTH, **extra)

    def test_kind_confirmed_query_is_reviewed(self):
        code, doc = check(app(self.reviewed(kindConfirmed=True)))
        ann = [f for f in doc["findings"] if f["rule"].startswith("ANN")]
        self.assertEqual([(f["rule"], f["severity"]) for f in ann], [("ANN-2", "info")])
        self.assertTrue(doc["conformance"]["level1"])
        self.assertEqual(code, 0)

    def test_unreviewed_hint_conflict_still_fails(self):
        code, doc = check(app(self.reviewed()))
        self.assertIn("ANN-2", rules_of(doc))
        self.assertIn("ANN-4", rules_of(doc))
        self.assertEqual(code, 1)


class Instructions(unittest.TestCase):
    def test_empty_instructions_are_not_checked(self):
        doc = app(tool("get_state", approval="none"))
        _, out = check(doc)
        self.assertIn(
            {"rules": ["DESC-11", "DESC-12"], "count": 1, "of": "groups", "reason": "no instruction text"},
            out["not_checked"],
        )
        with tempfile.TemporaryDirectory() as tmp:
            _, text, _ = run("check", str(write_json(Path(tmp), "home.json", doc)))
        self.assertIn("not checked: DESC-11, DESC-12 for 1 groups (no instruction text); not a pass", text)
        self.assertIn("some checked rules had no data", text)

    def test_instructions_present_are_checked(self):
        _, out = check(app(tool("get_state", approval="none"), instructions="Call get_state first."))
        self.assertEqual(out["not_checked"], [])


class PortalEdge(unittest.TestCase):
    def test_gateway_passthrough_group_skips_name8(self):
        names = ["gateway_search", "gateway_describe", "gateway_call", "adapters_search", "adapters_get_status"]
        inv = build_inventory([("portal", {"tools": [tool(n) for n in names]})], namespace="prefix")
        flagged = sorted(f.tool for f in run_checks(inv) if f.rule == "NAME-8")
        self.assertEqual(flagged, ["search"])
        self.assertEqual([f.group for f in run_checks(inv) if f.rule == "NAME-8"], ["adapters"])


class DiffWaivers(unittest.TestCase):
    def test_sync_ignores_waivers_for_rules_it_does_not_evaluate(self):
        body = (
            '[[waiver]]\nrule = "NAME-4"\ntarget = "*"\nreason = "edge uses domain_verb names"\n'
            'owner = "edge"\nexpires = 2026-12-01\n'
            '[[waiver]]\nrule = "EDGE-3"\ntarget = "nothing"\nreason = "r"\nowner = "o"\nexpires = 2026-12-01\n'
        )
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            up = write_json(d, "up.json", {"tools": [tool("get_a")]})
            (d / "w.toml").write_text(body, encoding="utf-8")
            _, doc = run_json(
                "diff", str(up), str(up), "--mode", "sync", "--waivers", str(d / "w.toml"), "--today", TODAY
            )
        conf3 = [f["message"] for f in doc["findings"] if f["rule"] == "CONF-3"]
        self.assertEqual(len(conf3), 1, conf3)
        self.assertIn("EDGE-3", conf3[0])


if __name__ == "__main__":
    unittest.main()
