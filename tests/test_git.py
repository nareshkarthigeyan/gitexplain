import os
import shutil
import tempfile
import unittest

from gx.services.git import (
    fetch_blame_data,
    fetch_commit_data,
    fetch_commit_data_for_file,
    fetch_conflict_data,
    fetch_stash_data,
    git_pull,
    git_push,
    git_reset_hard,
    get_repository_log,
    get_repository_status,
    resolve_stash_ref,
    resolve_tree_sha,
)

class TestGitService(unittest.TestCase):
    def test_fetch_commit_data_reads_single_commit(self):
        responses = {
            'log -1 --pretty=format:%B abc123': 'Fix login crash',
            'diff abc123^!': 'diff --git a/src/auth.js b/src/auth.js',
            'show --pretty=format: --name-only abc123': 'src/auth.js',
            'show --stat --oneline --format=%h %s abc123': 'abc123 Fix login crash\n 1 file changed, 4 insertions(+), 1 deletion(-)',
            'log -1 --pretty=format:%s abc123': 'Fix login crash'
        }

        def mock_runner(args, cwd):
            cmd = " ".join(args)
            return responses.get(cmd, "")

        data = fetch_commit_data("abc123", "/tmp", runner=mock_runner)

        self.assertEqual(data["analysisType"], "commit")
        self.assertEqual(data["commitMessage"], "Fix login crash")
        self.assertEqual(data["filesChanged"], ["src/auth.js"])

    def test_fetch_blame_data(self):
        blame_output = "\n".join([
            "1111111111111111111111111111111111111111 1 1 1",
            "author Alice",
            "author-mail <alice@example.com>",
            "author-time 1712700000",
            "summary Initial parser",
            "\tconst a = 1;",
            "2222222222222222222222222222222222222222 2 2 1",
            "author Bob",
            "author-mail <bob@example.com>",
            "author-time 1712786400",
            "summary Add guard",
            "\tif (!value) return;",
            "2222222222222222222222222222222222222222 3 3 1",
            "author Bob",
            "author-mail <bob@example.com>",
            "author-time 1712786400",
            "summary Add guard",
            "\treturn value;"
        ])

        def mock_runner(args, cwd):
            self.assertEqual(args, ["blame", "--line-porcelain", "--", "src/auth.js"])
            return blame_output

        data = fetch_blame_data("src/auth.js", "/tmp", runner=mock_runner)

        self.assertEqual(data["analysisType"], "blame")
        self.assertEqual(data["displayRef"], "src/auth.js")
        self.assertEqual(data["commitMessage"], "Blame analysis for src/auth.js")
        self.assertEqual(data["stats"], "3 line annotations across 2 authors")
        self.assertIn("Authors:", data["diff"])
        self.assertIn("Alice", data["diff"])
        self.assertIn("Bob", data["diff"])
        self.assertIn("L2 | Bob", data["diff"])

    def test_fetch_commit_data_range(self):
        responses = {
            'diff HEAD~2..HEAD': 'diff --git a/a.js b/a.js',
            'diff --name-only HEAD~2..HEAD': 'a.js\nb.js',
            'diff --stat HEAD~2..HEAD': ' 2 files changed, 10 insertions(+), 2 deletions(-)',
            'log --reverse --pretty=format:%H%x1f%s%x1f%B HEAD~2..HEAD': '1234567\u001fFirst change\u001fBody one\n89abcde\u001fSecond change\u001fBody two'
        }

        def mock_runner(args, cwd):
            cmd = " ".join(args)
            return responses.get(cmd, "")

        data = fetch_commit_data("HEAD~2..HEAD", "/tmp", runner=mock_runner)

        self.assertEqual(data["analysisType"], "range")
        self.assertEqual(data["commitCount"], 2)
        self.assertEqual(data["filesChanged"], ["a.js", "b.js"])
        self.assertIn("First change", data["commitMessage"])

    def test_fetch_commit_data_for_file_single(self):
        responses = {
            'log -1 --pretty=format:%B abc123': 'Fix login crash',
            'diff abc123^! -- src/auth.js': 'diff --git a/src/auth.js b/src/auth.js',
            'show --pretty=format: --name-only abc123 -- src/auth.js': 'src/auth.js',
            'show --stat --oneline --format=%h %s abc123 -- src/auth.js': 'abc123 Fix login crash\n 1 file changed, 4 insertions(+), 1 deletion(-)',
            'log -1 --pretty=format:%s abc123': 'Fix login crash'
        }

        def mock_runner(args, cwd):
            cmd = " ".join(args)
            return responses.get(cmd, "")

        data = fetch_commit_data_for_file("abc123", "src/auth.js", "/tmp", runner=mock_runner)

        self.assertEqual(data["displayRef"], "abc123 :: src/auth.js")
        self.assertEqual(data["filesChanged"], ["src/auth.js"])
        self.assertIn("src/auth.js", data["diff"])

    def test_fetch_stash_data(self):
        responses = {
            'log -1 --pretty=format:%gs stash@{1}': 'WIP on main: abc1234 fix login crash',
            'stash show -p stash@{1}': 'diff --git a/src/auth.js b/src/auth.js',
            'stash show --name-only stash@{1}': 'src/auth.js',
            'stash show --stat stash@{1}': ' src/auth.js | 5 +++--\n 1 file changed, 3 insertions(+), 2 deletions(-)'
        }

        def mock_runner(args, cwd):
            cmd = " ".join(args)
            return responses.get(cmd, "")

        data = fetch_stash_data("stash@{1}", "/tmp", runner=mock_runner)

        self.assertEqual(data["analysisType"], "stash")
        self.assertEqual(data["displayRef"], "stash@{1}")
        self.assertEqual(data["commitMessage"], "WIP on main: abc1234 fix login crash")
        self.assertEqual(data["filesChanged"], ["src/auth.js"])

    def test_fetch_conflict_data(self):
        cwd = tempfile.mkdtemp()
        try:
            os.makedirs(os.path.join(cwd, "src"), exist_ok=True)
            with open(os.path.join(cwd, "src", "auth.js"), "w", encoding="utf-8") as f:
                f.write("\n".join([
                    "function resolve() {",
                    "<<<<<<< HEAD",
                    "  return currentValue;",
                    "=======",
                    "  return incomingValue;",
                    ">>>>>>> feature-branch",
                    "}"
                ]))

            def mock_runner(args, cwd_arg):
                if " ".join(args) == "diff --name-only --diff-filter=U":
                    return "src/auth.js"
                return ""

            data = fetch_conflict_data(cwd, runner=mock_runner)

            self.assertEqual(data["analysisType"], "conflict")
            self.assertEqual(data["displayRef"], "working-tree conflicts")
            self.assertEqual(data["filesChanged"], ["src/auth.js"])
            self.assertIn("Conflict 1 (src/auth.js:2-6)", data["diff"])
            self.assertIn("Current Side (HEAD):", data["diff"])
            self.assertIn("Incoming Side (feature-branch):", data["diff"])
        finally:
            shutil.rmtree(cwd, ignore_errors=True)

    def test_get_repository_log_defaults(self):
        calls = []
        def mock_runner(args, cwd):
            calls.append(" ".join(args))
            return "abc1234 2026-04-08 Guru Initial commit"

        log = get_repository_log("/tmp", runner=mock_runner)

        self.assertEqual(log, "abc1234 2026-04-08 Guru Initial commit")
        self.assertEqual(calls, ["log --reverse --date=short --pretty=format:%h %ad %an %s"])

    def test_get_repository_status_clean(self):
        def mock_runner(args, cwd):
            return "## main"

        status = get_repository_status("/tmp", runner=mock_runner)
        self.assertEqual(status, "main\n\nWorking tree is clean.")

    def test_resolve_stash_ref_valid(self):
        self.assertEqual(resolve_stash_ref(), "stash@{0}")
        self.assertEqual(resolve_stash_ref("2"), "stash@{2}")
        self.assertEqual(resolve_stash_ref(5), "stash@{5}")
        self.assertEqual(resolve_stash_ref("stash@{3}"), "stash@{3}")

    def test_resolve_stash_ref_invalid(self):
        with self.assertRaises(RuntimeError):
            resolve_stash_ref("-1")
        with self.assertRaises(RuntimeError):
            resolve_stash_ref("abc")

if __name__ == "__main__":
    unittest.main()
