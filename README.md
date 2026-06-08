# gx

`gx` (with `gitxplain` compatibility) is a Python CLI that analyzes Git commits, commit ranges, and branch diffs to generate structured, human-readable explanations with AI.

It features a beautiful keyboard-driven animated Terminal User Interface (TUI) and configuration wizard, letting you manage your git workflow and review changes with style.

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

- **TUI Dashboard**: Selectable using Up/Down Arrow keys and Enter to run summaries, reviews, history search, etc.
- **Commit Analysis**: Explains what a commit does, why it exists, and how the fix works.
- **Output Modes**: Focused modes like summary (`-s`), issue (`-i`), fix (`-f`), impact (`-m`), review (`-r`), security (`-S`), and line-by-line walkthroughs (`-l`).
- **Additional Diagnostics**: Blame summaries, changelog drafting, PR description drafting, refactor suggestions, and test suggestion modes.
- **Merge Conflicts & Stashes**: Explains unresolved merge conflicts with suggested resolutions, and stash entries.
- **Interactive Commit Splitter**: AI-assisted plans to split large commits into atomic ones, reviewable interactively.
- **Commit Planner**: Automatically groups uncommitted working tree changes and plans commit batches.
- **CI/CD Pipeline Generator**: Generates repository-aware pipeline configs for GitHub Actions, GitLab CI, CircleCI, and Bitbucket.
- **Semantic & Pattern Search**: Run semantic or grep-style search across repository commits.
- **Hooks**: Easy installation of post-commit, post-merge, and pre-push hook integrations.
- **Local Cache & Cost Tracking**: Estimates usage costs and caches results locally.

## Requirements

- Python 3.8+
- A Git repository in your current working directory
- An API key for your chosen provider, or a local Ollama instance

## Installation

Install from PyPI using pip:

```bash
pip install gx
```

After installation, you can use either `gx` or the alias `gitxplain`:

```bash
gx HEAD -s
```

Install with Homebrew:

```bash
brew tap guruswarupa/homebrew-tap
brew install gx
```

Install from the AUR:

```bash
yay -S gx
```

Install from a Debian package downloaded from GitHub Releases:

```bash
sudo apt install ./gx_<version>_all.deb
```

## Interactive TUI Dashboard

Running the base command without arguments launches the **GX Interactive TUI**:

```bash
gx
```

- Features a colorful animated gradient logo on startup.
- Navigate the options using the **Arrow keys (Up/Down)** and press **Enter** to execute.
- Direct quick shortcuts via keys `1`-`9` or exit with `q`/`escape`.
- If not configured, launches the interactive configuration wizard automatically.

## Configuration Wizard

Run the configuration wizard to select your provider, securely enter your API keys (hidden output), and select recommended models or customize endpoints:

```bash
gx config
```
*(Or select Option 7 inside the TUI dashboard).*

### Optional Config Files
- **Project**: `.gxrc` or `.gxrc.json` (falls back to `.gitxplainrc` / `.gitxplainrc.json`)
- **User**: `~/.gx/config.json` (falls back to `~/.gitxplain/config.json`)

## Quick Command Reference

All commands support both long-form flags (e.g., `--summary`) and short aliases (e.g., `-s`).

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
- `-b` / `--blame` <file> - File ownership analysis
- `-C` / `--conflict` - Merge conflict resolution
- `-Z` / `--stash` [ref] - Stash explanation
- `-x` / `--split` - Commit splitting
- `-A` / `--performance` - Performance analysis
- `-Q` / `--database` - Database schema and query analysis
- `-G` / `--docs` - Documentation analysis
- `-Y` / `--api-docs` - API documentation generation
- `-J` / `--coverage` - Test coverage analysis
- `-K` / `--mutation` - Mutation testing targets

### Workflow Commands
- `-k` / `--commit` - Plan commits for changes (also: `--com`, `--plan`)
- `-g` / `--merge` - Release merge (also: `--mrg`, `--mg`)
- `-T` / `--tag` - Release tagging (also: `--tg`)
- `-e` / `--release` - Release status (also: `--rel`, `--rl`)
- `-E` / `--execute` - Execute plan (also: `--exe`, `--run`)
- `-d` / `--dry-run` - Preview without executing (also: `--dry`, `--prev`)
- `-I` / `--interactive` - Interactive review (also: `--int`, `--edit`)

### Output Options
- `-j` / `--json` - JSON output
- `-M` / `--markdown` - Markdown output (also: `--md`)
- `-H` / `--html` - HTML output
- `-q` / `--quiet` - Quiet mode (also: `--silent`)
- `-v` / `--verbose` - Verbose mode (also: `--verb`, `--vv`)
- `-y` / `--clipboard` - Copy to clipboard (also: `--clip`, `--copy`)
- `-z` / `--stream` - Stream output (also: `--str`)
- `-n` / `--no-cache` - Bypass cache (also: `--noc`, `--fresh`)
- `-o` / `--cost` - Show cost

## Development

To run the unit tests:

```bash
python3 -m unittest discover -s tests -p "*.py"
```

To install local development dependencies:

```bash
pip install -r requirements.txt
```
