import json
import re
import unittest
from unittest.mock import patch, PropertyMock

from gx.services.output import (
    format_html_output,
    format_json_output,
    format_markdown_output,
    format_output,
)

def strip_ansi(text: str) -> str:
    return re.sub(r'\u001b\[[0-9;]*m', '', text)

class TestOutputFormatter(unittest.TestCase):
    def setUp(self):
        self.commit_data = {
            "analysisType": "commit",
            "displayRef": "abc123",
            "commitId": "abc123",
            "commitCount": 1,
            "commitMessage": "Fix login crash",
            "filesChanged": ["src/auth.js"],
            "stats": "1 file changed, 4 insertions(+), 1 deletion(-)"
        }

    def test_format_output_includes_header_and_explanation(self):
        formatted = strip_ansi(
            format_output({
                "mode": "full",
                "commitData": self.commit_data,
                "explanation": "Summary:\nFix login crash",
                "responseMeta": None,
                "promptMeta": {"warnings": []},
                "options": {"quiet": False, "verbose": False}
            })
        )

        self.assertTrue(re.search(r'Commit: abc123|Range: abc123', formatted))
        self.assertIn("Fix login crash", formatted)

    def test_format_output_normalizes_headings_and_readable_spacing(self):
        formatted = strip_ansi(
            format_output({
                "mode": "full",
                "commitData": self.commit_data,
                "explanation": "1. Summary\n- Fixed login crash\n2. Security Review\n- No significant findings",
                "responseMeta": None,
                "promptMeta": {"warnings": []},
                "options": {"quiet": False, "verbose": False}
            })
        )

        self.assertIn("Summary:\n- Fixed login crash\n\nSecurity Review:\n- No significant findings", formatted)

    @patch("gx.services.color.sys.stdout.isatty", return_value=True)
    @patch.dict("os.environ", {"FORCE_COLOR": "1"})
    def test_format_output_keeps_bullet_markers_styled(self, mock_isatty):
        formatted = format_output({
            "mode": "review",
            "commitData": self.commit_data,
            "explanation": "Review Findings:\n- High risk regression in auth flow\nSuggestions:\n- Safe improvement: add coverage",
            "responseMeta": None,
            "promptMeta": {"warnings": []},
            "options": {"quiet": False, "verbose": False}
        })

        self.assertIn("\u001b[36m-\u001b[0m", formatted)
        self.assertNotIn("\u001b[31m-\u001b[0m", formatted)
        self.assertNotIn("\u001b[32m-\u001b[0m", formatted)
        self.assertNotIn("\u001b[33m-\u001b[0m", formatted)

    def test_format_output_converts_markdown_headings_and_inline_formatting(self):
        formatted = strip_ansi(
            format_output({
                "mode": "full",
                "commitData": self.commit_data,
                "explanation": "## **Summary**\n- **Good:** fixed login redirect\n\n### Review Findings\n1. **Issue:** missing null check\n\n```js\nconst ok = true;\n```",
                "responseMeta": None,
                "promptMeta": {"warnings": []},
                "options": {"quiet": False, "verbose": False}
            })
        )

        self.assertIn("Summary:\n- Good: fixed login redirect", formatted)
        self.assertIn("Review Findings:\n1. Issue: missing null check", formatted)
        self.assertIn("  const ok = true;", formatted)
        self.assertNotIn("```", formatted)
        self.assertNotIn("**", formatted)

    def test_format_output_converts_markdown_numbered_headings(self):
        formatted = strip_ansi(
            format_output({
                "mode": "full",
                "commitData": self.commit_data,
                "explanation": "### 1. Summary:\nRefactor release planning.\n\n### 2. Issue:\nDuplicated logic.",
                "responseMeta": None,
                "promptMeta": {"warnings": []},
                "options": {"quiet": True, "verbose": False}
            })
        )

        self.assertEqual(formatted, "Summary:\nRefactor release planning.\n\nIssue:\nDuplicated logic.")

    @patch("gx.services.color.sys.stdout.isatty", return_value=True)
    @patch.dict("os.environ", {"FORCE_COLOR": "1"})
    def test_format_output_leaves_risk_level_text_uncolored(self, mock_isatty):
        formatted = format_output({
            "mode": "full",
            "commitData": self.commit_data,
            "explanation": "Risk Level:\nLow. The change is a simple refactoring with minimal risk.",
            "responseMeta": None,
            "promptMeta": {"warnings": []},
            "options": {"quiet": True, "verbose": False}
        })

        self.assertIn("Low. The change is a simple refactoring with minimal risk.", formatted)
        # Check that low is not colored
        self.assertNotIn("\u001b[31mLow\u001b[0m", formatted)

    def test_format_markdown_output(self):
        formatted = format_markdown_output({
            "mode": "summary",
            "commitData": self.commit_data,
            "explanation": "Short summary",
            "responseMeta": {"provider": "openai", "model": "gpt-4.1-mini"},
            "promptMeta": {"warnings": []}
        })

        self.assertIn("# gx", formatted)
        self.assertIn("Provider: openai", formatted)
        self.assertIn("Short summary", formatted)

    def test_format_json_output(self):
        formatted = format_json_output({
            "mode": "summary",
            "commitData": self.commit_data,
            "explanation": "Short summary",
            "responseMeta": {"provider": "openai", "model": "gpt-4.1-mini"},
            "promptMeta": {"truncated": False, "warnings": []}
        })

        parsed = json.loads(formatted)
        self.assertEqual(parsed["mode"], "summary")
        self.assertEqual(parsed["commit"]["id"], "abc123")
        self.assertEqual(parsed["response"]["provider"], "openai")

if __name__ == "__main__":
    unittest.main()
