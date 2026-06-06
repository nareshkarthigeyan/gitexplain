# gitxplain

`gitxplain` is a Node.js CLI that analyzes Git commits, commit ranges, and branch diffs to generate structured, human-readable explanations with AI.

Supported providers:

- OpenAI
- Groq
- OpenRouter
- Gemini
- Ollama
- Chutes AI
- Anthropic
- Mistral
- Azure OpenAI

## Features

- Explains what a commit does, why it exists, and how the fix works
- Supports focused output modes like summary, issue, fix, impact, review, security, and line-by-line walkthroughs
- Supports blame summaries, changelog drafting, PR description drafting, refactor suggestions, and test suggestion modes
- Supports stash explanation and single-file diff deep dives
- Supports merge conflict analysis with suggested resolutions
- Supports cumulative token usage tracking and optional estimated cost reporting
- Supports interactive split-plan review before history is rewritten
- Supports AI-assisted commit splitting plans, with optional execution for the latest commit
- Supports release-branch merge previews driven by detected version bumps in diffs
- Supports automatic release tagging driven by the same version-bump detection used for release merges
- Supports release health status checks that show missing tags, unmerged version bumps, branch drift, and next steps
- Supports AI-assisted commit planning for uncommitted working tree changes
- Supports quick repository log output for full history inspection
- Supports repository-aware CI/CD workflow generation for GitHub Actions, GitLab CI, CircleCI, and Bitbucket Pipelines
- Supports single commits, commit ranges, and branch-vs-base comparisons
- Truncates oversized diffs before sending them to the model and reports that truncation
- Streams output for supported providers
- Caches responses locally to reduce repeat API costs
- Supports plain, JSON, Markdown, and HTML output
- Supports clipboard copy, verbosity controls, and hook installation
- Supports project-level and user-level config files
- Returns plain text or JSON output
- Uses native Node APIs only, so the MVP has no runtime dependencies

## Requirements

- Node.js 18+
- A Git repository in your current working directory
- An API key for your chosen provider, or a local Ollama instance

## Installation

Install from npm:

```bash
npm install -g gitxplain
```

Install from bun:

```bash
bun install -g gitxplain
```

Install with Homebrew:

```bash
brew tap guruswarupa/homebrew-tap
brew install gitxplain
```

Install from the AUR:

```bash
yay -S gitxplain
```

```bash
paru -S gitxplain
```

Install from a Debian package downloaded from GitHub Releases:

```bash
sudo apt install ./gitxplain_<version>_all.deb
```

Optional advanced environment variables:

- `LLM_PROVIDER` default: `openai`
- `LLM_MODEL` optional shared model override
- `OPENAI_API_KEY`, `OPENAI_MODEL`, `OPENAI_BASE_URL`
- `GROQ_API_KEY`, `GROQ_MODEL`, `GROQ_BASE_URL`
- `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`, `OPENROUTER_BASE_URL`
- `OPENROUTER_SITE_URL`, `OPENROUTER_APP_NAME`
- `GEMINI_API_KEY`, `GEMINI_MODEL`, `GEMINI_BASE_URL`
- `OLLAMA_API_KEY` optional, default: `ollama`
- `OLLAMA_MODEL`, `OLLAMA_BASE_URL` default: `http://127.0.0.1:11434/v1`
- `CHUTES_API_KEY`, `CHUTES_MODEL`, `CHUTES_BASE_URL`

Optional config files:

- Project: `.gitxplainrc` or `.gitxplainrc.json`
- User: `~/.gitxplain/config.json` on macOS/Linux, or `%USERPROFILE%\.gitxplain\config.json` on Windows

You can start from:

```bash
cp .env.example .env
```

## Quick Command Reference

All commands support both long-form flags (e.g., `--summary`) and short aliases (e.g., `-s`) for faster typing. Here are the most commonly used short aliases:

### Analysis Modes
- `-s` / `--summary` - One-line summary
- `-F` / `--full` - Full structured analysis  
- `-r` / `--review` - Code review findings
- `-S` / `--security` - Security analysis
- `-l` / `--lines` - Line-by-line walkthrough
- `-R` / `--refactor` - Refactoring suggestions
- `-t` / `--test-suggest` - Test suggestions
- `-p` / `--pr-description` - PR description
- `-c` / `--changelog` - Changelog notes
- `-i` / `--issues` - Issue-focused analysis
- `-f` / `--fix` - Simple explanation
- `-m` / `--impact` - Before/after impact
- `-b` / `--blame` - File ownership analysis
- `-C` / `--conflict` - Merge conflict resolution
- `-Z` / `--stash` - Stash explanation
- `-x` / `--split` - Commit splitting

