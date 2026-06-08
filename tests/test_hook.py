import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from gx.services.hook import install_hook

class TestHookService(unittest.TestCase):
    def setUp(self):
        self.cwd = tempfile.mkdtemp()
        subprocess.run(["git", "init"], cwd=self.cwd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def tearDown(self):
        shutil.rmtree(self.cwd, ignore_errors=True)

    def test_install_hook_writes_post_merge_and_pre_push_scripts(self):
        post_merge_path = install_hook(self.cwd, "post-merge")
        pre_push_path = install_hook(self.cwd, "pre-push")

        with open(post_merge_path, "r", encoding="utf-8") as f:
            post_merge_content = f.read()
        with open(pre_push_path, "r", encoding="utf-8") as f:
            pre_push_content = f.read()

        self.assertIn("last-merge-explanation.md", post_merge_content)
        self.assertIn("--security --markdown --quiet", pre_push_content)

if __name__ == "__main__":
    unittest.main()
