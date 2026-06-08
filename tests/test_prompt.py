import unittest
from gx.services.prompt import build_prompt

class TestPromptService(unittest.TestCase):
    def setUp(self):
        self.commit_data = {
            "analysisType": "commit",
            "commitMessage": "Fix null token handling",
            "filesChanged": ["src/auth.js"],
            "stats": "1 file changed, 4 insertions(+), 1 deletion(-)",
            "diff": "\n".join(f"line {i + 1}" for i in range(10))
        }

    def test_build_prompt_truncates_long_diffs_and_reports_metadata(self):
        prompt, prompt_meta = build_prompt("full", self.commit_data, {"maxDiffLines": 3})

        self.assertIn("Diff truncated: kept 3 of 10 lines", prompt)
        self.assertTrue(prompt_meta["truncated"])
        self.assertEqual(prompt_meta["keptDiffLines"], 3)
        self.assertEqual(prompt_meta["diffLineCount"], 10)

    def test_build_prompt_adds_range_prelude(self):
        commit_range_data = {
            **self.commit_data,
            "analysisType": "range",
            "commitCount": 2,
            "commits": [
                {"hash": "1234567", "subject": "First change"},
                {"hash": "89abcde", "subject": "Second change"}
            ]
        }
        prompt, _ = build_prompt("summary", commit_range_data, {"maxDiffLines": 20})

        self.assertIn("This analysis covers a range of commits", prompt)
        self.assertIn("Commit Count: 2", prompt)

    def test_build_prompt_flags_comment_only_diffs(self):
        comment_diff = {
            **self.commit_data,
            "analysisType": "workingTree",
            "commitMessage": "Uncommitted working tree changes",
            "filesChanged": ["cli/services/configService.js"],
            "diff": "\n".join([
                "diff --git a/cli/services/configService.js b/cli/services/configService.js",
                "index c4508b6..de4d996 100644",
                "--- a/cli/services/configService.js",
                "+++ b/cli/services/configService.js",
                "@@ -14,6 +14,7 @@ function readJsonConfig(filePath) {",
                "+// Load configuration with the following precedence:"
            ])
        }
        prompt, _ = build_prompt("commit", comment_diff, {"maxDiffLines": 20})

        self.assertIn("All changed lines appear to be comments or whitespace", prompt)
        self.assertIn("prefer `docs:` or `chore:` wording instead of `feat:`/`fix:`", prompt)

    def test_build_prompt_loads_all_modes(self):
        modes = ["refactor", "changelog", "blame", "stash", "conflict"]
        expected_patterns = {
            "refactor": "Review this change for refactoring opportunities",
            "changelog": "Generate release notes in a conventional-changelog style",
            "blame": "Analyze this git blame report for a file",
            "stash": "Explain the contents of this Git stash entry",
            "conflict": "You are helping resolve unresolved Git merge conflicts"
        }

        for mode in modes:
            prompt, _ = build_prompt(mode, self.commit_data, {"maxDiffLines": 20})
            self.assertIn(expected_patterns[mode], prompt)

if __name__ == "__main__":
    unittest.main()