### Workflow Commands
- `-k` / `--commit` - Plan commits for changes
- `-g` / `--merge` - Release merge
- `-T` / `--tag` - Release tagging
- `-e` / `--release` - Release status
- `-E` / `--execute` - Execute plan
- `-d` / `--dry-run` - Preview without executing
- `-I` / `--interactive` - Interactive review

### Output Options
- `-j` / `--json` - JSON output
- `-M` / `--markdown` - Markdown output
- `-H` / `--html` - HTML output
- `-q` / `--quiet` - Quiet mode
- `-v` / `--verbose` - Verbose mode
- `-y` / `--clipboard` - Copy to clipboard
- `-z` / `--stream` - Stream output
- `-n` / `--no-cache` - Bypass cache
- `-o` / `--cost` - Show cost

### Repository & Comparison
- `-L` / `--log` - Repository log
- `-u` / `--status` - Repository status
- `-V` / `--pipeline` - CI/CD pipeline generation
- `-B` / `--branch` - Branch comparison
- `-P` / `--pr` - PR-style comparison
- `-D` / `--diff` - File-specific diff
- `-w` / `--provider` - AI provider
- `-O` / `--model` - AI model
- `-X` / `--max-diff-lines` - Diff line limit

## Usage

Show the built-in command reference.

```bash
gitxplain --help
```

Inspect cache usage or clear cached responses.

```bash
gitxplain cache stats
gitxplain cache clear
```

Show cumulative token usage and estimated cost totals.

```bash
gitxplain --cost
```

Save the default AI provider.

```bash
gitxplain config set provider <name>
```

Save the API key for a provider.

```bash
gitxplain config set api-key <value> [--provider <name>]
```

Print one saved config value, or all of them.

```bash
gitxplain config get [key]
```

List saved user config values.

```bash
gitxplain config list
```

Analyze a single commit.

```bash
gitxplain <commit-id> [options]
```

Analyze a commit range.

```bash
gitxplain <start>..<end> [options]
```

Compare the current branch to a base branch.

```bash
gitxplain --branch [base-ref] [options]
```

Compare the current branch like a PR.

```bash
gitxplain --pr [base-ref] [options]
```

Plan commits for uncommitted working tree changes.

```bash
gitxplain --commit
```

Show release branch health and next steps.

```bash
gitxplain --release [status]
```

Preview or execute a release merge.

```bash
gitxplain --merge
```

Preview or create release tags.

```bash
gitxplain --tag
```

Explain the latest stash, or a specific stash entry.

```bash
gitxplain --stash
gitxplain --stash stash@{2}
```

Print repository log output.

```bash
gitxplain --log
```

Print repository status output.

```bash
gitxplain --status
```

Detect and generate CI/CD workflow files.

```bash
gitxplain --pipeline
```

Analyze unresolved merge conflicts in the working tree.

```bash
gitxplain --conflict
gitxplain --conflict --diff src/auth.js
```

Install a git hook for commit, merge, or push workflows.

```bash
gitxplain install-hook
gitxplain install-hook post-merge
gitxplain install-hook pre-push
```

Analysis:

Generate a one-line summary.

```bash
-s, --summary
```

Focus on the issue being fixed.

```bash
-i, --issues
```

Explain the fix in simple terms.

```bash
-f, --fix
```

Explain behavior changes before vs after.

```bash
-m, --impact
```

Generate the full structured analysis.

```bash
-F, --full
```

Walk through the changed code file by file.

```bash
-l, --lines
```

Generate review findings and risks.

```bash
-r, --review
```

Focus on security-relevant changes.

```bash
-S, --security
```

Suggest refactoring follow-ups.

```bash
-R, --refactor
```

Suggest tests to add or update.

```bash
-t, --test-suggest
```

Generate a PR description.

```bash
-p, --pr-description
```

Generate changelog-style notes.

```bash
-c, --changelog
```

Analyze file ownership with git blame.

```bash
-b, --blame <file>
```

