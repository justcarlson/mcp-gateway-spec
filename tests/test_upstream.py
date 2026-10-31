"""MCP revision tracking: rule windows, upstream.json, frozen profiles, and the tracking script."""

import contextlib
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from mcp_gateway_check import revisions
from mcp_gateway_check.model import InputError
from mcp_gateway_check.rules import RULES, STATELESS
from test_checker import FIX, ROOT, run, run_json


def _script(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module  # dataclasses look the module up by name
    spec.loader.exec_module(module)
    return module


conformance = _script("conformance")
check_frozen = _script("check_frozen")
track = _script("track_upstream")
UPSTREAM = json.loads((ROOT / "upstream.json").read_text(encoding="utf-8"))


class Windows(unittest.TestCase):
    def test_applies_is_inclusive_and_draft_is_last(self):
        self.assertTrue(revisions.applies("2025-11-25", None, "2025-11-25"))
        self.assertTrue(revisions.applies("2025-11-25", None, "draft"))
        self.assertFalse(revisions.applies("2026-07-28", None, "2025-11-25"))
        self.assertTrue(revisions.applies("2025-11-25", "2025-11-25", "2025-11-25"))
        self.assertFalse(revisions.applies("2025-11-25", "2025-11-25", "2026-07-28"))
        self.assertFalse(revisions.applies("2025-11-25", "2025-11-25", "draft"))

    def test_stateless_rules_are_skipped_for_older_revision(self):
        code, doc = run_json("check", str(FIX / "good" / "executor-app.json"), "--mcp-revision", "2025-11-25")
        self.assertEqual(code, 0, doc)
        self.assertEqual(doc["mcp_revision"], "2025-11-25")
        expected = sorted(r.id for r in RULES.values() if r.since == STATELESS)
        self.assertEqual(sorted(doc["skipped_rules"]), expected)
        self.assertIn("VIEW-1", doc["skipped_rules"])

    def test_target_is_the_default(self):
        _, doc = run_json("check", str(FIX / "good" / "executor-app.json"))
        self.assertEqual(doc["mcp_revision"], UPSTREAM["mcp"]["target"])
        self.assertEqual(doc["skipped_rules"], ["DISC-11"])
        _, doc = run_json("check", str(FIX / "good" / "executor-app.json"), "--mcp-revision", "target")
        self.assertEqual(doc["mcp_revision"], UPSTREAM["mcp"]["target"])

    def test_draft_is_accepted(self):
        code, doc = run_json("check", str(FIX / "good" / "executor-app.json"), "--mcp-revision", "draft")
        self.assertEqual(code, 0)
        self.assertEqual(doc["mcp_revision"], "draft")

    def test_findings_of_skipped_rules_are_dropped(self):
        # DISC-2 applies everywhere; pretend it is new to see the filter work.
        rule = RULES["DISC-2"]
        object.__setattr__(rule, "since", "2099-01-01")
        self.addCleanup(object.__setattr__, rule, "since", "2025-11-25")
        with tempfile.TemporaryDirectory() as tmp:
            tools = [
                {"name": f"get_t{i}", "description": "x" * 90, "inputSchema": {"type": "object"}} for i in range(60)
            ]
            path = Path(tmp) / "t.json"
            path.write_text(json.dumps({"tools": tools}), encoding="utf-8")
            _, doc = run_json("check", str(path))
        self.assertNotIn("DISC-2", {f["rule"] for f in doc["findings"]})
        self.assertIn("DISC-2", doc["skipped_rules"])

    def test_text_output_reports_skipped_rules(self):
        _, out, _ = run("check", str(FIX / "good" / "executor-app.json"), "--mcp-revision", "2025-11-25")
        self.assertIn("MCP revision 2025-11-25", out)
        self.assertRegex(out, r"skipped \d+ rules outside MCP 2025-11-25: .*DISC-8")

    def test_unknown_revision_is_rejected(self):
        code, _, err = run("check", str(FIX / "good" / "executor-app.json"), "--mcp-revision", "2030-01-01")
        self.assertEqual(code, 2)
        self.assertIn("'2030-01-01' is unknown", err)
        self.assertIn("2026-07-28 (target)", err)

    def test_known_but_unsupported_revision_is_rejected(self):
        up = revisions.parse(json.dumps({"mcp": {**UPSTREAM["mcp"], "supported": ["2026-07-28"]}}))
        with self.assertRaisesRegex(InputError, "does not support"):
            up.resolve("2025-11-25")

    def test_rules_command_filters_by_revision(self):
        _, out, _ = run("rules", "--format", "json", "--mcp-revision", "2025-11-25")
        ids = {r["id"] for r in json.loads(out)}
        self.assertIn("DISC-11", ids)
        self.assertNotIn("DISC-10", ids)


class UpstreamFile(unittest.TestCase):
    def test_target_supported_and_pinned(self):
        mcp = UPSTREAM["mcp"]
        self.assertIn(mcp["target"], mcp["supported"])
        for rev in mcp["supported"]:
            entry = mcp["revisions"][rev]
            self.assertRegex(entry["commit"], r"^[0-9a-f]{40}$")
            self.assertRegex(entry["verified_on"], r"^\d{4}-\d{2}-\d{2}$")

    def test_rule_windows_use_known_revisions(self):
        known = set(UPSTREAM["mcp"]["revisions"])
        for rule in RULES.values():
            self.assertIn(rule.since, known, rule.id)
            if rule.until:
                self.assertIn(rule.until, known, rule.id)

    def test_readme_badge_and_table_match(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        target = UPSTREAM["mcp"]["target"]
        self.assertIn(f"MCP-{target.replace('-', '--')}", readme, "badge must show the upstream.json target")
        row = next(line for line in readme.splitlines() if line.startswith("| 0.1"))
        for rev in UPSTREAM["mcp"]["supported"]:
            self.assertIn(rev, row)
        self.assertIn(f"{target} (target)", row)


class FrozenProfiles(unittest.TestCase):
    def test_profiles_match_registry_for_this_version(self):
        self.assertEqual(conformance.check(), [])

    def test_profile_has_frozen_header_and_window(self):
        text = (ROOT / "conformance" / "mcp-2025-11-25.yaml").read_text(encoding="utf-8")
        profile = conformance.parse(text)
        self.assertTrue(text.startswith("# FROZEN."))
        ids = {rule_id for rule_id, _ in profile.rules}
        self.assertIn("DISC-11", ids)
        self.assertNotIn("CHG-11", ids)

    def test_parser_is_strict(self):
        good = conformance.render("2026-07-28")
        with self.assertRaises(ValueError):
            conformance.parse(good.replace("# FROZEN.", "# frozen", 1))
        with self.assertRaises(ValueError):
            conformance.parse(good.replace("level: MUST}", "level: MUSTY}", 1))
        with self.assertRaises(ValueError):
            conformance.parse(good + "  - {id: NAME-1, level: MUST}\n")

    def _repo(self, tmp: str) -> Path:
        repo = Path(tmp)

        def git(*args):
            subprocess.run(["git", "-C", tmp, *args], check=True, capture_output=True)

        git("init", "-q")
        git("config", "user.email", "test@example.com")
        git("config", "user.name", "test")
        (repo / "conformance").mkdir()
        (repo / "conformance" / "mcp-2026-07-28.yaml").write_text("# FROZEN.\nfrozen_in: v9.9.9\n", encoding="utf-8")
        git("add", ".")
        git("commit", "-qm", "profile")
        return repo, git

    def test_guard_allows_changes_before_the_tag(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, _ = self._repo(tmp)
            (repo / "conformance" / "mcp-2026-07-28.yaml").write_text(
                "# FROZEN.\nfrozen_in: v9.9.9\nx\n", encoding="utf-8"
            )
            self.assertEqual(check_frozen.check(repo), [])

    def test_guard_fails_on_change_after_the_tag(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, git = self._repo(tmp)
            git("tag", "v9.9.9")
            self.assertEqual(check_frozen.check(repo), [])
            (repo / "conformance" / "mcp-2026-07-28.yaml").write_text(
                "# FROZEN.\nfrozen_in: v9.9.9\nx\n", encoding="utf-8"
            )
            problems = check_frozen.check(repo)
            self.assertEqual(len(problems), 1)
            self.assertIn("changed after v9.9.9", problems[0])


class Tracking(unittest.TestCase):
    FIXTURES = FIX / "upstream"

    def releases(self):
        return track.parse_releases(json.loads((self.FIXTURES / "releases.json").read_text(encoding="utf-8")))

    def changelog(self, rel):
        path = self.FIXTURES / f"{rel.rev}.mdx"
        return path.read_text(encoding="utf-8") if path.is_file() else ""

    def plan(self, issues):
        repo = UPSTREAM["mcp"]["repo"]
        return track.plan("o/r", repo, UPSTREAM, self.releases(), issues, self.changelog)

    def test_new_rc_opens_one_issue(self):
        actions = self.plan([])
        self.assertEqual([a["action"] for a in actions], ["create"])
        act = actions[0]
        self.assertEqual(act["title"], "Track MCP 2027-01-26")
        self.assertIn("releases/tag/2027-01-26-RC", act["body"])
        self.assertIn("blob/2027-01-26-RC/docs/specification/2027-01-26/changelog.mdx", act["body"])
        self.assertIn("- Add the `example/ping` method.", act["body"])
        self.assertNotIn("Not part of the summary", act["body"])
        self.assertIn("draft PR", act["body"])

    def issue(self, body, labeled=True, state="open"):
        labels = [{"name": track.LABEL}] if labeled else []
        return {"number": 7, "title": "Track MCP 2027-01-26", "body": body, "labels": labels, "state": state}

    def test_existing_issue_is_updated_not_duplicated(self):
        body = self.plan([])[0]["body"]
        self.assertEqual(self.plan([self.issue(body)]), [])
        actions = self.plan([self.issue("old")])
        self.assertEqual([(a["action"], a["number"]) for a in actions], [("update", 7)])

    def test_closed_issue_is_left_alone(self):
        self.assertEqual(self.plan([self.issue("old", labeled=False, state="closed")]), [])

    def test_relabel_on_a_new_upstream_tag_or_a_missing_label(self):
        body = self.plan([])[0]["body"]
        self.assertIn(f"`{track.LABEL}` label starts the [upstream agent]", body)
        edited = body.replace("Add the `example/ping` method.", "Reworded upstream.")
        self.assertEqual([a["relabel"] for a in self.plan([self.issue(edited)])], [False])
        old_tag = body.replace("2027-01-26-RC -->", "2027-01-26-RC0 -->")
        self.assertEqual([a["relabel"] for a in self.plan([self.issue(old_tag)])], [True])
        repair = self.plan([self.issue(body, labeled=False)])
        self.assertEqual([(a["relabel"], a["body"]) for a in repair], [(True, None)])

    def run_live(self, issues, fail=None):
        """Run main() against a fake GitHub. Returns (method, last path parts) per call."""
        calls = []

        class FakeGitHub:
            token = "t"

            def __init__(self, token):
                pass

            def request(self, method, path, body=None, raw=False):
                calls.append((method, path.rsplit("/", 2)[-2:], body))
                if method == fail:
                    raise track.urllib.error.HTTPError(path, 500, "Server Error", None, io.BytesIO())
                return []

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "issues.json"
            path.write_text(json.dumps(issues), encoding="utf-8")
            args = ["--releases-file", str(self.FIXTURES / "releases.json"), "--changelog-dir", str(self.FIXTURES)]
            with mock.patch.object(track, "GitHub", FakeGitHub), contextlib.redirect_stdout(io.StringIO()):
                if fail:
                    with self.assertRaises(track.urllib.error.HTTPError) as caught:
                        track.main(args + ["--issues-file", str(path)])
                    caught.exception.close()
                else:
                    self.assertEqual(track.main(args + ["--issues-file", str(path)]), 0)
        return calls

    def test_live_run_labels_new_issues(self):
        calls = self.run_live([])
        self.assertEqual([(m, b["labels"]) for m, _, b in calls], [("POST", [track.LABEL])])

    def test_live_run_relabels_on_new_tag_in_a_safe_order(self):
        body = self.plan([])[0]["body"]
        stale = [self.issue(body.replace("-RC -->", "-RC0 -->"))]
        self.assertEqual(
            [(m, p) for m, p, _ in self.run_live(stale)],
            [("DELETE", ["labels", track.LABEL]), ("PATCH", ["issues", "7"]), ("POST", ["7", "labels"])],
        )

    def test_failed_label_add_is_repaired_on_the_next_run(self):
        body = self.plan([])[0]["body"]
        stale = body.replace("-RC -->", "-RC0 -->")
        calls = self.run_live([self.issue(stale)], fail="POST")
        # The label removal and the body update went through; the label add did not.
        patched = next(b["body"] for m, _, b in calls if m == "PATCH")
        after_failure = [self.issue(patched, labeled=False)]
        self.assertEqual([(m, p) for m, p, _ in self.run_live(after_failure)], [("POST", ["7", "labels"])])

    def test_final_beats_rc_and_known_releases_are_ignored(self):
        final = track.Release("2027-01-26", "2027-01-26", False, "https://example.test/final", "2027-01-26T00:00:00Z")
        new = track.new_revisions(UPSTREAM, self.releases() + [final])
        self.assertEqual([(r.rev, r.rc) for r in new], [("2027-01-26", False)])
        known_only = [r for r in self.releases() if not r.rev.startswith("2027")]
        self.assertEqual(track.new_revisions(UPSTREAM, known_only), [])

    def test_dry_run_cli(self):
        out = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp:
            issues = Path(tmp) / "issues.json"
            issues.write_text("[]", encoding="utf-8")
            with contextlib.redirect_stdout(out):
                code = track.main(
                    [
                        "--dry-run",
                        "--releases-file",
                        str(self.FIXTURES / "releases.json"),
                        "--changelog-dir",
                        str(self.FIXTURES),
                        "--issues-file",
                        str(issues),
                    ]
                )
        self.assertEqual(code, 0)
        self.assertIn("would create issue 'Track MCP 2027-01-26'", out.getvalue())


if __name__ == "__main__":
    unittest.main()
