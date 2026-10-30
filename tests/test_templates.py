"""The template examples must pass the checker and match the spec version."""

import json
import re
import tempfile
import tomllib
import unittest
from pathlib import Path

from mcp_gateway_check import SPEC_VERSION
from test_checker import ROOT, run_json

TEMPLATES = ROOT / "templates"


def json_block(name: str) -> dict:
    text = (TEMPLATES / name).read_text(encoding="utf-8")
    return json.loads(re.search(r"```json\n(.*?)\n```", text, re.S).group(1))


class Templates(unittest.TestCase):
    def test_tool_and_group_examples_pass(self):
        doc = json_block("group.md")
        doc["tools"] = [json_block("tool-description.md")]
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "tracker.json").write_text(json.dumps(doc), encoding="utf-8")
            code, report = run_json("check", tmp, "--namespace", "path")
        self.assertEqual(code, 0, report)
        self.assertEqual(report["findings"], [])

    def test_view_template_parses(self):
        doc = tomllib.loads((TEMPLATES / "view.toml").read_text(encoding="utf-8"))
        self.assertEqual(doc["spec_version"], SPEC_VERSION)
        for view in doc["view"]:
            self.assertLessEqual(len(view.get("pinned", [])), 5, view["name"])


if __name__ == "__main__":
    unittest.main()