Suggest resolutions for unresolved merge conflicts.

```bash
-C, --conflict
```

Explain a stash entry.

```bash
-Z, --stash [ref]
```

Focus analysis on one changed file.

```bash
-D, --diff <file>
```

Propose splitting a commit into smaller commits.

```bash
-x, --split
```

Propose commits for current working tree changes.

```bash
-k, --commit
```

Apply a split, commit, merge, or tag plan.

```bash
-E, --execute
```

Preview a plan without applying it.

```bash
-d, --dry-run
```

Review or edit a split plan before execution.

```bash
-I, --interactive
```

Release:

Show release status details.

```bash
-e, --release [status]
```

Preview or apply a merge into the release branch.

```bash
-g, --merge
```

Preview or create release tags from version bumps.

```bash
-T, --tag
```

Repo:

Print the current repository log.

```bash
-L, --log
```

Print the current working tree status.

```bash
-u, --status
```

Inspect the repo and create CI/CD workflow files.

```bash
-V, --pipeline
```

Quick Actions:

Persist provider, model, and API key settings.

```bash
config
```

Stage one or more files.

```bash
add
```

Unstage one or more files.

```bash
remove
```

Hard reset the repository to HEAD.

```bash
remove hard
```

Delete one or more files from the working tree.

```bash
del
```

Soft reset `HEAD~1` and keep your changes.

```bash
bin
```

Pop a stash entry.

```bash
pop
```

Run `git pull`.

```bash
pull
```

Run `git push`.

```bash
push
```

Install the `gitxplain` hook.

```bash
install-hook
```

Pass through to native Git commands.

```bash
git
```

Output:

Override the configured provider for one command.

```bash
-w, --provider <name>
```

Override the configured model for one command.

```bash
-O, --model <name>
```

Return JSON output.

```bash
-j, --json
```

Return Markdown output.

```bash
-M, --markdown
```

Return HTML output.

```bash
-H, --html
```

Reduce extra console output.

```bash
-q, --quiet
```

Show extra response metadata.

```bash
-v, --verbose
```

Copy the final output to the clipboard.

```bash
-y, --clipboard
```

Stream model output as it arrives.

```bash
-z, --stream
```

Bypass cached responses for one command.

```bash
-n, --no-cache
```

Show cumulative token usage and estimated cost totals.

```bash
-o, --cost
```

Limit diff size before sending it to the model.

```bash
-X, --max-diff-lines <n>
```

## Running The CLI

To use the actual `gitxplain` command directly:

```bash
npm link
```

Run that from the repository root. `npm link` works on Windows, macOS, and Linux, though it may require elevated privileges depending on your Node/npm install prefix.

Then from any Git repository:

```bash
gitxplain --help
gitxplain HEAD~1 --full
gitxplain a1b2c3d --summary
gitxplain HEAD~1 --lines
gitxplain HEAD~5..HEAD --markdown
gitxplain --branch main --review
gitxplain --branch main --pr-description
gitxplain HEAD~10..HEAD --changelog
gitxplain HEAD --refactor
gitxplain HEAD --test-suggest
gitxplain --blame cli/index.js
gitxplain --conflict
gitxplain --stash
gitxplain HEAD~5..HEAD --lines --diff cli/index.js
gitxplain --cost
gitxplain HEAD --split --interactive --execute
gitxplain install-hook post-merge
```

If you do not want to link it globally, you can still run it locally:

```bash
node ./cli/index.js HEAD~1 --full
```

## Quick Examples with Short Aliases

Using short aliases can significantly speed up your workflow:

```bash
# Quick summary of last commit
gitxplain HEAD -s

# Full analysis with JSON output
gitxplain HEAD~1 -F -j

# Security review of current branch vs main
gitxplain -B main -S

# Plan commits for current changes
gitxplain -k

# Show repository status
gitxplain -u

# Generate PR description for branch
gitxplain -B main -p -M

# Split last commit interactively
gitxplain HEAD -x -I -E

# Check release status
gitxplain -e status

# Review with cost tracking
gitxplain HEAD~1 -r -o
```

## Output Modes

