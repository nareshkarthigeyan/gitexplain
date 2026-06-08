import os
import shutil
import tempfile
import unittest
from pathlib import Path

from gx.services.usage import (
    append_usage_record,
    clear_usage_log,
    estimate_cost_usd,
    get_usage_log_file,
    get_usage_stats,
    normalize_usage_metrics,
    resolve_pricing,
)

class TestUsageService(unittest.TestCase):
    def setUp(self):
        self.temp_home = tempfile.mkdtemp()
        self.original_home = os.environ.get("HOME")
        self.original_userprofile = os.environ.get("USERPROFILE")
        os.environ["HOME"] = self.temp_home
        os.environ["USERPROFILE"] = self.temp_home

    def tearDown(self):
        if self.original_home is not None:
            os.environ["HOME"] = self.original_home
        else:
            os.environ.pop("HOME", None)

        if self.original_userprofile is not None:
            os.environ["USERPROFILE"] = self.original_userprofile
        else:
            os.environ.pop("USERPROFILE", None)

        shutil.rmtree(self.temp_home, ignore_errors=True)

    def test_normalize_usage_metrics(self):
        self.assertEqual(
            normalize_usage_metrics({"prompt_tokens": 10, "completion_tokens": 4, "total_tokens": 14}),
            {"inputTokens": 10, "outputTokens": 4, "totalTokens": 14}
        )
        self.assertEqual(
            normalize_usage_metrics({"promptTokenCount": 8, "candidatesTokenCount": 3, "totalTokenCount": 11}),
            {"inputTokens": 8, "outputTokens": 3, "totalTokens": 11}
        )

    def test_resolve_pricing(self):
        original_input = os.environ.get("OPENAI_INPUT_COST_PER_MTOK")
        original_output = os.environ.get("OPENAI_OUTPUT_COST_PER_MTOK")

        try:
            os.environ["OPENAI_INPUT_COST_PER_MTOK"] = "0.15"
            os.environ["OPENAI_OUTPUT_COST_PER_MTOK"] = "0.60"

            self.assertEqual(
                resolve_pricing({"provider": "openai", "model": "gpt-4.1-mini"}),
                {"inputPerMillion": 0.15, "outputPerMillion": 0.60}
            )
        finally:
            if original_input is not None:
                os.environ["OPENAI_INPUT_COST_PER_MTOK"] = original_input
            else:
                os.environ.pop("OPENAI_INPUT_COST_PER_MTOK", None)

            if original_output is not None:
                os.environ["OPENAI_OUTPUT_COST_PER_MTOK"] = original_output
            else:
                os.environ.pop("OPENAI_OUTPUT_COST_PER_MTOK", None)

    def test_estimate_cost_usd(self):
        cost = estimate_cost_usd(
            {"prompt_tokens": 1000, "completion_tokens": 500},
            {"inputPerMillion": 1.0, "outputPerMillion": 2.0}
        )
        self.assertAlmostEqual(cost, 0.002)

    def test_usage_log_persists(self):
        append_usage_record({
            "provider": "openai",
            "model": "gpt-4.1-mini",
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            "latencyMs": 120,
            "estimatedCostUsd": 0.0001
        })
        append_usage_record({
            "provider": "anthropic",
            "model": "claude-3-5-haiku-latest",
            "usage": {"input_tokens": 4, "output_tokens": 6},
            "latencyMs": 95,
            "estimatedCostUsd": 0.0002
        })

        stats = get_usage_stats()
        self.assertEqual(stats["requestCount"], 2)
        self.assertEqual(stats["inputTokens"], 14)
        self.assertEqual(stats["outputTokens"], 11)
        self.assertEqual(stats["totalTokens"], 25)
        self.assertAlmostEqual(stats["estimatedCostUsd"], 0.0003)
        self.assertTrue(os.path.exists(get_usage_log_file()))
        self.assertEqual(clear_usage_log(), 2)

if __name__ == "__main__":
    unittest.main()
