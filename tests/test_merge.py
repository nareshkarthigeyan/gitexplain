import json
import os
import shutil
import subprocess
import tempfile
import unittest

from gx.services.merge import (
    build_release_merge_plan,
    build_release_status,
    build_release_tag_plan,
    build_release_windows,
    detect_version_changes,
    execute_release_merge,
    finalize_release_merge_plan,
    finalize_release_tag_plan,
    format_release_merge_plan,
    format_release_status,
    format_release_tag_plan,
    select_release_tags,
    select_release_tags_from_release_commits,
    select_release_windows,
)

class TestMergeService(unittest.TestCase):
    def test_detect_version_changes_finds_semver_bumps(self):
        change = detect_version_changes("""
diff --git a/package.json b/package.json
--- a/package.json
+++ b/package.json
@@
-  "version": "0.1.0",
+  "version": "0.2.0",
   "name": "gx"
""")

        self.assertTrue(change["hasVersionChange"])
        self.assertEqual(change["from"], ["0.1.0"])
        self.assertEqual(change["to"], ["0.2.0"])

    def test_detect_version_changes_ignores_non_version_diff(self):
        change = detect_version_changes("""
diff --git a/README.md b/README.md
--- a/README.md
+++ b/README.md
@@
-Old copy
+New copy
""")

        self.assertFalse(change["hasVersionChange"])
        self.assertEqual(change["from"], [])
        self.assertEqual(change["to"], [])

    def test_detect_version_changes_reads_android_gradle(self):
        change = detect_version_changes("""
diff --git a/android/app/build.gradle b/android/app/build.gradle
--- a/android/app/build.gradle
+++ b/android/app/build.gradle
@@
-        versionCode 14
-        versionName "1.4.0"
+        versionCode 15
+        versionName "1.5.0"
""")

        self.assertTrue(change["hasVersionChange"])
        self.assertEqual(change["from"], ["14", "1.4.0"])
        self.assertEqual(change["to"], ["15", "1.5.0"])
        self.assertEqual(change["releaseVersion"], "1.5.0")

    def test_detect_version_changes_ignores_gradle_wrapper(self):
        change = detect_version_changes("""
diff --git a/android/gradle/wrapper/gradle-wrapper.properties b/android/gradle/wrapper/gradle-wrapper.properties
--- a/android/gradle/wrapper/gradle-wrapper.properties
+++ b/android/gradle/wrapper/gradle-wrapper.properties
@@
-distributionUrl=https\\://services.gradle.org/distributions/gradle-8.10.2-bin.zip
+distributionUrl=https\\://services.gradle.org/distributions/gradle-8.14.3-bin.zip
""")

        self.assertFalse(change["hasVersionChange"])
        self.assertEqual(change["from"], [])
        self.assertEqual(change["to"], [])
        self.assertIsNone(change["releaseVersion"])

    def test_build_release_windows_groups_commits(self):
        source_commits = [
            {
                "shortSha": "1111111",
                "subject": "docs: start release work",
                "releaseVersion": None,
                "versionChange": {"from": [], "to": [], "hasVersionChange": False}
            },
            {
                "shortSha": "2222222",
                "subject": "feat: finish release 0.1.1",
                "releaseVersion": "0.1.1",
                "versionChange": {"from": ["0.1.0"], "to": ["0.1.1"], "hasVersionChange": True}
            },
            {
                "shortSha": "3333333",
                "subject": "fix: follow-up for 0.1.1",
                "releaseVersion": "0.1.1",
                "versionChange": {"from": ["0.1.1"], "to": ["0.1.1"], "hasVersionChange": False}
            },
            {
                "shortSha": "4444444",
                "subject": "feat: start release 0.1.2",
                "releaseVersion": None,
                "versionChange": {"from": [], "to": [], "hasVersionChange": False}
            },
            {
                "shortSha": "5555555",
                "subject": "chore: bump to 0.1.2",
                "releaseVersion": "0.1.2",
                "versionChange": {"from": ["0.1.1"], "to": ["0.1.2"], "hasVersionChange": True}
            }
        ]

        windows = build_release_windows(source_commits)

        self.assertEqual(len(windows), 2)
        self.assertEqual(windows[0]["version"], "0.1.1")
        self.assertEqual([c["shortSha"] for c in windows[0]["commits"]], ["1111111", "2222222", "3333333", "4444444"])
        self.assertEqual(windows[1]["version"], "0.1.2")
        self.assertEqual([c["shortSha"] for c in windows[1]["commits"]], ["5555555"])

    def test_select_release_windows_skips_released(self):
        source_commits = [
            {
                "shortSha": "1111111",
                "subject": "docs: start release work",
                "releaseVersion": None,
                "versionChange": {"from": [], "to": [], "hasVersionChange": False}
            },
            {
                "shortSha": "2222222",
                "subject": "chore: bump to 0.1.1",
                "releaseVersion": "0.1.1",
                "versionChange": {"from": ["0.1.0"], "to": ["0.1.1"], "hasVersionChange": True}
            },
            {
                "shortSha": "3333333",
                "subject": "feat: follow-up",
                "releaseVersion": None,
                "versionChange": {"from": [], "to": [], "hasVersionChange": False}
            },
            {
                "shortSha": "4444444",
                "subject": "chore: bump to 0.1.2",
                "releaseVersion": "0.1.2",
                "versionChange": {"from": ["0.1.1"], "to": ["0.1.2"], "hasVersionChange": True}
            }
        ]

        release_commits = [
            {
                "subject": "release 0.1.1",
                "releaseVersion": None
            }
        ]

        selection = select_release_windows(source_commits, release_commits)

        self.assertEqual(selection["releasedVersions"], ["0.1.1"])
        self.assertEqual(len(selection["windows"]), 1)
        self.assertEqual(selection["windows"][0]["version"], "0.1.2")
        self.assertEqual([c["shortSha"] for c in selection["windows"][0]["commits"]], ["4444444"])

    def test_select_release_tags_maps_unreleased(self):
        source_commits = [
            {
                "sha": "1111111111111111111111111111111111111111",
                "shortSha": "1111111",
                "subject": "docs: prep 0.1.1",
                "releaseVersion": None,
                "versionChange": {"from": [], "to": [], "hasVersionChange": False}
            },
            {
                "sha": "2222222222222222222222222222222222222222",
                "shortSha": "2222222",
                "subject": "bump 0.1.1",
                "releaseVersion": "0.1.1",
                "versionChange": {"from": ["0.1.0"], "to": ["0.1.1"], "hasVersionChange": True}
            },
            {
                "sha": "3333333333333333333333333333333333333333",
                "shortSha": "3333333",
                "subject": "follow-up for 0.1.1",
                "releaseVersion": None,
                "versionChange": {"from": [], "to": [], "hasVersionChange": False}
            },
            {
                "sha": "4444444444444444444444444444444444444444",
                "shortSha": "4444444",
                "subject": "bump 0.1.2",
                "releaseVersion": "0.1.2",
                "versionChange": {"from": ["0.1.1"], "to": ["0.1.2"], "hasVersionChange": True}
            }
        ]

        selection = select_release_tags(source_commits, ["0.1.1"])

        self.assertEqual(selection["taggedVersions"], ["0.1.1"])
        self.assertEqual(len(selection["tags"]), 1)
        self.assertEqual(selection["tags"][0]["tagName"], "v0.1.2")
        self.assertEqual(selection["tags"][0]["targetSha"], "4444444444444444444444444444444444444444")
        self.assertEqual(selection["tags"][0]["targetShortSha"], "4444444")

    def test_select_release_tags_from_release_commits(self):
        release_commits = [
            {
                "sha": "1111111111111111111111111111111111111111",
                "shortSha": "1111111",
                "subject": "release 0.1.2",
                "versionChange": {"from": [], "to": [], "hasVersionChange": False}
            },
            {
                "sha": "2222222222222222222222222222222222222222",
                "shortSha": "2222222",
                "subject": "release 0.1.1",
                "versionChange": {"from": [], "to": [], "hasVersionChange": False}
            },
            {
                "sha": "3333333333333333333333333333333333333333",
                "shortSha": "3333333",
                "subject": "release 0.1.0",
                "versionChange": {"from": [], "to": [], "hasVersionChange": False}
            }
        ]

        selection = select_release_tags_from_release_commits(release_commits, ["0.1.1"])

        self.assertEqual(selection["taggedVersions"], ["0.1.1"])
        self.assertEqual(selection["latestDetectedVersion"], "0.1.0")
        self.assertEqual([t["tagName"] for t in selection["tags"]], ["v0.1.2", "v0.1.0"])
        self.assertEqual(selection["tags"][0]["targetSha"], "1111111111111111111111111111111111111111")
        self.assertEqual(selection["tags"][1]["targetSha"], "3333333333333333333333333333333333333333")

    def test_format_release_merge_plan(self):
        plan = finalize_release_merge_plan({
            "sourceBranch": "main",
            "releaseBranch": "release",
            "baseRef": "release",
            "releasedVersions": ["0.1.1"],
            "latestDetectedVersion": "0.1.2",
            "windows": [
                {
                    "version": "0.1.2",
                    "startRef": "3333333",
                    "endRef": "4444444",
                    "commits": [
                        {
                            "shortSha": "3333333",
                            "subject": "feat: follow-up",
                            "versionChange": {"from": [], "to": [], "hasVersionChange": False}
                        },
                        {
                            "shortSha": "4444444",
                            "subject": "chore: bump to 0.1.2",
                            "versionChange": {"from": ["0.1.1"], "to": ["0.1.2"], "hasVersionChange": True}
                        }
                    ]
                }
            ]
        })

        output = format_release_merge_plan(plan)

        self.assertIn("Release Merge Plan", output)
        self.assertIn("release 0.1.2", output)
        self.assertIn("Commit Range: 3333333..4444444", output)
        self.assertIn("Version: 0.1.1 -> 0.1.2", output)

    def test_execute_release_merge_orphan(self):
        repo_dir = tempfile.mkdtemp()
        def run_git(*args):
            return subprocess.run(["git"] + list(args), cwd=repo_dir, capture_output=True, text=True, check=True).stdout.strip()

        try:
            run_git("init", "-b", "main")
            run_git("config", "user.name", "Test User")
            run_git("config", "user.email", "test@example.com")

            with open(os.path.join(repo_dir, "package.json"), "w", encoding="utf-8") as f:
                f.write(json.dumps({"name": "gx", "version": "0.1.0"}, indent=2) + "\n")
            run_git("add", "package.json")
            run_git("commit", "-m", "chore: scaffold app")

            with open(os.path.join(repo_dir, "package.json"), "w", encoding="utf-8") as f:
                f.write(json.dumps({"name": "gx", "version": "0.1.1"}, indent=2) + "\n")
            run_git("commit", "-am", "chore: bump version to 0.1.1")

            plan = finalize_release_merge_plan(build_release_merge_plan(repo_dir))
            execute_release_merge(plan, repo_dir)

            release_subjects = run_git("log", "--format=%s", "release").split("\n")
            release_subjects = [s for s in release_subjects if s]

            self.assertEqual(release_subjects, ["release 0.1.1", "release 0.1.0"])

            # Verify no merge base
            has_merge_base = True
            try:
                run_git("merge-base", "main", "release")
            except subprocess.CalledProcessError:
                has_merge_base = False
            self.assertFalse(has_merge_base)
        finally:
            shutil.rmtree(repo_dir, ignore_errors=True)

if __name__ == "__main__":
    unittest.main()
