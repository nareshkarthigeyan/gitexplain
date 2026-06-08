import os
import shutil
import tempfile
import unittest
from pathlib import Path

from gx.services.cache import (
    clear_cache,
    create_cache_key,
    get_cache_directory,
    get_cache_stats,
    read_cache,
    write_cache,
)

class TestCacheService(unittest.TestCase):
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

    def test_write_and_read_cache_round_trip(self):
        cache_key = create_cache_key({"prompt": "summary", "ref": "HEAD"})
        value = {
            "explanation": "Hello from cache",
            "responseMeta": {"provider": "openai", "model": "gpt-4.1-mini", "cacheHit": False, "latencyMs": 12}
        }

        write_cache(cache_key, value)
        self.assertEqual(read_cache(cache_key), value)

    def test_clear_cache_removes_files_and_returns_count(self):
        write_cache(create_cache_key({"prompt": "one"}), {"explanation": "1", "responseMeta": {"provider": "openai", "model": "m", "cacheHit": False, "latencyMs": 1}})
        write_cache(create_cache_key({"prompt": "two"}), {"explanation": "2", "responseMeta": {"provider": "openai", "model": "m", "cacheHit": False, "latencyMs": 1}})

        deleted_count = clear_cache()
        self.assertEqual(deleted_count, 2)
        self.assertFalse(os.path.exists(get_cache_directory()))

    def test_get_cache_stats_reports_correct_values(self):
        write_cache(create_cache_key({"prompt": "stats-one"}), {"explanation": "1", "responseMeta": {"provider": "openai", "model": "m", "cacheHit": False, "latencyMs": 1}})
        write_cache(create_cache_key({"prompt": "stats-two"}), {"explanation": "2", "responseMeta": {"provider": "openai", "model": "m", "cacheHit": False, "latencyMs": 1}})

        stats = get_cache_stats()
        self.assertEqual(stats["entryCount"], 2)
        self.assertGreater(stats["totalSizeBytes"], 0)
        self.assertTrue(stats["oldestEntryIso"].startswith("202"))
        self.assertTrue(stats["newestEntryIso"].startswith("202"))

if __name__ == "__main__":
    unittest.main()