- `-s, --summary`: one-sentence commit summary
- `-i, --issues`: bug or issue-oriented analysis
- `-f, --fix`: junior-friendly explanation of the fix
- `-m, --impact`: before-vs-after explanation focused on behavior changes
- `-F, --full`: full structured analysis
- `-l, --lines`: file-by-file, line-by-line walkthrough of the changed code
- `-r, --review`: code review findings with actionable suggestions
- `-S, --security`: security-focused analysis of the change
- `-R, --refactor`: suggest maintainability-focused refactors visible in the change
- `-t, --test-suggest`: suggest the most valuable tests to add or update
- `-p, --pr-description`: draft a ready-to-paste pull request description
- `-c, --changelog`: generate changelog-style release notes from the change set
- `-b, --blame <file>`: summarize ownership and change history for one file using `git blame`
- `-C, --conflict`: inspect unresolved merge conflicts and suggest likely resolutions
- `-Z, --stash [ref]`: explain what is stored in a stash entry, defaulting to `stash@{0}`
- `-D, --diff <file>`: focus commit or range analysis on a single file
- `-x, --split`: propose how to split a commit into multiple atomic commits
- `-I, --interactive`: review or edit a split plan before executing it
- `-o, --cost`: show cumulative token usage and estimated cost totals
- `-g, --merge`: preview or execute a merge into the `release` branch based on detected version bumps
- `-T, --tag`: preview or create release tags from the same detected version windows
- `-e, --release [status]`: inspect release branch health, missing tags, source-vs-release drift, and the next recommended action
- `-k, --commit`: propose commits for current uncommitted changes
- `-L, --log`: print Git log entries for the current repository
- `-u, --status`: print Git working tree status for the current repository
- `-V, --pipeline`: inspect the current repository and generate GitHub Actions, GitLab CI, CircleCI, or Bitbucket Pipelines config
- `-E, --execute`: apply a proposed split by rewriting history
- `-d, --dry-run`: preview the split or commit plan without applying it
- `-j, --json`: return structured JSON instead of formatted text
- `-M, --markdown`: return Markdown output
- `-H, --html`: return HTML output

## Repository Log

Print recent log entries from the current repository:

```bash
gitxplain --log
```

This prints the repository history in a compact one-line format using the current repository, without calling the LLM.

## Quick Actions

Run a few common Git actions directly through `gitxplain`:

```bash
gitxplain --status
gitxplain cache stats
gitxplain cache clear
gitxplain --cost
gitxplain add README.md
gitxplain remove README.md
gitxplain remove hard
gitxplain del scratch.txt
gitxplain bin
gitxplain pop
gitxplain pop 2
gitxplain pull
gitxplain pull origin main
gitxplain push
gitxplain push origin main
```

For native Git commands that do not have a custom `gitxplain` workflow, use them directly:

```bash
gitxplain branch -a
gitxplain checkout -b feature/demo
gitxplain rebase origin/main
gitxplain worktree list
```

If you want to force native Git for a reserved custom command name, use the `git` wrapper:

```bash
gitxplain git commit -m "native commit message"
gitxplain git merge feature/demo
gitxplain git tag -a v1.2.3 -m "release"
```

## Comparison Modes

Single commit:

```bash
gitxplain HEAD~1 --full
```

Commit range:

```bash
gitxplain HEAD~5..HEAD --markdown
```

Branch or PR-style comparison:

```bash
gitxplain --branch main --review
gitxplain --pr origin/main --security
```

`--branch` and `--pr` compare the current branch to a base ref using the merge base with `HEAD`.

## Commit Splitting

Preview how a commit could be split:

```bash
gitxplain HEAD~1 --split
```

Actually split the current `HEAD` commit into smaller commits:

```bash
gitxplain HEAD --split --execute
```

Review the plan interactively before executing it:

```bash
gitxplain HEAD --split --interactive --execute
```

Use a specific provider for the analysis:

```bash
gitxplain HEAD --split --provider gemini
```

`--split` asks the model for a plan first. By default this is a dry run and only prints the proposed commit breakdown. Adding `--execute` rewrites Git history by undoing the current `HEAD` commit and recreating it as multiple commits in the suggested order. Adding `--interactive` lets you keep, edit, skip, or abort individual split groups before the rewrite happens.

Warning: `--split --execute` rewrites history. If the commit was already pushed, you may need to force-push after reviewing the new commit stack. For safety, execution only supports splitting the current `HEAD` commit and requires a clean working tree.

## Release Merge

