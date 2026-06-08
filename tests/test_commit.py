import os
import shutil
import subprocess
import tempfile
import unittest

from gx.services.commit import (
    execute_commit_plan,
    format_commit_plan,
    parse_commit_plan,
    reconcile_commit_plan,
)

class TestCommitService(unittest.TestCase):
    def create_repo_fixture(self):
        cwd = tempfile.mkdtemp()
        subprocess.run(["git", "init", "-b", "main"], cwd=cwd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["git", "config", "user.name", "Gitxplain Test"], cwd=cwd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["git", "config", "user.email", "gx@example.com"], cwd=cwd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        tracked_path = os.path.join(cwd, "tracked.txt")
        with open(tracked_path, "w", encoding="utf-8") as f:
            f.write("base\n")
        
        subprocess.run(["git", "add", "tracked.txt"], cwd=cwd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["git", "commit", "-m", "base"], cwd=cwd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return cwd

    def test_parse_commit_plan_parses_valid_json(self):
        plan = parse_commit_plan("""{
            "working_tree_summary": "Adds validation logic and tests.",
            "reason_to_commit": "The implementation and tests should be committed separately.",
            "commits": [
                {
                    "order": 1,
                    "message": "feat: add validation helper",
                    "files": ["src/validation.js"],
                    "description": "Adds the validation helper."
                }
            ]
        }""")

        self.assertEqual(plan["working_tree_summary"], "Adds validation logic and tests.")
        self.assertEqual(plan["commits"][0]["message"], "feat: add validation helper")

    def test_parse_commit_plan_parses_fenced_json(self):
        plan = parse_commit_plan("""```json
        {
          "working_tree_summary": "No meaningful changes detected",
          "reason_to_commit": null,
          "commits": []
        }
        ```""")

        self.assertIsNone(plan["reason_to_commit"])
        self.assertEqual(plan["commits"], [])

    def test_parse_commit_plan_parses_javascript_fenced_json(self):
        plan = parse_commit_plan("""```javascript
        {
          "working_tree_summary": "No meaningful changes detected",
          "reason_to_commit": null,
          "commits": []
        }
        ```""")

        self.assertIsNone(plan["reason_to_commit"])
        self.assertEqual(plan["commits"], [])

    def test_parse_commit_plan_text_fallback(self):
        plan = parse_commit_plan("""
        Working Tree Summary: Adds validation logic and tests.
        Reason To Commit: The implementation and tests should be committed separately.

        1. feat: add validation helper
        Files: src/validation.js
        Why: Adds the validation helper.

        2. test: add validation coverage
        Files: test/validation.test.js
        Why: Adds tests for the helper.
        """)

        self.assertEqual(plan["working_tree_summary"], "Adds validation logic and tests.")
        self.assertEqual(plan["reason_to_commit"], "The implementation and tests should be committed separately.")
        self.assertEqual(len(plan["commits"]), 2)
        self.assertEqual(plan["commits"][0]["message"], "feat: add validation helper")
        self.assertEqual(plan["commits"][0]["files"], ["src/validation.js"])

    def test_parse_commit_plan_invalid_json(self):
        with self.assertRaises(RuntimeError):
            parse_commit_plan("{broken json}")

    def test_parse_commit_plan_deduplicates_files(self):
        plan = parse_commit_plan("""{
            "working_tree_summary": "Adds validation logic and tests.",
            "reason_to_commit": "Separate implementation and tests.",
            "commits": [
                {
                    "order": 1,
                    "message": "feat: add validation helper",
                    "files": ["src/validation.js", "test/validation.test.js"],
                    "description": "Adds implementation."
                },
                {
                    "order": 2,
                    "message": "test: add validation coverage",
                    "files": ["test/validation.test.js"],
                    "description": "Adds tests."
                }
            ]
        }""")

        self.assertEqual(plan["commits"][0]["files"], ["src/validation.js", "test/validation.test.js"])
        self.assertEqual(len(plan["commits"]), 1)
        self.assertTrue(any("Duplicate file assignments" in w for w in plan["warnings"]))

    def test_format_commit_plan(self):
        output = format_commit_plan({
            "working_tree_summary": "Adds validation logic and tests.",
            "reason_to_commit": "The implementation and tests should be committed separately.",
            "warnings": ["Duplicate file assignments were removed from later commit groups: src/validation.js."],
            "commits": [
                {
                    "order": 1,
                    "message": "feat: add validation helper",
                    "files": ["src/validation.js"],
                    "description": "Adds the validation helper."
                }
            ]
        })

        self.assertIn("Commit Plan", output)
        self.assertIn("Working Tree Summary:", output)
        self.assertIn("Reason To Commit:", output)
        self.assertIn("Warning:", output)
        self.assertIn("1. feat: add validation helper", output)

    def test_reconcile_commit_plan_adds_missing_files(self):
        cwd = self.create_repo_fixture()
        try:
            with open(os.path.join(cwd, "tracked.txt"), "w", encoding="utf-8") as f:
                f.write("base\nupdated\n")
            with open(os.path.join(cwd, "extra.txt"), "w", encoding="utf-8") as f:
                f.write("new file\n")

            plan = reconcile_commit_plan(
                {
                    "working_tree_summary": "Updates tracked file and adds extra file.",
                    "reason_to_commit": "Split changes.",
                    "commits": [
                        {
                            "order": 1,
                            "message": "feat: update tracked file",
                            "files": ["tracked.txt"],
                            "description": "Updates only the tracked file."
                        }
                    ]
                },
                cwd
            )

            self.assertEqual(len(plan["commits"]), 2)
            self.assertEqual(plan["commits"][1]["files"], ["extra.txt"])
            self.assertIn("include remaining working tree changes", plan["commits"][1]["message"])
            self.assertTrue(any("Missing files were added" in w for w in plan["warnings"]))
        finally:
            shutil.rmtree(cwd, ignore_errors=True)

    def test_execute_commit_plan_refuses_incomplete_plan(self):
        cwd = self.create_repo_fixture()
        try:
            with open(os.path.join(cwd, "tracked.txt"), "w", encoding="utf-8") as f:
                f.write("base\nupdated\n")
            with open(os.path.join(cwd, "extra.txt"), "w", encoding="utf-8") as f:
                f.write("new file\n")

            with self.assertRaises(RuntimeError):
                execute_commit_plan(
                    {
                        "working_tree_summary": "Updates tracked file and adds extra file.",
                        "reason_to_commit": "Split changes.",
                        "commits": [
                            {
                                "order": 1,
                                "message": "feat: update tracked file",
                                "files": ["tracked.txt"],
                                "description": "Updates only the tracked file."
                            }
                        ]
                    },
                    cwd
                )

            # verify files are still modified/untracked
            status = subprocess.run(["git", "status", "--short"], cwd=cwd, capture_output=True, text=True).stdout
            self.assertIn("tracked.txt", status)
            self.assertIn("extra.txt", status)
        finally:
            shutil.rmtree(cwd, ignore_errors=True)

if __name__ == "__main__":
    unittest.main()
