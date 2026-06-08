import os
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from gx.cli import main, parse_args

class TestCLIRouting(unittest.TestCase):
    def test_parse_args_handles_commit_mode_and_overrides(self):
        parsed = parse_args([
            "gx",
            "HEAD~1",
            "--summary",
            "--provider",
            "groq",
            "--model",
            "llama-3.3-70b-versatile",
            "--clipboard",
            "--verbose"
        ])

        self.assertEqual(parsed["commitRef"], "HEAD~1")
        self.assertEqual(parsed["mode"], "summary")
        self.assertEqual(parsed["provider"], "groq")
        self.assertEqual(parsed["model"], "llama-3.3-70b-versatile")
        self.assertTrue(parsed["clipboard"])
        self.assertTrue(parsed["verbose"])

    def test_parse_args_handles_branch_analysis(self):
        parsed = parse_args(["gx", "--branch", "--review"])

        self.assertTrue(parsed["hasBranchFlag"])
        self.assertIsNone(parsed["branchBase"])
        self.assertEqual(parsed["mode"], "review")

    def test_parse_args_treats_native_subcommands_as_passthrough(self):
        parsed = parse_args(["gx", "branch", "-a"], {"gitSubcommands": {"branch", "checkout", "worktree"}})

        self.assertTrue(parsed["nativeGitCommand"])
        self.assertEqual(parsed["nativeGitArgs"], ["branch", "-a"])
        self.assertIsNone(parsed["commitRef"])

    def test_parse_args_treats_git_wrapper_as_passthrough(self):
        parsed = parse_args(["gx", "git", "worktree", "list"], {"gitSubcommands": {"worktree"}})

        self.assertTrue(parsed["nativeGitCommand"])
        self.assertEqual(parsed["nativeGitArgs"], ["worktree", "list"])
        self.assertIsNone(parsed["commitRef"])

    def test_parse_args_handles_help_and_install_hook(self):
        help_parsed = parse_args(["gx", "help"])
        self.assertTrue(help_parsed["help"])

        hook_parsed = parse_args(["gx", "install-hook", "post-commit"])
        self.assertTrue(hook_parsed["installHook"])
        self.assertEqual(hook_parsed["hookName"], "post-commit")

    def test_parse_args_handles_version_flag(self):
        parsed = parse_args(["gx", "--version"])

        self.assertTrue(parsed["version"])
        self.assertIsNone(parsed["commitRef"])

    def test_parse_args_handles_cost_and_interactive(self):
        parsed = parse_args(["gx", "HEAD", "--split", "--interactive", "--cost"])

        self.assertTrue(parsed["cost"])
        self.assertTrue(parsed["interactive"])

    def test_parse_args_handles_config_set(self):
        parsed = parse_args(["gx", "config", "set", "api-key", "secret-token", "--provider", "openai"])

        self.assertTrue(parsed["configCommand"])
        self.assertEqual(parsed["configAction"], "set")
        self.assertEqual(parsed["configKey"], "api-key")
        self.assertEqual(parsed["configValue"], "secret-token")
        self.assertEqual(parsed["provider"], "openai")
        self.assertIsNone(parsed["commitRef"])

    def test_parse_args_handles_cache_clear(self):
        parsed = parse_args(["gx", "cache", "clear"])

        self.assertTrue(parsed["configCommand"] is False and parsed["cacheCommand"] is True)
        self.assertEqual(parsed["cacheAction"], "clear")
        self.assertIsNone(parsed["commitRef"])

    def test_parse_args_handles_empty_invocation(self):
        parsed = parse_args(["gx"])

        self.assertFalse(parsed["help"])
        self.assertIsNone(parsed["commitRef"])
        self.assertIsNone(parsed["mode"])

    def test_parse_args_handles_split_execution_flags(self):
        parsed = parse_args(["gx", "HEAD", "--split", "--execute", "--dry-run"])

        self.assertEqual(parsed["commitRef"], "HEAD")
        self.assertEqual(parsed["mode"], "split")
        self.assertTrue(parsed["execute"])
        self.assertTrue(parsed["dryRun"])

    def test_parse_args_handles_no_cache_flag(self):
        parsed = parse_args(["gx", "HEAD", "--summary", "--no-cache"])

        self.assertEqual(parsed["commitRef"], "HEAD")
        self.assertTrue(parsed["noCache"])

    def test_parse_args_handles_blame_mode(self):
        parsed = parse_args(["gx", "--blame", "cli/index.js", "--markdown"])

        self.assertEqual(parsed["mode"], "blame")
        self.assertEqual(parsed["blameFile"], "cli/index.js")
        self.assertIsNone(parsed["commitRef"])
        self.assertEqual(parsed["format"], "markdown")

    def test_parse_args_handles_conflict_mode(self):
        parsed = parse_args(["gx", "--conflict", "--diff", "src/auth.js"])

        self.assertEqual(parsed["mode"], "conflict")
        self.assertEqual(parsed["diffFile"], "src/auth.js")
        self.assertIsNone(parsed["commitRef"])

    def test_parse_args_handles_stash_mode(self):
        parsed = parse_args(["gx", "--stash", "stash@{2}", "--diff", "cli/index.js"])

        self.assertEqual(parsed["mode"], "stash")
        self.assertEqual(parsed["stashRef"], "stash@{2}")
        self.assertEqual(parsed["diffFile"], "cli/index.js")
        self.assertIsNone(parsed["commitRef"])

    def test_parse_args_handles_diff_filtering(self):
        parsed = parse_args(["gx", "HEAD~1", "--summary", "--diff", "cli/index.js"])

        self.assertEqual(parsed["commitRef"], "HEAD~1")
        self.assertEqual(parsed["mode"], "summary")
        self.assertEqual(parsed["diffFile"], "cli/index.js")

    def test_parse_args_handles_changelog_and_pr(self):
        changelog_parsed = parse_args(["gx", "HEAD~5..HEAD", "--changelog"])
        self.assertEqual(changelog_parsed["mode"], "changelog")
        self.assertEqual(changelog_parsed["commitRef"], "HEAD~5..HEAD")

        pr_parsed = parse_args(["gx", "--branch", "main", "--pr-description"])
        self.assertEqual(pr_parsed["mode"], "pr-description")
        self.assertEqual(pr_parsed["branchBase"], "main")

    def test_parse_args_handles_refactor_and_test_suggest(self):
        refactor_parsed = parse_args(["gx", "HEAD", "--refactor"])
        self.assertEqual(refactor_parsed["mode"], "refactor")

        test_suggest_parsed = parse_args(["gx", "HEAD", "--test-suggest"])
        self.assertEqual(test_suggest_parsed["mode"], "test-suggest")

    def test_parse_args_handles_merge_flag(self):
        parsed = parse_args(["gx", "--merge", "--execute"])

        self.assertEqual(parsed["mode"], "merge")
        self.assertTrue(parsed["merge"])
        self.assertTrue(parsed["execute"])
        self.assertIsNone(parsed["commitRef"])

    def test_parse_args_treats_merge_subcommand_as_native(self):
        parsed = parse_args(["gx", "merge"])

        self.assertTrue(parsed["nativeGitCommand"])
        self.assertEqual(parsed["nativeGitArgs"], ["merge"])
        self.assertIsNone(parsed["commitRef"])

    def test_parse_args_handles_tag_flag(self):
        parsed = parse_args(["gx", "--tag", "--execute"])

        self.assertEqual(parsed["mode"], "tag")
        self.assertTrue(parsed["tag"])
        self.assertTrue(parsed["execute"])
        self.assertIsNone(parsed["commitRef"])

    def test_parse_args_treats_tag_subcommand_as_native(self):
        parsed = parse_args(["gx", "tag"])

        self.assertTrue(parsed["nativeGitCommand"])
        self.assertEqual(parsed["nativeGitArgs"], ["tag"])
        self.assertIsNone(parsed["commitRef"])

    def test_parse_args_handles_release_status(self):
        parsed = parse_args(["gx", "--release", "status"])

        self.assertTrue(parsed["releaseCommand"])
        self.assertEqual(parsed["releaseAction"], "status")
        self.assertIsNone(parsed["commitRef"])
        self.assertTrue(parsed["release"])

    def test_parse_args_treats_log_subcommand_as_native(self):
        parsed = parse_args(["gx", "log"])

        self.assertTrue(parsed["nativeGitCommand"])
        self.assertEqual(parsed["nativeGitArgs"], ["log"])
        self.assertFalse(parsed["log"])
        self.assertIsNone(parsed["commitRef"])

    def test_parse_args_handles_log_flag(self):
        parsed = parse_args(["gx", "--log"])

        self.assertTrue(parsed["log"])
        self.assertIsNone(parsed["commitRef"])
        self.assertEqual(parsed["mode"], "log")

    def test_parse_args_treats_status_subcommand_as_native(self):
        parsed = parse_args(["gx", "status"])

        self.assertTrue(parsed["nativeGitCommand"])
        self.assertEqual(parsed["nativeGitArgs"], ["status"])
        self.assertFalse(parsed["status"])
        self.assertIsNone(parsed["commitRef"])

    def test_parse_args_handles_status_flag(self):
        parsed = parse_args(["gx", "--status"])

        self.assertTrue(parsed["status"])
        self.assertIsNone(parsed["commitRef"])
        self.assertEqual(parsed["mode"], "status")

    def test_parse_args_treats_pipeline_subcommand_as_commit_ref(self):
        parsed = parse_args(["gx", "pipeline"])

        self.assertFalse(parsed["pipelineCommand"])
        self.assertEqual(parsed["commitRef"], "pipeline")
        self.assertFalse(parsed["nativeGitCommand"])

    def test_parse_args_handles_pipeline_flag(self):
        parsed = parse_args(["gx", "--pipeline"])

        self.assertTrue(parsed["pipelineCommand"])
        self.assertEqual(parsed["mode"], "pipeline")
        self.assertIsNone(parsed["commitRef"])

    @patch("gx.cli.inspect_repository_for_pipeline")
    def test_main_routes_pipeline_without_help(self, mock_inspect):
        import asyncio
        temp_dir = tempfile.mkdtemp()
        subprocess.run(["git", "init"], cwd=temp_dir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        mock_inspect.return_value = {
            "supported": False,
            "reason": "No supported project files detected.",
            "existingWorkflows": [],
            "options": []
        }

        with patch("os.getcwd", return_value=temp_dir), \
             patch("sys.stdout.write") as mock_stdout_write, \
             patch("builtins.print") as mock_print:
            result = main(["gx", "--pipeline"])
            self.assertEqual(result, 1)
            mock_print.assert_any_call("No supported project files detected.")

        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_parse_args_handles_add_command(self):
        parsed = parse_args(["gx", "add", "README.md", "cli/index.js"])

        self.assertTrue(parsed["addCommand"])
        self.assertEqual(parsed["actionPaths"], ["README.md", "cli/index.js"])
        self.assertIsNone(parsed["commitRef"])

    def test_parse_args_handles_remove_command(self):
        parsed = parse_args(["gx", "remove", "README.md"])

        self.assertTrue(parsed["removeCommand"])
        self.assertFalse(parsed["removeHardCommand"])
        self.assertEqual(parsed["actionPaths"], ["README.md"])
        self.assertIsNone(parsed["commitRef"])

    def test_parse_args_handles_remove_hard_command(self):
        parsed = parse_args(["gx", "remove", "hard"])

        self.assertTrue(parsed["removeCommand"])
        self.assertTrue(parsed["removeHardCommand"])
        self.assertEqual(parsed["actionPaths"], [])
        self.assertIsNone(parsed["commitRef"])

    def test_parse_args_handles_del_command(self):
        parsed = parse_args(["gx", "del", "scratch.txt"])

        self.assertTrue(parsed["deleteCommand"])
        self.assertEqual(parsed["actionPaths"], ["scratch.txt"])
        self.assertIsNone(parsed["commitRef"])

    def test_parse_args_handles_pop_command(self):
        parsed = parse_args(["gx", "pop", "2"])

        self.assertTrue(parsed["popCommand"])
        self.assertEqual(parsed["stashIndex"], "2")
        self.assertIsNone(parsed["commitRef"])

    def test_parse_args_handles_pop_command_no_index(self):
        parsed = parse_args(["gx", "pop"])

        self.assertTrue(parsed["popCommand"])
        self.assertIsNone(parsed["stashIndex"])
        self.assertIsNone(parsed["commitRef"])

    def test_parse_args_handles_push_command(self):
        parsed = parse_args(["gx", "push", "origin", "main"])

        self.assertTrue(parsed["pushCommand"])
        self.assertEqual(parsed["pushRemote"], "origin")
        self.assertEqual(parsed["pushBranch"], "main")
        self.assertIsNone(parsed["commitRef"])

    def test_parse_args_handles_bin_command(self):
        parsed = parse_args(["gx", "bin"])

        self.assertTrue(parsed["binCommand"])
        self.assertIsNone(parsed["commitRef"])

    def test_parse_args_handles_pull_command(self):
        parsed = parse_args(["gx", "pull", "origin", "main"])

        self.assertTrue(parsed["pullCommand"])
        self.assertEqual(parsed["pullRemote"], "origin")
        self.assertEqual(parsed["pullBranch"], "main")
        self.assertIsNone(parsed["commitRef"])

class TestCLIInteractive(unittest.TestCase):
    @patch("gx.cli.load_config")
    @patch("os.environ.get")
    def test_is_configured(self, mock_env, mock_config):
        from gx.cli import is_configured
        
        mock_config.return_value = {}
        mock_env.return_value = None
        self.assertFalse(is_configured("/dummy"))
        
        mock_config.return_value = {"provider": "ollama"}
        self.assertTrue(is_configured("/dummy"))
        
        mock_config.return_value = {"provider": "openai", "OPENAI_API_KEY": "sk-123"}
        self.assertTrue(is_configured("/dummy"))
        
        mock_config.return_value = {"provider": "openai"}
        self.assertFalse(is_configured("/dummy"))

    @patch("gx.cli.select_provider_interactive")
    @patch("getpass.getpass")
    @patch("gx.cli.select_model_interactive")
    @patch("gx.cli.ask_question")
    @patch("gx.cli.update_user_config")
    def test_run_config_wizard(self, mock_update, mock_ask, mock_select_model, mock_getpass, mock_select_provider):
        from gx.cli import run_config_wizard
        
        mock_select_provider.return_value = "openai"
        mock_getpass.return_value = "secret"
        mock_select_model.return_value = "gpt-4o-test"
        mock_ask.return_value = "no"
        
        run_config_wizard("/dummy")
        
        mock_update.assert_any_call({"provider": "openai"})
        mock_update.assert_any_call({"OPENAI_API_KEY": "secret"})
        mock_update.assert_any_call({"model": "gpt-4o-test"})

    @patch("gx.cli.get_key")
    @patch("gx.cli.animate_gx_logo")
    @patch("gx.cli.load_config")
    @patch("gx.cli.is_git_repository")
    def test_run_tui_exits_on_q(self, mock_is_repo, mock_config, mock_animate, mock_get_key):
        from gx.cli import run_tui
        import asyncio
        
        mock_is_repo.return_value = True
        mock_config.return_value = {"provider": "openai", "model": "gpt-4o"}
        mock_get_key.return_value = "q"
        
        loop = asyncio.get_event_loop()
        res = loop.run_until_complete(run_tui("/dummy"))
        
        self.assertEqual(res, 0)

if __name__ == "__main__":
    unittest.main()