Preview the release merge plan for the current branch:

```bash
gitxplain --merge
```

Actually merge the current branch into the `release` branch:

```bash
gitxplain --merge --execute
```

This command scans commits on your current branch after the branch split point and uses version-file diffs as release checkpoints. Each time a commit changes the version, that closes a release window. On the `release` branch, the command creates commits named `release <version>`. If no release versions have been promoted yet, it creates release commits for all detected versions in order. If some release versions already exist on `release`, it skips those and creates only the latest unreleased `release <version>` commit.

## Release Tagging

Preview the release tags for the current branch:

```bash
gitxplain --tag
gitxplore --tag
```

Actually create the tags:

```bash
gitxplain --tag --execute
gitxplore --tag --execute
```

This command scans the full history of your current branch, detects version bumps from version-file diffs, and maps each untagged detected version to the last commit in that version window. It works independently from the `merge` workflow and does not require a `release` branch. By default it creates annotated tags named exactly after the detected version, such as `1.2.3`.

## Commit Working Tree

Preview how the current uncommitted changes should be committed:

```bash
gitxplain --commit
```

Actually create the suggested commits:

```bash
gitxplain --commit --execute
```

Use a specific provider for the analysis:

```bash
gitxplain --commit --provider gemini
```

This mode analyzes the current working tree, proposes one or more logical commits with conventional commit messages, and can then create those commits automatically. By default it only previews the plan.

## Config File

Example `.gitxplainrc`:

```json
{
  "provider": "groq",
  "model": "llama-3.3-70b-versatile",
  "mode": "full",
  "format": "markdown",
  "maxDiffLines": 600,
  "stream": true,
  "verbose": false
}
```

CLI flags still override config values for a single command.

You can also save provider settings permanently with the CLI:

```bash
gitxplain config set provider openai
gitxplain config set api-key your_key
gitxplain config set model gpt-4.1-mini
gitxplain config list
```

## Clipboard, Streaming, Cost, And Hooks

Copy the final output to your clipboard:

```bash
gitxplain HEAD~1 --markdown --clipboard
```

Stream long responses as they arrive:

```bash
gitxplain HEAD~1 --full --stream
```

Show cumulative usage and estimated cost totals:

```bash
gitxplain --cost
```

Install a post-commit hook that saves a Markdown explanation under `.git/gitxplain/last-explanation.md`:

```bash
gitxplain install-hook
```

Install a post-merge hook that explains the new `HEAD` after merges:

```bash
gitxplain install-hook post-merge
```

Install a pre-push hook that runs a security-oriented review:

```bash
gitxplain install-hook pre-push
```

## Provider Setup

Recommended persistent setup:

```bash
gitxplain config set provider openai
gitxplain config set api-key your_key
```

You can also save a default model:

```bash
gitxplain config set model gpt-4.1-mini
```

You can switch providers later:

```bash
gitxplain config set provider groq
gitxplain config set api-key your_key
```

Additional supported providers:

```bash
gitxplain config set provider anthropic
gitxplain config set api-key your_key

gitxplain config set provider mistral
gitxplain config set api-key your_key

gitxplain config set provider azure-openai
gitxplain config set api-key your_key
```

Azure OpenAI also requires endpoint configuration:

```bash
export AZURE_OPENAI_BASE_URL="https://your-resource.openai.azure.com"
export AZURE_OPENAI_DEPLOYMENT="your-deployment-name"
export AZURE_OPENAI_API_VERSION="2024-10-21"
```

Optional token pricing env vars for estimated cost tracking:

```bash
export OPENAI_INPUT_COST_PER_MTOK="0.15"
export OPENAI_OUTPUT_COST_PER_MTOK="0.60"
```

Or use generic pricing defaults across providers:

```bash
export LLM_INPUT_COST_PER_MTOK="0.15"
export LLM_OUTPUT_COST_PER_MTOK="0.60"
```

If you want to inspect what is saved:

```bash
gitxplain config list
gitxplain config get provider
```

Saved user settings live in `~/.gitxplain/config.json` on macOS/Linux, or `%USERPROFILE%\.gitxplain\config.json` on Windows.

## Development

```bash
npm run lint
npm test
```

To make the command globally available during local development:

```bash
npm link
```

Run this from the repository root. On some systems, you may need an elevated shell depending on where npm installs global links.
