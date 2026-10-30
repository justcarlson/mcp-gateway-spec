"""Regression tests for inputs the first checker release got wrong."""

import json
import tempfile
import unittest
from pathlib import Path

from mcp_gateway_check.checks import run_checks
from mcp_gateway_check.diff import schema_breaks
from mcp_gateway_check.model import build_inventory
from test_checker import TODAY, rules_of, run, run_json, tool, write_json


class Schemas(unittest.TestCase):
    def test_new_type_on_untyped_property_is_a_break(self):
        old = {"type": "object", "properties": {"q": {}}}
        new = {"type": "object", "properties": {"q": {"type": "integer"}}}
        self.assertEqual(list(schema_breaks(old, new)), ["input.q: new type restriction ['integer']"])

    def test_property_named_definitions_is_not_ref_usage(self):
        schema = {"type": "object", "properties": {"definitions": {"type": "string", "description": "Words."}}}
        inv = build_inventory([("t", {"tools": [tool("get_word", inputSchema=schema)]})])
        self.assertNotIn("SCHEMA-5", {f.rule for f in run_checks(inv)})


class Grouping(unittest.TestCase):
    def test_same_slug_in_two_documents_keeps_all_tools(self):
        docs = [
            (f"n{i}", {"group": {"slug": "notes", "description": "Notes."}, "tools": [tool(f"get_n{i}")]})
            for i in range(2)
        ]
        inv = build_inventory(docs)
        self.assertEqual(len(inv.groups["notes"].tools), 2)

    def test_same_file_name_in_two_directories_is_two_groups(self):
        with tempfile.TemporaryDirectory() as tmp:
            for sub in ("a", "b"):
                (Path(tmp) / sub).mkdir()
                write_json(Path(tmp) / sub, "tools.json", {"tools": [tool(f"get_{sub}")]})
            _, doc = run_json("check", tmp, "--namespace", "file")
        self.assertEqual(doc["inventory"]["groups"], 2)

    def test_flat_tool_named_execute_is_an_ordinary_tool(self):
        inv = build_inventory([("t", {"tools": [tool("execute"), tool("get_a")]})])
        self.assertEqual(inv.discovery, "flat")
        self.assertFalse(inv.is_meta(inv.tools[0]))


class Waivers(unittest.TestCase):
    def waive(self, body: str, *extra: str):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "w.toml"
            path.write_text(body, encoding="utf-8")
            good = str(Path(__file__).parent / "fixtures" / "good" / "executor-app.json")
            return run("check", good, "--waivers", str(path), "--today", TODAY, *extra)

    def test_waiver_for_rule_outside_revision_is_not_unused(self):
        body = 'rule = "CHG-11"\ntarget = "*"\nreason = "r"\nowner = "o"\nexpires = 2026-12-01\n'
        code, out, _ = self.waive("[[waiver]]\n" + body, "--mcp-revision", "2025-11-25", "--format", "json")
        self.assertNotIn("CONF-3", rules_of(json.loads(out)))
        self.assertEqual(code, 0)

    def test_wrong_field_type_is_an_input_error(self):
        body = '[[waiver]]\nrule = "NAME-1"\ntarget = "*"\nreason = 5\nowner = "o"\nexpires = 2026-12-01\n'
        code, _, err = self.waive(body)
        self.assertEqual(code, 2)
        self.assertIn("reason must be a string", err)


class Diff(unittest.TestCase):
    def test_path_snapshot_against_flat_snapshot_matches_by_exposed_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_dir = Path(tmp) / "old"
            old_dir.mkdir()
            write_json(old_dir, "notes.json", {"group": {"slug": "notes"}, "tools": [tool("get_note")]})
            new = write_json(Path(tmp), "new.json", {"tools": [tool("notes_get_note")]})
            code, doc = run_json("diff", str(old_dir), str(new))
        self.assertNotIn("CHG-1", rules_of(doc), doc)
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
