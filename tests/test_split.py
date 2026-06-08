import os
import shutil
import subprocess
import tempfile
import unittest

from gx.services.split import (
    execute_split,
    format_split_plan,
    parse_split_plan,
    reconcile_split_plan,
    validate_split_execution_target,
)

class TestSplitService(unittest.TestCase):
    def create_repo_fixture(self):
        cwd = tempfile.mkdtemp()
        subprocess.run(["git", "init", "-b", "main"], cwd=cwd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["git", "config", "user.name", "Gitxplain Test"], cwd=cwd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["git", "config", "user.email", "gx@example.com"], cwd=cwd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return cwd

    def test_parse_split_plan_valid(self):
        plan = parse_split_plan("""{
            "original_summary": "Added validation and tests.",
            "reason_to_split": "Feature logic and tests should be separated.",
            "commits": [
                {
                    "order": 1,
                    "message": "feat: add validation helper",
                    "files": ["src/validation.js"],
                    "description": "Adds the reusable validation helper."
                }
            ]
        }""")

        self.assertEqual(plan["original_summary"], "Added validation and tests.")
        self.assertEqual(plan["commits"][0]["message"], "feat: add validation helper")

    def test_parse_split_plan_fenced_json(self):
        plan = parse_split_plan("""```json
        {
          "original_summary": "Added validation and tests.",
          "reason_to_split": null,
          "commits": []
        }
        ```""")

        self.assertIsNone(plan["reason_to_split"])
        self.assertEqual(plan["commits"], [])

    def test_parse_split_plan_invalid(self):
        with self.assertRaises(RuntimeError):
            parse_split_plan("{not valid json}")

    def test_parse_split_plan_deduplicates_files(self):
        plan = parse_split_plan("""{
            "original_summary": "Adds validation and tests.",
            "reason_to_split": "Separate implementation and tests.",
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

    def test_reconcile_split_plan_removes_extra_and_adds_missing(self):
        plan = reconcile_split_plan(
            {
                "original_summary": "Initial commit",
                "reason_to_split": "Separate docs and code.",
                "warnings": [],
                "commits": [
                    {
                        "order": 1,
                        "message": "feat: add code",
                        "files": ["src/app.js", ".npmignore"],
                        "description": "Adds code."
                    }
                ]
            },
            ["src/app.js", "README.md"]
        )

        self.assertEqual(plan["commits"][0]["files"], ["src/app.js"])
        self.assertEqual(plan["commits"][1]["files"], ["README.md"])
        self.assertTrue(any("Files not present in the target commit" in w for w in plan["warnings"]))
        self.assertTrue(any("Missing files were added" in w for w in plan["warnings"]))

    def test_format_split_plan(self):
        output = format_split_plan({
            "original_summary": "Added validation and tests.",
            "reason_to_split": "The change mixes app logic and test coverage.",
            "warnings": ["Duplicate file assignments were removed from later split groups: test/validation.test.js."],
            "commits": [
                {
                    "order": 1,
                    "message": "feat: add validation helper",
                    "files": ["src/validation.js"],
                    "description": "Adds the helper implementation."
                },
                {
                    "order": 2,
                    "message": "test: cover validation helper",
                    "files": ["test/validation.test.js"],
                    "description": "Adds focused test coverage."
                }
            ]
        })

        self.assertIn("Split Plan", output)
        self.assertIn("Original Summary:", output)
        self.assertIn("Reason To Split:", output)
        self.assertIn("Warning:", output)
        self.assertIn("1. feat: add validation helper", output)
        self.assertIn("Files: src/validation.js", output)
        self.assertIn("Why: Adds the helper implementation.", output)

    def test_validate_split_execution_target_allows_reachable(self):
        helpers = {
            "resolveCommitSha": lambda ref, cwd: "abc123",
            "getCurrentHeadSha": lambda cwd: "def456",
            "getCommitParents": lambda ref, cwd: ["parent123"],
            "isAncestorCommit": lambda anc, desc, cwd: True
        }

        result = validate_split_execution_target("abc123", "/tmp", helpers)
        self.assertEqual(result["targetSha"], "abc123")
        self.assertEqual(result["currentHeadSha"], "def456")
        self.assertEqual(result["parentSha"], "parent123")
        self.assertEqual(result["isHeadTarget"], False)

    def test_validate_split_execution_target_rejects_unreachable(self):
        helpers = {
            "resolveCommitSha": lambda ref, cwd: "abc123",
            "getCurrentHeadSha": lambda cwd: "def456",
            "getCommitParents": lambda ref, cwd: ["parent123"],
            "isAncestorCommit": lambda anc, desc, cwd: False
        }

        with self.assertRaises(RuntimeError):
            validate_split_execution_target("abc123", "/tmp", helpers)

    def test_validate_split_execution_target_rejects_merge(self):
        helpers = {
            "resolveCommitSha": lambda ref, cwd: "abc123",
            "getCurrentHeadSha": lambda cwd: "abc123",
            "getCommitParents": lambda ref, cwd: ["parent1", "parent2"],
            "isAncestorCommit": lambda anc, desc, cwd: True
        }

        with self.assertRaises(RuntimeError):
            validate_split_execution_target("abc123", "/tmp", helpers)

    def test_execute_split_root(self):
        cwd = self.create_repo_fixture()
        try:
            with open(os.path.join(cwd, "a.txt"), "w", encoding="utf-8") as f:
                f.write("one\n")
            with open(os.path.join(cwd, "b.txt"), "w", encoding="utf-8") as f:
                f.write("two\n")
            
            subprocess.run(["git", "add", "."], cwd=cwd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["git", "commit", "-m", "root"], cwd=cwd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            root_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=cwd, capture_output=True, text=True).stdout.strip()

            with open(os.path.join(cwd, "a.txt"), "w", encoding="utf-8") as f:
                f.write("one\ntail\n")
            subprocess.run(["git", "add", "a.txt"], cwd=cwd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["git", "commit", "-m", "follow-up"], cwd=cwd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            original_head_tree = subprocess.run(["git", "rev-parse", "HEAD^{tree}"], cwd=cwd, capture_output=True, text=True).stdout.strip()

            execute_split(
                {
                    "original_summary": "Initial project files.",
                    "reason_to_split": "Split root files.",
                    "commits": [
                        {
                            "order": 1,
                            "message": "feat: add a",
                            "files": ["a.txt"],
                            "description": "Adds a.txt."
                        },
                        {
                            "order": 2,
                            "message": "feat: add b",
                            "files": ["b.txt"],
                            "description": "Adds b.txt."
                        }
                    ]
                },
                root_sha,
                cwd
            )

            log_subjects = subprocess.run(["git", "log", "--reverse", "--pretty=format:%s"], cwd=cwd, capture_output=True, text=True).stdout.strip().split("\n")
            self.assertEqual(log_subjects, ["feat: add a", "feat: add b", "follow-up"])
            
            current_head_tree = subprocess.run(["git", "rev-parse", "HEAD^{tree}"], cwd=cwd, capture_output=True, text=True).stdout.strip()
            self.assertEqual(current_head_tree, original_head_tree)
        finally:
            shutil.rmtree(cwd, ignore_errors=True)

if __name__ == "__main__":
    unittest.main()
