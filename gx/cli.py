import os
import sys
from typing import Any, Dict, List, Optional, Set, Tuple

# Load version
from gx import __version__ as CLI_VERSION
from .services.color import ANSI, colorize
from .services.env import load_env_file
from .services.config import (
    apply_config_environment,
    get_provider_api_key_field,
    get_user_config_path,
    load_config,
    load_user_config,
    update_user_config
)
from .services.cache import clear_cache, get_cache_stats
from .services.usage import get_usage_stats, clear_usage_log
from .services.clipboard import copy_to_clipboard
from .services.git import (
    build_branch_range,
    delete_paths,
    fetch_blame_data,
    fetch_commit_data,
    fetch_commit_data_for_file,
    fetch_conflict_data,
    fetch_stash_data,
    fetch_working_tree_data,
    git_add_files,
    git_pull,
    git_push,
    git_reset_hard,
    git_reset_soft,
    git_restore_staged,
    get_repository_log,
    get_repository_status,
    get_default_base_ref,
    is_git_repository,
    list_git_subcommands,
    run_native_git_passthrough,
    resolve_stash_ref
)
from .services.hook import install_hook
from .services.ai import generate_explanation
from .services.output import (
    format_footer,
    format_html_output,
    format_json_output,
    format_markdown_output,
    format_output,
    format_preamble
)
from .services.pipeline import (
    format_pipeline_recommendations,
    inspect_repository_for_pipeline,
    resolve_pipeline_selection,
    write_pipeline_files
)
from .services.commit import (
    execute_commit_plan,
    format_commit_plan,
    parse_commit_plan,
    reconcile_commit_plan
)
from .services.split import (
    execute_split,
    format_split_plan,
    parse_split_plan,
    reconcile_split_plan,
    validate_split_execution_target
)
from .services.merge import (
    build_release_merge_plan,
    build_release_status,
    build_release_tag_plan,
    execute_release_merge,
    execute_release_tag_plan,
    finalize_release_merge_plan,
    finalize_release_tag_plan,
    format_release_merge_plan,
    format_release_status,
    format_release_tag_plan
)
from .services.search import (
    semantic_search,
    pattern_search,
    code_pattern_search,
    author_activity_timeline
)

MODE_FLAGS = {
    "--summary": "summary",
    "--issues": "issues",
    "--fix": "fix",
    "--impact": "impact",
    "--full": "full",
    "--lines": "lines",
    "--review": "review",
    "--security": "security",
    "--refactor": "refactor",
    "--test-suggest": "test-suggest",
    "--pr-description": "pr-description",
    "--changelog": "changelog",
    "--blame": "blame",
    "--conflict": "conflict",
    "--stash": "stash",
    "--split": "split",
    "--merge": "merge",
    "--tag": "tag",
    "--commit": "commit",
    "--release": "release",
    "--log": "log",
    "--status": "status",
    "--pipeline": "pipeline",
    "--performance": "performance",
    "--database": "database",
    "--docs": "docs",
    "--api-docs": "api-docs",
    "--coverage": "coverage",
    "--mutation": "mutation"
}

SHORT_ALIASES = {
    # Analysis modes
    "-s": "--summary",
    "--sum": "--summary",
    "-i": "--issues",
    "--iss": "--issues",
    "-f": "--fix",
    "-m": "--impact",
    "--imp": "--impact",
    "-F": "--full",
    "-l": "--lines",
    "--lin": "--lines",
    "-r": "--review",
    "--rev": "--review",
    "-S": "--security",
    "--sec": "--security",
    "-R": "--refactor",
    "--ref": "--refactor",
    "-t": "--test-suggest",
    "--test": "--test-suggest",
    "-p": "--pr-description",
    "--pr": "--pr-description",
    "-c": "--changelog",
    "--ch": "--changelog",
    "-b": "--blame",
    "--bla": "--blame",
    "-C": "--conflict",
    "--con": "--conflict",
    "-Z": "--stash",
    "--sta": "--stash",
    "-x": "--split",
    "--spl": "--split",
    # New Analysis Modes
    "-A": "--performance",
    "--perf": "--performance",
    "-Q": "--database",
    "--db": "--database",
    "-G": "--docs",
    "-Y": "--api-docs",
    "--api": "--api-docs",
    "-J": "--coverage",
    "--cov": "--coverage",
    "-K": "--mutation",
    "--mut": "--mutation",
    # Workflow
    "-k": "--commit",
    "--com": "--commit",
    "--plan": "--commit",
    "-g": "--merge",
    "--mrg": "--merge",
    "--mg": "--merge",
    "-T": "--tag",
    "--tg": "--tag",
    "-e": "--release",
    "--rel": "--release",
    "--rl": "--release",
    "-E": "--execute",
    "--exe": "--execute",
    "--run": "--execute",
    "-d": "--dry-run",
    "--dry": "--dry-run",
    "--prev": "--dry-run",
    "-I": "--interactive",
    "--int": "--interactive",
    "--edit": "--interactive",
    # Output
    "-j": "--json",
    "--json": "--json",
    "-M": "--markdown",
    "--md": "--markdown",
    "-H": "--html",
    "-q": "--quiet",
    "--silent": "--quiet",
    "-v": "--verbose",
    "--verb": "--verbose",
    "--vv": "--verbose",
    "-y": "--clipboard",
    "--clip": "--clipboard",
    "--copy": "--clipboard",
    "-z": "--stream",
    "--str": "--stream",
    "-n": "--no-cache",
    "--noc": "--no-cache",
    "--fresh": "--no-cache",
    "-o": "--cost",
    # Comparison & repo
    "-D": "--diff",
    "--dif": "--diff",
    "-B": "--branch",
    "--br": "--branch",
    "--branch-named": "--branch",
    "-P": "--pr",
    "--pull-request": "--pr",
    "-L": "--log",
    "--log": "--log",
    "--lg": "--log",
    "-u": "--status",
    "--stat": "--status",
    "-st": "--status",
    "-V": "--pipeline",
    "--pipe": "--pipeline",
    "--ci": "--pipeline",
    # Search
    "--src": "--search",
    "-a": "--author",
    "--from": "--since",
    "-S": "--since",
    "--to": "--until",
    "-U": "--until",
    "-L": "--limit",
    "--pat": "--pattern",
    "-T": "--file-type",
    "--type": "--file-type",
    "-G": "--granularity",
    # Search action shortcuts
    "--sm": "semantic",
    "--sp": "pattern",
    "--sc": "code",
    "--sl": "timeline",
    "-sm": "semantic",
    "-sp": "pattern",
    "-sc": "code",
    "-sl": "timeline",
    # Provider
    "-w": "--provider",
    "--prov": "--provider",
    "-W": "--provider",
    "-O": "--model",
    "--mod": "--model",
    "--mo": "--model",
    # Other
    "-X": "--max-diff-lines",
    "--max": "--max-diff-lines",
    "--limit": "--max-diff-lines"
}

FORMAT_FLAGS = {
    "--json": "json",
    "--markdown": "markdown",
    "--html": "html"
}

ANALYSIS_MODES = {
    "summary",
    "issues",
    "fix",
    "impact",
    "full",
    "lines",
    "review",
    "security",
    "refactor",
    "test-suggest",
    "pr-description",
    "changelog",
    "blame",
    "conflict",
    "stash",
    "split",
    "performance",
    "database",
    "docs",
    "api-docs",
    "coverage",
    "mutation"
}

RESERVED_SUBCOMMANDS = {
    "help",
    "cache",
    "config",
    "install-hook",
    "git",
    "add",
    "remove",
    "del",
    "bin",
    "pop",
    "pull",
    "push",
    "search",
    "find"
}

def expand_aliases(args: List[str]) -> List[str]:
    expanded = []
    for arg in args:
        if "=" in arg:
            flag, *val_parts = arg.split("=")
            val = "=".join(val_parts)
            expanded_flag = SHORT_ALIASES.get(flag, flag)
            expanded.append(f"{expanded_flag}={val}")
        else:
            expanded.append(SHORT_ALIASES.get(arg, arg))
    return expanded

def print_help() -> None:
    print(f"""gx - AI-powered Git change analysis, review, and commit workflow CLI

Usage:
  gitxplain --help
  gx --help
  gitxplain --version
  gitxplain cache clear
  gitxplain cache stats
  gitxplain --cost
  gitxplain install-hook [post-commit|post-merge|pre-push]
  gitxplain config set provider <name>
  gitxplain config set api-key <value> [--provider <name>]
  gitxplain config get [key]
  gitxplain config list
  gitxplain <commit-id> [options]
  gitxplain <start>..<end> [options]
  gitxplain --branch [base-ref] [options]
  gitxplain --pr [base-ref] [options]
  gitxplain --commit
  gitxplain --release [status]
  gitxplain --merge
  gitxplain --tag
  gitxplain --conflict
  gitxplain --stash [stash-ref]
  gitxplain --log
  gitxplain --status
  gitxplain --pipeline
  gitxplain search <semantic|pattern|code|timeline> "<query>" [options]
  gitxplain find <semantic|pattern|code|timeline> "<query>" [options]

Analysis:
  -s, --summary       Generate a one-line summary of a change
  -i, --issues        Focus on the issue or failure being addressed
  -f, --fix           Explain the fix in simple terms
  -m, --impact        Explain behavior changes before vs after
  -F, --full          Generate a full structured analysis
  -l, --lines         Walk through the changed code file by file
  -r, --review        Generate review findings, risks, and suggestions
  -S, --security      Focus on security-relevant changes and concerns
  -R, --refactor      Suggest refactoring opportunities in the change
  -t, --test-suggest  Suggest tests to add or update for the change
  -p, --pr-description Generate a ready-to-paste PR description
  -c, --changelog     Generate changelog-style release notes
  -b, --blame <file>  Analyze ownership and history for one file with git blame
  -C, --conflict      Suggest resolutions for unresolved merge conflicts in the working tree
  -Z, --stash [ref]   Explain a stash entry, defaulting to stash@{{0}}
  -x, --split         Propose splitting a commit into smaller atomic commits
  -A, --performance   Analyze performance implications of changes
  -Q, --database      Focus on database schema changes and query optimizations
  -G, --docs          Identify missing or outdated documentation
  -Y, --api-docs      Generate API documentation updates from code changes
  -J, --coverage      Analyze test coverage implications of changes
  -K, --mutation      Suggest mutation testing targets based on changed code
  -o, --cost          Show cumulative token usage and estimated cost totals
  -k, --commit        Propose commits for current uncommitted changes (also: --com, --plan)
  -E, --execute       Execute a proposed split or commit plan (also: --exe, --run)
  -d, --dry-run       Preview the plan without executing it (also: --dry, --prev)
  -I, --interactive   Review or edit a split plan before execution (also: --int, --edit)

Release:
  -e, --release [status]  Show release branch health and next recommended action (also: --rel, --rl)
  -g, --merge         Preview or apply a merge into the release branch (also: --mrg, --mg)
  -T, --tag           Preview or create release tags from version bumps (also: --tg)

Repo:
  -L, --log           Print Git log entries for the current repository (also: --lg)
  -u, --status        Print Git working tree status for the current repository (also: --stat, -st)
  -V, --pipeline      Detect the current repository stack and create GitHub/GitLab/CircleCI/Bitbucket CI files (also: --pipe, --ci)

Quick Actions:
  config          Persist provider, model, and API key settings
  add             Stage one or more files with git add
  remove          Unstage one or more files with git restore --staged
  remove hard     Hard reset the repository to HEAD
  del             Delete one or more files from the working tree
  bin             Soft reset HEAD~1 while keeping your changes
  pop             Pop a stash entry like "pop 2"
  pull            Run git pull, optionally with a remote and branch
  push            Run git push, optionally with a remote and branch
  search/find     Search commits by semantic, pattern, code, or timeline
  install-hook    Install a post-commit, post-merge, or pre-push gitxplain hook
  cache           Manage gitxplain cache entries
  git             Pass through to native git commands

Output:
  -w, -W, --provider <name>
  -O, --mod, --mo, --model <name>
  -j, --json
  -M, --md, --markdown
  -H, --html
  -q, --silent, --quiet
  -v, --verb, --vv, --verbose
  -y, --clip, --copy, --clipboard
  -z, --str, --stream
  -n, --noc, --fresh, --no-cache
  -D, --dif, --diff <file>
  -X, --max, --limit, --max-diff-lines <n>

Comparison:
  -B, --br, --branch [base-ref]   Analyze the current branch against a base branch
  -P, --pull-request, --pr [base-ref]       Alias for --branch, useful for PR-style comparisons

Search:
  --author <name>, -a       Filter results by author
  --since <date>, --from, -S  Start date for search (YYYY-MM-DD)
  --until <date>, --to, -U  End date for search (YYYY-MM-DD)
  --limit <n>, -L           Maximum number of results (default: 50)
  --pattern <pattern>, --pat File pattern to filter by
  --file-type <ext>, --type, -T  File extension for code search (e.g., js, py)
  --case-insensitive, -i    Case-insensitive pattern matching
  --granularity <period>, -G  Timeline granularity: hourly, daily, weekly, monthly (default: daily)
  Actions: semantic (sm), pattern (sp), code (sc), timeline (sl)

Config:
  Project config: .gitxplainrc or .gitxplainrc.json
  User config: ~/.gitxplain/config.json (macOS/Linux) or %USERPROFILE%\\.gitxplain\\config.json (Windows)

Notes:
  Run gitxplain inside a Git repository (or use gx as a short alias).
  If no command or mode is supplied, gitxplain prints this help text.
  Use --provider or --model to override your config or environment for one command.
  Use gitxplain git <args...> to run any native Git subcommand with its normal flags.
  install-hook supports: post-commit, post-merge, pre-push.
""")

def get_flag_value(args: List[str], flag_name: str) -> Optional[str]:
    try:
        direct_index = args.index(flag_name)
        if direct_index >= 0:
            if direct_index + 1 < len(args):
                next_arg = args[direct_index + 1]
                if not next_arg.startswith("--"):
                    return next_arg
            return None
    except ValueError:
        pass

    for arg in args:
        if arg.startswith(f"{flag_name}="):
            return arg[len(flag_name) + 1:]
    return None

def parse_number(value: Optional[str], fallback: Optional[int] = None) -> Optional[int]:
    if value is None or value == "":
        return fallback
    try:
        parsed = int(value)
        if parsed <= 0:
            raise ValueError()
        return parsed
    except ValueError:
        raise ValueError(f"Invalid numeric value: {value}")

def redact_config_value(key: str, value: Any) -> Any:
    if not isinstance(value, str):
        return value

    import re
    if not re.search(r'api[_-]?key', key, re.IGNORECASE):
        return value

    if len(value) <= 8:
        return "*" * len(value)

    return f"{value[:4]}...{value[-4:]}"

def print_config_entries(config: Dict[str, Any]) -> None:
    entries = sorted(config.items())
    if not entries:
        print("No user config saved yet.")
        return

    for key, value in entries:
        print(f"{key}: {redact_config_value(key, value)}")

def resolve_config_set_update(parsed: Dict[str, Any], current_config: Dict[str, Any]) -> Dict[str, Any]:
    key = parsed.get("configKey")
    value = parsed.get("configValue")

    if not key or not value:
        raise RuntimeError('Usage: gitxplain config set <provider|model|api-key> <value> [--provider <name>]')

    if key == "provider":
        return {"provider": value.lower()}

    if key == "model":
        return {"model": value}

    if key == "api-key":
        resolved_provider = (parsed.get("provider") or current_config.get("provider") or os.environ.get("LLM_PROVIDER") or "").lower()
        api_key_field = get_provider_api_key_field(resolved_provider)

        if not api_key_field:
            raise RuntimeError("Set a provider first with `gitxplain config set provider <name>`, or pass `--provider <name>`.")

        return {api_key_field: value}

    return {key: value}

def handle_config_command(parsed: Dict[str, Any]) -> int:
    current_config = load_user_config()
    action = parsed.get("configAction")

    if action == "list" or action is None:
        print(f"User config: {get_user_config_path()}")
        print_config_entries(current_config)
        return 0

    if action == "get":
        print(f"User config: {get_user_config_path()}")
        key = parsed.get("configKey")
        if not key:
            print_config_entries(current_config)
            return 0

        value = current_config.get(key)
        if value is None:
            print(f"No value saved for {key}.")
            return 0

        print(f"{key}: {redact_config_value(key, value)}")
        return 0

    if action == "set":
        updates = resolve_config_set_update(parsed, current_config)
        res = update_user_config(updates)
        config_path = res["configPath"]
        saved_key, saved_value = list(updates.items())[0]
        print(f"Saved {saved_key} to {config_path}.")
        print(f"{saved_key}: {redact_config_value(saved_key, saved_value)}")
        return 0

    raise ValueError(f"Unknown config subcommand: {action}")

def handle_cache_command(parsed: Dict[str, Any]) -> int:
    action = parsed.get("cacheAction")
    if action is None:
        raise ValueError('Usage: gitxplain cache <clear|stats>')

    if action == "clear":
        deleted_count = clear_cache()
        print(f"Cleared {deleted_count} cache {'entry' if deleted_count == 1 else 'entries'}.")
        return 0

    if action == "stats":
        stats = get_cache_stats()
        print("\n".join([
            "Cache Stats",
            f"Entries: {stats['entryCount']}",
            f"Size: {stats['totalSizeBytes']} bytes",
            f"Oldest: {stats['oldestEntryIso'] or 'n/a'}",
            f"Newest: {stats['newestEntryIso'] or 'n/a'}"
        ]))
        return 0

    raise ValueError(f"Unknown cache subcommand: {action}")

async def handle_search_command(parsed: Dict[str, Any], cwd: str, config: Dict[str, Any]) -> int:
    search_action_name = parsed.get("searchAction")
    search_query = parsed.get("searchQuery")
    search_author = parsed.get("searchAuthor")
    search_since = parsed.get("searchSince")
    search_until = parsed.get("searchUntil")
    search_limit = parsed.get("searchLimit")
    search_pattern = parsed.get("searchPattern")
    search_file_type = parsed.get("searchFileType")
    search_case_insensitive = parsed.get("searchCaseInsensitive")
    search_granularity = parsed.get("searchGranularity")
    fmt = parsed.get("format")

    if not search_query:
        raise RuntimeError('Usage: gitxplain search <semantic|pattern|code|timeline> "<query>" [options]')

    options = {
        "limit": int(search_limit) if search_limit else 50,
        "author": search_author,
        "since": search_since,
        "until": search_until,
        "pattern": search_pattern,
        "fileType": search_file_type,
        "caseInsensitive": search_case_insensitive,
        "granularity": search_granularity,
        "provider": config.get("provider"),
        "model": config.get("model")
    }

    action_map = {
        "semantic": "semantic",
        "sm": "semantic",
        "pattern": "pattern",
        "sp": "pattern",
        "code": "code",
        "sc": "code",
        "timeline": "timeline",
        "sl": "timeline"
    }

    normalized_action = action_map.get(search_action_name, search_action_name)

    if normalized_action == "semantic":
        result = await semantic_search(search_query, cwd, options)
    elif normalized_action == "pattern":
        result = await pattern_search(search_query, cwd, options)
    elif normalized_action == "code":
        result = await code_pattern_search(search_query, cwd, options)
    elif normalized_action == "timeline":
        if not search_author:
            raise RuntimeError("Timeline search requires --author flag")
        result = await author_activity_timeline(search_author, cwd, options)
    else:
        raise ValueError(f"Unknown search action: {search_action_name}. Use: semantic (sm), pattern (sp), code (sc), or timeline (sl)")

    if fmt == "json":
        print(json.dumps(result, indent=2))
    elif fmt == "markdown":
        print(format_search_result_markdown(result))
    else:
        print(format_search_result_text(result))

    return 0

def format_search_result_text(result: Dict[str, Any]) -> str:
    if result.get("error"):
        return f"Error: {result['error']}"

    if "timeline" in result:
        # Timeline result
        output = f"Author Activity Timeline: {result['author']}\n"
        stats = result.get("stats")
        if stats:
            output += f"Total Commits: {stats['totalCommits']}\n"
            dr = stats.get("dateRange")
            output += f"Date Range: {dr.get('start') if dr else 'n/a'} to {dr.get('end') if dr else 'n/a'}\n"
            output += f"Average per {result.get('granularity')}: {stats['averagePerPeriod']}\n"
            map_period = stats.get("mostActivePeriod")
            output += f"Most Active Period: {map_period.get('period') if map_period else 'n/a'} ({map_period.get('count') if map_period else 0} commits)\n\n"
        output += "Timeline:\n"

        timeline_data = result.get("timeline", [])
        if timeline_data:
            max_commits = max(p.get("count", 0) for p in timeline_data) or 1
            for period in timeline_data:
                bar_length = round((period.get("count", 0) / max_commits) * 20)
                bar = '█' * bar_length + '░' * (20 - bar_length)
                output += f"  {period.get('period')}: {bar} {period.get('count')}\n"
        return output

    query_val = result.get("query") or result.get("pattern")
    total = result.get("total", 0)
    fallback = "Fallback " if result.get("fallback") else ""
    output = f"{fallback}Search Results for: \"{query_val}\"\n"
    output += f"Found {total} result{'s' if total != 1 else ''}\n\n"

    results = result.get("results", [])
    if not results:
        return output + "No matching commits found."

    for idx, commit in enumerate(results):
        output += f"{idx + 1}. {commit.get('sha')} - {commit.get('message')}\n"
        output += f"   Author: {commit.get('author')} | Date: {commit.get('date')}\n"
        if commit.get("diff"):
            output += f"   Diff: {commit['diff'][:100]}...\n"
        if commit.get("matchType"):
            output += f"   Match Type: {commit.get('matchType')}\n"
        if commit.get("relevance") is not None:
            output += f"   Relevance: {commit.get('relevance')}\n"
        output += "\n"

    return output

def format_search_result_markdown(result: Dict[str, Any]) -> str:
    if result.get("error"):
        return f"**Error:** {result['error']}"

    if "timeline" in result:
        output = f"## Author Activity Timeline: {result['author']}\n\n"
        stats = result.get("stats")
        if stats:
            output += f"- **Total Commits:** {stats['totalCommits']}\n"
            dr = stats.get("dateRange")
            output += f"- **Date Range:** {dr.get('start') if dr else 'n/a'} to {dr.get('end') if dr else 'n/a'}\n"
            output += f"- **Average per {result.get('granularity')}:** {stats['averagePerPeriod']}\n"
            map_period = stats.get("mostActivePeriod")
            output += f"- **Most Active Period:** {map_period.get('period') if map_period else 'n/a'} ({map_period.get('count') if map_period else 0} commits)\n\n"
        output += "### Timeline\n\n"
        output += "| Period | Commits | Activity |\n"
        output += "|--------|---------|----------|\n"

        timeline_data = result.get("timeline", [])
        if timeline_data:
            max_commits = max(p.get("count", 0) for p in timeline_data) or 1
            for period in timeline_data:
                bar_length = round((period.get("count", 0) / max_commits) * 20)
                bar = '█' * bar_length
                output += f"| {period.get('period')} | {period.get('count')} | {bar} |\n"
        return output

    query_val = result.get("query") or result.get("pattern")
    total = result.get("total", 0)
    fallback = "Fallback " if result.get("fallback") else ""
    output = f"## {fallback}Search Results for: \"{query_val}\"\n\n"
    output += f"**Found {total} result{'s' if total != 1 else ''}**\n\n"

    results = result.get("results", [])
    if not results:
        return output + "No matching commits found."

    for idx, commit in enumerate(results):
        output += f"### {idx + 1}. {commit.get('sha')}\n\n"
        output += f"**{commit.get('message')}**\n\n"
        output += f"- **Author:** {commit.get('author')}\n"
        output += f"- **Date:** {commit.get('date')}\n"
        if commit.get("diff"):
            output += f"- **Diff Preview:** `{commit['diff'][:100]}...`\n"
        if commit.get("matchType"):
            output += f"- **Match Type:** {commit.get('matchType')}\n"
        if commit.get("relevance") is not None:
            output += f"- **Relevance Score:** {commit.get('relevance')}\n"
        output += "\n"

    return output

def is_direct_native_git_subcommand(subcommand: str, known_git_subcommands: Set[str]) -> bool:
    if not subcommand or subcommand.startswith("-"):
        return False

    if subcommand in RESERVED_SUBCOMMANDS:
        return False

    return subcommand in known_git_subcommands

def parse_args(argv: List[str], options: Dict[str, Any] = None) -> Dict[str, Any]:
    if options is None:
        options = {}

    known_git_subcommands = options.get("gitSubcommands") or list_git_subcommands()
    raw_subcommand = argv[1] if len(argv) > 1 else None
    
    is_native = (
        raw_subcommand == "git" or
        is_direct_native_git_subcommand(raw_subcommand, known_git_subcommands)
    )
    
    if is_native:
        args = argv[1:]
    else:
        args = expand_aliases(argv[1:])
        
    subcommand = args[0] if args else None
    
    flags = set(arg for arg in args if arg.startswith("--"))
    value_flags = {
        "--provider", "--model", "--max-diff-lines", "--branch", "--pr", "--blame", "--stash", "--diff",
        "-w", "--prov", "-W", "-O", "--mod", "--mo", "-X", "--max", "--limit", "-B", "--br", "-P", "-b",
        "--bla", "-Z", "--sta", "-D", "--dif", "--author", "--since", "--until", "--pattern", "--file-type",
        "--granularity", "-a", "--from", "-S", "--to", "-U", "-L", "--pat", "-T", "--type", "-G"
    }

    positional = []
    index = 0
    while index < len(args):
        arg = args[index]
        if not arg.startswith("--"):
            positional.append(arg)
            index += 1
            continue

        if "=" in arg:
            index += 1
            continue

        if arg in value_flags:
            if index + 1 < len(args):
                next_arg = args[index + 1]
                if not next_arg.startswith("--"):
                    index += 2
                    continue
        index += 1

    explicit_mode = None
    for flag, mode in MODE_FLAGS.items():
        if flag in flags:
            explicit_mode = mode
            break

    explicit_format = None
    for flag, fmt in FORMAT_FLAGS.items():
        if flag in flags:
            explicit_format = fmt
            break

    is_install_hook = subcommand == "install-hook"
    is_config_command = subcommand == "config"
    is_cache_command = subcommand == "cache"
    is_native_git_wrapper = subcommand == "git"
    is_release_command = "--release" in flags
    is_add_command = subcommand == "add"
    is_remove_command = subcommand == "remove"
    is_delete_command = subcommand == "del"
    is_pipeline_command = "--pipeline" in flags
    is_bin_command = subcommand == "bin"
    is_pop_command = subcommand == "pop"
    is_pull_command = subcommand == "pull"
    is_push_command = subcommand == "push"
    is_search_command = subcommand in ("search", "find")

    is_remove_hard_command = is_remove_command and len(positional) == 2 and positional[1] == "hard"
    is_native_git_command = is_native_git_wrapper or is_direct_native_git_subcommand(subcommand, known_git_subcommands)

    return {
        "subcommand": subcommand,
        "help": "--help" in flags or subcommand == "help",
        "version": "--version" in flags,
        "cost": "--cost" in flags,
        "nativeGitCommand": is_native_git_command,
        "installHook": is_install_hook,
        "configCommand": is_config_command,
        "cacheCommand": is_cache_command,
        "configAction": positional[1] if (is_config_command and len(positional) > 1) else None,
        "configKey": positional[2] if (is_config_command and len(positional) > 2) else None,
        "configValue": " ".join(positional[3:]) if (is_config_command and len(positional) > 3) else None,
        "cacheAction": positional[1] if (is_cache_command and len(positional) > 1) else None,
        "releaseCommand": is_release_command,
        "releaseAction": positional[0] if (is_release_command and len(positional) > 0) else "status",
        "addCommand": is_add_command,
        "removeCommand": is_remove_command,
        "deleteCommand": is_delete_command,
        "pipelineCommand": is_pipeline_command,
        "binCommand": is_bin_command,
        "popCommand": is_pop_command,
        "pullCommand": is_pull_command,
        "pushCommand": is_push_command,
        "searchCommand": is_search_command,
        "removeHardCommand": is_remove_hard_command,
        "nativeGitArgs": args[1:] if is_native_git_wrapper else (args if is_native_git_command else []),
        "hookName": positional[1] if (is_install_hook and len(positional) > 1) else "post-commit",
        "actionPaths": positional[1:] if (is_add_command or is_delete_command or (is_remove_command and not is_remove_hard_command)) else [],
        "stashIndex": positional[1] if (is_pop_command and len(positional) > 1) else None,
        "pullRemote": positional[1] if (is_pull_command and len(positional) > 1) else None,
        "pullBranch": positional[2] if (is_pull_command and len(positional) > 2) else None,
        "pushRemote": positional[1] if (is_push_command and len(positional) > 1) else None,
        "pushBranch": positional[2] if (is_push_command and len(positional) > 2) else None,
        "searchAction": positional[1] if (is_search_command and len(positional) > 1) else "semantic",
        "searchQuery": positional[2] if (is_search_command and len(positional) > 2) else None,
        "searchAuthor": get_flag_value(args, "--author"),
        "searchSince": get_flag_value(args, "--since"),
        "searchUntil": get_flag_value(args, "--until"),
        "searchLimit": get_flag_value(args, "--limit"),
        "searchPattern": get_flag_value(args, "--pattern"),
        "searchFileType": get_flag_value(args, "--file-type"),
        "searchCaseInsensitive": "--case-insensitive" in flags or "-i" in flags,
        "searchGranularity": get_flag_value(args, "--granularity") or "daily",
        "commitRef": None if (
            is_install_hook or is_config_command or is_cache_command or is_native_git_command or
            is_release_command or is_add_command or is_remove_command or is_delete_command or
            is_pipeline_command or is_bin_command or is_pop_command or is_pull_command or
            is_push_command or is_search_command or subcommand == "help"
        ) else (positional[0] if len(positional) > 0 else None),
        "mode": explicit_mode,
        "format": explicit_format,
        "provider": get_flag_value(args, "--provider"),
        "model": get_flag_value(args, "--model"),
        "maxDiffLines": parse_number(get_flag_value(args, "--max-diff-lines")),
        "blameFile": get_flag_value(args, "--blame"),
        "stashRef": get_flag_value(args, "--stash") if ("--stash" in flags or any(arg.startswith("--stash=") for arg in args)) else None,
        "diffFile": get_flag_value(args, "--diff"),
        "hasBranchFlag": "--branch" in flags or any(arg.startswith("--branch=") for arg in args),
        "branchBase": get_flag_value(args, "--branch"),
        "hasPrFlag": "--pr" in flags or any(arg.startswith("--pr=") for arg in args),
        "prBase": get_flag_value(args, "--pr"),
        "clipboard": "--clipboard" in flags,
        "stream": "--stream" in flags,
        "noCache": "--no-cache" in flags,
        "verbose": "--verbose" in flags,
        "quiet": "--quiet" in flags,
        "execute": "--execute" in flags,
        "dryRun": "--dry-run" in flags,
        "interactive": "--interactive" in flags,
        "release": "--release" in flags,
        "log": "--log" in flags,
        "status": "--status" in flags,
        "merge": "--merge" in flags,
        "tag": "--tag" in flags
    }

def ask_question(prompt: str) -> str:
    try:
        return input(prompt).strip()
    except (KeyboardInterrupt, EOFError):
        return ""

def resolve_configured_analysis_mode(config: Dict[str, Any]) -> str:
    mode = config.get("mode")
    return mode if mode in ANALYSIS_MODES else "full"

def resolve_runtime_options(parsed: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "mode": parsed.get("mode") or resolve_configured_analysis_mode(config),
        "format": parsed.get("format") or config.get("format") or "plain",
        "provider": parsed.get("provider") or config.get("provider"),
        "model": parsed.get("model") or config.get("model"),
        "maxDiffLines": parsed.get("maxDiffLines") or config.get("maxDiffLines") or 800,
        "clipboard": parsed.get("clipboard") or config.get("clipboard") is True,
        "stream": parsed.get("stream") or config.get("stream") is True,
        "noCache": parsed.get("noCache", False),
        "verbose": parsed.get("verbose") or config.get("verbose") is True,
        "quiet": parsed.get("quiet") or config.get("quiet") is True
    }

def format_usage_stats(stats: Dict[str, Any]) -> str:
    return "\n".join([
        "Usage Stats",
        f"Requests: {stats['requestCount']}",
        f"Input Tokens: {stats['inputTokens']}",
        f"Output Tokens: {stats['outputTokens']}",
        f"Total Tokens: {stats['totalTokens']}",
        f"Estimated Cost: ${stats['estimatedCostUsd']:.6f}"
    ])

async def review_split_plan_interactively(plan: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    edited_commits = []
    deferred_files = []

    commits = plan.get("commits", [])
    for commit in sorted(commits, key=lambda x: x.get("order", 0)):
        print("")
        print(f"{commit.get('order')}. {commit.get('message')}")
        print(f"Files: {', '.join(commit.get('files', []))}")
        print(f"Why: {commit.get('description')}")

        action = ask_question('Action [keep/edit/skip/abort] > ').strip().lower()

        if action == "abort":
            return None

        if action == "skip":
            deferred_files.extend(commit.get("files", []))
            continue

        if action == "edit":
            next_message = ask_question("New commit message (leave blank to keep current) > ").strip()
            next_description = ask_question("New description (leave blank to keep current) > ").strip()
            edited_commits.append({
                **commit,
                "message": next_message if next_message else commit.get("message"),
                "description": next_description if next_description else commit.get("description")
            })
            continue

        edited_commits.append(commit)

    if deferred_files:
        edited_commits.append({
            "order": len(edited_commits) + 1,
            "message": "chore: include deferred split changes",
            "files": deferred_files,
            "description": "Captures split groups that were skipped during interactive review."
        })

    return {
        **plan,
        "commits": [{**commit, "order": idx + 1} for idx, commit in enumerate(edited_commits)]
    }

def resolve_target_ref(parsed: Dict[str, Any], cwd: str) -> Optional[str]:
    if parsed.get("commitRef"):
        return parsed["commitRef"]

    if parsed.get("hasBranchFlag") or parsed.get("hasPrFlag"):
        base_ref = parsed.get("branchBase") or parsed.get("prBase") or get_default_base_ref(cwd)
        return build_branch_range(base_ref, cwd)

    return None

def render_final_output(params: Dict[str, Any]) -> str:
    runtime_options = params.get("runtimeOptions", {})
    fmt = runtime_options.get("format")

    if fmt == "json":
        return format_json_output(params)
    if fmt == "markdown":
        return format_markdown_output(params)
    if fmt == "html":
        return format_html_output(params)

    # plain output format
    return format_output({
        **params,
        "options": runtime_options
    })

async def run_pipeline_command(cwd: str) -> int:
    analysis = inspect_repository_for_pipeline(cwd)
    if not analysis.get("supported"):
        print(analysis.get("reason", "Pipeline not supported"))
        return 1

    print(format_pipeline_recommendations(analysis))

    answer = ask_question(f'\nChoose a pipeline option (1-{len(analysis["options"])}) or type "cancel" > ')
    selection = resolve_pipeline_selection(analysis, answer)

    if not selection:
        print("Aborted.")
        return 0

    res = write_pipeline_files(cwd, analysis, selection)
    written_files = res["writtenFiles"]
    updated_files = res["updatedFiles"]
    unchanged_files = res["unchangedFiles"]
    notes = res["notes"]

    if not updated_files and unchanged_files:
        print(f"\nWorkflow files already matched the current template: {', '.join(unchanged_files)}")
    elif updated_files and not unchanged_files:
        print(f"\nUpdated workflow files: {', '.join(updated_files)}")
    else:
        print(f"\nUpdated workflow files: {', '.join(updated_files)}")
        print(f"Unchanged workflow files: {', '.join(unchanged_files)}")

    if notes:
        print("\n" + "\n".join(notes))

    return 0

def is_configured(cwd: str) -> bool:
    config = load_config(cwd)
    provider = config.get("provider") or os.environ.get("LLM_PROVIDER")
    if not provider:
        return False
    if provider.lower() == "ollama":
        return True
    api_key_field = get_provider_api_key_field(provider)
    if not api_key_field:
        return False
    api_key = config.get(api_key_field) or os.environ.get(api_key_field)
    if not api_key:
        return False
    return True

def get_key_unix(timeout: float) -> Optional[str]:
    import select
    import termios
    import tty
    import sys
    
    fd = sys.stdin.fileno()
    if not os.isatty(fd):
        return sys.stdin.read(1)
        
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        rlist, _, _ = select.select([sys.stdin], [], [], timeout)
        if rlist:
            char = sys.stdin.read(1)
            if char == '\x1b':
                rlist2, _, _ = select.select([sys.stdin], [], [], 0.05)
                if rlist2:
                    char2 = sys.stdin.read(1)
                    if char2 == '[':
                        rlist3, _, _ = select.select([sys.stdin], [], [], 0.05)
                        if rlist3:
                            char3 = sys.stdin.read(1)
                            return f"\x1b[{char3}"
                    return f"\x1b{char2}"
                return '\x1b'
            return char
        return None
    except Exception:
        return None
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

def get_key_windows(timeout: float) -> Optional[str]:
    import msvcrt
    import time
    start = time.time()
    while time.time() - start < timeout:
        if msvcrt.kbhit():
            try:
                char = msvcrt.getch()
                if char in [b'\x00', b'\xe0']:
                    if msvcrt.kbhit():
                        sub = msvcrt.getch()
                        if sub == b'H':
                            return '\x1b[A'
                        elif sub == b'P':
                            return '\x1b[B'
                return char.decode('utf-8', errors='ignore')
            except Exception:
                return None
        time.sleep(0.01)
    return None

def get_key(timeout: float) -> Optional[str]:
    try:
        import msvcrt
        return get_key_windows(timeout)
    except ImportError:
        return get_key_unix(timeout)

def animate_gx_logo(duration: float = 1.0) -> None:
    import time
    
    logo = """
    ██████╗ ██╗  ██╗
   ██╔════╝ ╚██╗██╔╝
   ██║  ███╗ ╚███╔╝ 
   ██║   ██║ ██╔██╗ 
   ╚██████╔╝██╔╝ ██╗
    ╚═════╝ ╚═╝  ╚═╝
    """
    
    color_sequences = [
        "\u001b[35m", # Magenta
        "\u001b[95m", # Light Magenta
        "\u001b[34m", # Blue
        "\u001b[94m", # Light Blue
        "\u001b[36m", # Cyan
        "\u001b[96m", # Light Cyan
        "\u001b[32m", # Green
        "\u001b[92m", # Light Green
        "\u001b[33m", # Yellow
        "\u001b[31m"  # Red
    ]
    
    start_time = time.time()
    frame = 0
    
    sys.stdout.write("\033[?25l")
    sys.stdout.flush()
    
    try:
        while time.time() - start_time < duration:
            sys.stdout.write("\033[H\033[J")
            
            logo_lines = logo.strip("\n").split("\n")
            for idx, line in enumerate(logo_lines):
                color = color_sequences[(idx + frame) % len(color_sequences)]
                sys.stdout.write(colorize(line, "\u001b[1m" + color) + "\n")
            
            loader_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
            loader_char = loader_chars[frame % len(loader_chars)]
            
            progress = int((time.time() - start_time) / duration * 20)
            bar = "█" * progress + "░" * (20 - progress)
            
            sys.stdout.write(f"\n  {colorize(loader_char, ANSI.cyan)} Loading GX TUI... [{colorize(bar, ANSI.cyan)}]\n")
            sys.stdout.flush()
            
            frame += 1
            time.sleep(0.06)
            
    finally:
        sys.stdout.write("\033[?25h")
        sys.stdout.flush()

def select_provider_interactive() -> Optional[str]:
    providers = [
        ("openai", "OpenAI (gpt-4o, gpt-4-turbo)"),
        ("anthropic", "Anthropic (claude-3-5-sonnet-latest)"),
        ("gemini", "Google Gemini (gemini-1.5-pro, gemini-1.5-flash)"),
        ("groq", "Groq (llama3-70b-8192)"),
        ("openrouter", "OpenRouter (anthropic/claude-3.5-sonnet)"),
        ("mistral", "Mistral (mistral-large-latest)"),
        ("azure-openai", "Azure OpenAI (Enterprise)"),
        ("ollama", "Ollama (Local models)"),
        ("chutes", "Chutes (Open Source models)")
    ]
    
    selected_idx = 0
    sys.stdout.write("\033[?25l")
    sys.stdout.flush()
    
    try:
        while True:
            sys.stdout.write("\033[H\033[J")
            sys.stdout.write(colorize("""
  ┌──────────────────────────────────────────────────────────┐
  │                 GX Configuration Wizard                  │
  └──────────────────────────────────────────────────────────┘
            """, ANSI.bold + ANSI.cyan))
            sys.stdout.write("Please select your AI provider (Use Arrow keys + Enter):\n\n")
            
            for idx, (p_id, desc) in enumerate(providers):
                if idx == selected_idx:
                    sys.stdout.write(f"  {colorize('➔', ANSI.bold + ANSI.cyan)} {colorize(desc, ANSI.bold + ANSI.cyan)}\n")
                else:
                    sys.stdout.write(f"    {desc}\n")
                    
            sys.stdout.write(colorize("\n[Enter] Select  |  [q] Quit\n", ANSI.gray))
            sys.stdout.flush()
            
            key = get_key(0.2)
            if key:
                if key.lower() in ['q', '\x03', '\x1b']:
                    return None
                elif key == '\x1b[A':
                    selected_idx = (selected_idx - 1) % len(providers)
                elif key == '\x1b[B':
                    selected_idx = (selected_idx + 1) % len(providers)
                elif key in ['\r', '\n']:
                    return providers[selected_idx][0]
    finally:
        sys.stdout.write("\033[?25h")
        sys.stdout.flush()

def select_model_interactive(provider: str) -> Optional[str]:
    provider_models = {
        "openai": ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"],
        "anthropic": ["claude-3-5-sonnet-latest", "claude-3-5-haiku-latest", "claude-3-opus-latest"],
        "gemini": ["gemini-1.5-pro", "gemini-1.5-flash"],
        "groq": ["llama3-70b-8192", "mixtral-8x7b-32768"],
        "openrouter": ["anthropic/claude-3.5-sonnet", "meta-llama/llama-3-70b-instruct"],
        "mistral": ["mistral-large-latest", "mistral-medium-latest"],
        "azure-openai": [],
        "ollama": ["llama3", "mistral", "phi3"],
        "chutes": ["meta-llama/Meta-Llama-3-8B-Instruct"]
    }
    
    models = provider_models.get(provider, []).copy()
    models.append("Custom Model...")
    
    selected_idx = 0
    sys.stdout.write("\033[?25l")
    sys.stdout.flush()
    
    try:
        while True:
            sys.stdout.write("\033[H\033[J")
            sys.stdout.write(colorize("""
  ┌──────────────────────────────────────────────────────────┐
  │                 GX Configuration Wizard                  │
  └──────────────────────────────────────────────────────────┘
            """, ANSI.bold + ANSI.cyan))
            sys.stdout.write(f"Please select a model for {provider.upper()} (Use Arrow keys + Enter):\n\n")
            
            for idx, model in enumerate(models):
                if idx == selected_idx:
                    sys.stdout.write(f"  {colorize('➔', ANSI.bold + ANSI.cyan)} {colorize(model, ANSI.bold + ANSI.cyan)}\n")
                else:
                    sys.stdout.write(f"    {model}\n")
                    
            sys.stdout.write(colorize("\n[Enter] Select  |  [q] Quit\n", ANSI.gray))
            sys.stdout.flush()
            
            key = get_key(0.2)
            if key:
                if key.lower() in ['q', '\x03', '\x1b']:
                    return None
                elif key == '\x1b[A':
                    selected_idx = (selected_idx - 1) % len(models)
                elif key == '\x1b[B':
                    selected_idx = (selected_idx + 1) % len(models)
                elif key in ['\r', '\n']:
                    selected_model = models[selected_idx]
                    if selected_model == "Custom Model...":
                        sys.stdout.write("\033[?25h")
                        sys.stdout.flush()
                        custom = ask_question("\nEnter custom model name > ")
                        return custom if custom else None
                    return selected_model
    finally:
        sys.stdout.write("\033[?25h")
        sys.stdout.flush()

def run_config_wizard(cwd: str) -> None:
    import time
    import getpass
    
    provider = select_provider_interactive()
    if not provider:
        print(colorize("Aborted.", ANSI.red))
        time.sleep(1)
        return

    update_user_config({"provider": provider})
    
    if provider != "ollama":
        api_key_field = get_provider_api_key_field(provider)
        print(f"\nAPI Key is required for {provider.upper()}.")
        if provider == "openai":
            print(colorize("  Get one from: https://platform.openai.com/api-keys", ANSI.gray))
        elif provider == "anthropic":
            print(colorize("  Get one from: https://console.anthropic.com/settings/keys", ANSI.gray))
        elif provider == "gemini":
            print(colorize("  Get one from: https://aistudio.google.com/app/apikey", ANSI.gray))
        elif provider == "groq":
            print(colorize("  Get one from: https://console.groq.com/keys", ANSI.gray))
        elif provider == "openrouter":
            print(colorize("  Get one from: https://openrouter.ai/settings/keys", ANSI.gray))
        elif provider == "mistral":
            print(colorize("  Get one from: https://console.mistral.ai/api-keys", ANSI.gray))
        elif provider == "chutes":
            print(colorize("  Get one from: https://chutes.ai", ANSI.gray))
            
        try:
            api_key = getpass.getpass(colorize(f"Enter your {provider.upper()} API Key (hidden) > ", ANSI.bold + ANSI.cyan)).strip()
        except (KeyboardInterrupt, EOFError):
            print(colorize("\nAborted.", ANSI.red))
            return
            
        if not api_key:
            print(colorize("API key cannot be empty. Aborted.", ANSI.red))
            time.sleep(1.5)
            return
        update_user_config({api_key_field: api_key})
        
    model = select_model_interactive(provider)
    if not model:
        print(colorize("Aborted.", ANSI.red))
        time.sleep(1)
        return
        
    update_user_config({"model": model})
        
    custom_url = ask_question("\nDo you want to specify a custom API Base URL? (yes/no) [default: no] > ")
    if custom_url.lower() in ["yes", "y"]:
        base_url = ask_question("Enter custom Base URL > ")
        if base_url:
            url_field = f"{provider.upper().replace('-', '_')}_BASE_URL"
            update_user_config({url_field: base_url})
            print(colorize(f"Saved custom Base URL for {provider.upper()}.", ANSI.green))

    print("\033[H\033[J", end="")
    success_banner = f"""
  ┌──────────────────────────────────────────────────────────┐
  │           Configuration Saved Successfully!              │
  ├──────────────────────────────────────────────────────────┤
  │  Provider: {provider.upper():<45} │
  │  Model:    {model:<45} │
  │  Config:   {get_user_config_path():<45} │
  └──────────────────────────────────────────────────────────┘
    """
    print(colorize(success_banner, ANSI.bold + ANSI.green))
    time.sleep(2)

async def run_tui(cwd: str) -> int:
    import time
    
    logo = """
    ██████╗ ██╗  ██╗
   ██╔════╝ ╚██╗██╔╝
   ██║  ███╗ ╚███╔╝ 
   ██║   ██║ ██╔██╗ 
   ╚██████╔╝██╔╝ ██╗
    ╚═════╝ ╚═╝  ╚═╝
    """
    
    color_sequences = [
        "\u001b[35m", # Magenta
        "\u001b[95m", # Light Magenta
        "\u001b[34m", # Blue
        "\u001b[94m", # Light Blue
        "\u001b[36m", # Cyan
        "\u001b[96m", # Light Cyan
        "\u001b[32m", # Green
        "\u001b[92m", # Light Green
        "\u001b[33m", # Yellow
        "\u001b[31m"  # Red
    ]
    
    animate_gx_logo(0.6)
    
    frame = 0
    selected_index = 0
    sys.stdout.write("\033[?25l")
    sys.stdout.flush()
    
    try:
        while True:
            current_config = load_config(cwd)
            provider = current_config.get("provider") or os.environ.get("LLM_PROVIDER") or "none"
            model = current_config.get("model") or os.environ.get("LLM_MODEL") or "default"
            is_repo = is_git_repository(cwd)
            
            sys.stdout.write("\033[H")
            
            logo_lines = logo.strip("\n").split("\n")
            for idx, line in enumerate(logo_lines):
                color = color_sequences[(idx + frame) % len(color_sequences)]
                sys.stdout.write(colorize(line, "\u001b[1m" + color) + "\n")
                
            sys.stdout.write(colorize(f"\n  Version: {CLI_VERSION} | Provider: {provider.upper()} | Model: {model}\n", ANSI.gray))
            
            if not is_repo:
                sys.stdout.write(colorize("  [Warning] Not inside a Git repository. Git commands are disabled.\n", ANSI.bold + ANSI.yellow))
            else:
                sys.stdout.write("\n")
                
            sys.stdout.write(colorize("  ┌──────────────────────────────────────────────────────────┐\n", ANSI.cyan))
            sys.stdout.write(colorize("  │  GX Interactive Dashboard                                │\n", ANSI.cyan))
            sys.stdout.write(colorize("  ├──────────────────────────────────────────────────────────┤\n", ANSI.cyan))
            
            menu_options = [
                ("1", "Quick Summary of Last Commit"),
                ("2", "Full Analysis of Last Commit"),
                ("3", "Plan & Execute Commits (Commit Planner)"),
                ("4", "Interactive Commit Splitting"),
                ("5", "Search Commit History"),
                ("6", "Usage Cost and Cache Stats"),
                ("7", "Run Configuration Wizard"),
                ("8", "Install Git Hooks"),
                ("9", "Exit Dashboard")
            ]
            
            for idx, (key, name) in enumerate(menu_options):
                if idx == selected_index:
                    sys.stdout.write(f"  │ {colorize('➔', ANSI.bold + ANSI.cyan)} {colorize(f'[{key}] {name:<51}', ANSI.bold + ANSI.cyan)} │\n")
                else:
                    sys.stdout.write(f"  │    [{key}] {name:<51} │\n")
                
            sys.stdout.write(colorize("  └──────────────────────────────────────────────────────────┘\n", ANSI.cyan))
            sys.stdout.write(colorize("\n  Use Arrow keys to navigate, [Enter] to select, or 'q' to quit > ", ANSI.bold + ANSI.cyan))
            sys.stdout.flush()
            
            key = get_key(0.1)
            choice = None
            
            if key:
                if key.lower() in ['q', '\x03', '\x1b']:
                    print(colorize("\n\n  Goodbye!", ANSI.bold + ANSI.green))
                    break
                elif key == '\x1b[A':
                    selected_index = (selected_index - 1) % len(menu_options)
                elif key == '\x1b[B':
                    selected_index = (selected_index + 1) % len(menu_options)
                elif key in ['\r', '\n']:
                    choice = menu_options[selected_index][0]
                elif key in ['1', '2', '3', '4', '5', '6', '7', '8', '9']:
                    choice = key
                    selected_index = int(key) - 1
                
                if choice:
                    sys.stdout.write("\033[?25h\033[H\033[J")
                    sys.stdout.flush()
                    
                    try:
                        if choice == "1":
                            if not is_repo:
                                print(colorize("Error: This command requires a Git repository.", ANSI.red))
                            else:
                                print(colorize("=== Quick Summary of Last Commit ===\n", ANSI.bold + ANSI.cyan))
                                await _main(["gx", "HEAD", "-s"])
                            ask_question("\nPress Enter to return to menu...")
                        elif choice == "2":
                            if not is_repo:
                                print(colorize("Error: This command requires a Git repository.", ANSI.red))
                            else:
                                print(colorize("=== Full Analysis of Last Commit ===\n", ANSI.bold + ANSI.cyan))
                                await _main(["gx", "HEAD", "-F"])
                            ask_question("\nPress Enter to return to menu...")
                        elif choice == "3":
                            if not is_repo:
                                print(colorize("Error: This command requires a Git repository.", ANSI.red))
                            else:
                                print(colorize("=== Plan Commits for Working Tree ===\n", ANSI.bold + ANSI.cyan))
                                await _main(["gx", "--commit"])
                                apply_choice = ask_question("\nWould you like to execute the commit plan? (yes/no) > ")
                                if apply_choice.lower() == "yes":
                                    await _main(["gx", "--commit", "--execute"])
                            ask_question("\nPress Enter to return to menu...")
                        elif choice == "4":
                            if not is_repo:
                                print(colorize("Error: This command requires a Git repository.", ANSI.red))
                            else:
                                print(colorize("=== Interactive Commit Splitting ===\n", ANSI.bold + ANSI.cyan))
                                ref = ask_question("Enter commit ref to split [HEAD] > ")
                                if not ref:
                                    ref = "HEAD"
                                await _main(["gx", ref, "--split"])
                                apply_choice = ask_question("\nWould you like to execute the split plan? (yes/no) > ")
                                if apply_choice.lower() == "yes":
                                    await _main(["gx", ref, "--split", "--interactive", "--execute"])
                            ask_question("\nPress Enter to return to menu...")
                        elif choice == "5":
                            if not is_repo:
                                print(colorize("Error: This command requires a Git repository.", ANSI.red))
                            else:
                                print(colorize("=== Search Commit History ===\n", ANSI.bold + ANSI.cyan))
                                print("Select search type:")
                                print("  1. Semantic")
                                print("  2. Pattern")
                                print("  3. Code")
                                stype_choice = ask_question("\nChoose type (1-3) > ")
                                stype = "semantic"
                                if stype_choice == "2":
                                    stype = "pattern"
                                elif stype_choice == "3":
                                    stype = "code"
                                
                                query = ask_question("Enter search query > ")
                                if query:
                                    await _main(["gx", "search", stype, query])
                                else:
                                    print("Query cannot be empty.")
                            ask_question("\nPress Enter to return to menu...")
                        elif choice == "6":
                            print(colorize("=== Usage and Cache Stats ===\n", ANSI.bold + ANSI.cyan))
                            print(format_usage_stats(get_usage_stats()))
                            print("\n")
                            stats = get_cache_stats()
                            print("\n".join([
                                "Cache Stats",
                                f"Entries: {stats['entryCount']}",
                                f"Size: {stats['totalSizeBytes']} bytes",
                                f"Oldest: {stats['oldestEntryIso'] or 'n/a'}",
                                f"Newest: {stats['newestEntryIso'] or 'n/a'}"
                            ]))
                            ask_question("\nPress Enter to return to menu...")
                        elif choice == "7":
                            run_config_wizard(cwd)
                        elif choice == "8":
                            if not is_repo:
                                print(colorize("Error: This command requires a Git repository.", ANSI.red))
                            else:
                                print(colorize("=== Install Git Hooks ===\n", ANSI.bold + ANSI.cyan))
                                print("Select hook to install:")
                                print("  1. post-commit")
                                print("  2. post-merge")
                                print("  3. pre-push")
                                hook_choice = ask_question("\nChoose hook (1-3) > ")
                                hook_name = "post-commit"
                                if hook_choice == "2":
                                    hook_name = "post-merge"
                                elif hook_choice == "3":
                                    hook_name = "pre-push"
                                await _main(["gx", "install-hook", hook_name])
                            ask_question("\nPress Enter to return to menu...")
                        elif choice == "9":
                            print(colorize("\n\n  Goodbye!", ANSI.bold + ANSI.green))
                            break
                    except Exception as e:
                        print(colorize(f"\nError executing command: {str(e)}", ANSI.red))
                        ask_question("\nPress Enter to return to menu...")
                    
                    sys.stdout.write("\033[?25l\033[H\033[J")
                    sys.stdout.flush()
            
            frame += 1
            
    finally:
        sys.stdout.write("\033[?25h\n")
        sys.stdout.flush()
        
    return 0

def main(argv: List[str] = None) -> int:
    import asyncio
    try:
        return asyncio.run(_main(argv))
    except (KeyboardInterrupt, SystemExit):
        return 130

async def _main(argv: List[str] = None) -> int:
    if argv is None:
        argv = sys.argv

    cwd = os.getcwd()
    parsed = parse_args(argv)
    has_no_command_or_flags = len(argv[1:]) == 0

    load_env_file(cwd)
    config = load_config(cwd)
    apply_config_environment(config)

    if parsed.get("version"):
        print(CLI_VERSION)
        return 0

    if parsed.get("cost"):
        print(format_usage_stats(get_usage_stats()))
        return 0

    if parsed.get("help"):
        print_help()
        return 0

    if has_no_command_or_flags:
        if not is_configured(cwd):
            print(colorize("\nNo provider or API key configured. Launching Configuration Wizard...", ANSI.bold + ANSI.yellow))
            run_config_wizard(cwd)
            if not is_configured(cwd):
                print(colorize("\nProvider not configured. Exiting.", ANSI.red))
                return 1
        return await run_tui(cwd)

    if parsed.get("configCommand"):
        try:
            return handle_config_command(parsed)
        except Exception as e:
            print(f"Error: {str(e)}", file=sys.stderr)
            return 1

    if parsed.get("cacheCommand"):
        try:
            return handle_cache_command(parsed)
        except Exception as e:
            print(f"Error: {str(e)}", file=sys.stderr)
            return 1

    if parsed.get("nativeGitCommand"):
        return run_native_git_passthrough(parsed["nativeGitArgs"], cwd)

    if not is_git_repository(cwd):
        print("gitxplain must be run inside a Git repository.", file=sys.stderr)
        return 1

    if parsed.get("installHook"):
        hook_path = install_hook(cwd, parsed.get("hookName", "post-commit"))
        print(f"Installed {parsed.get('hookName')} hook at {hook_path}")
        return 0

    if parsed.get("log"):
        print(get_repository_log(cwd))
        return 0

    if parsed.get("status"):
        print(get_repository_status(cwd))
        return 0

    if parsed.get("releaseCommand"):
        if parsed.get("releaseAction") != "status":
            print(f"Unknown release subcommand: {parsed.get('releaseAction')}", file=sys.stderr)
            return 1
        print(format_release_status(build_release_status(cwd)))
        return 0

    if parsed.get("pipelineCommand"):
        return await run_pipeline_command(cwd)

    if parsed.get("searchCommand"):
        try:
            return await handle_search_command(parsed, cwd, config)
        except Exception as e:
            print(f"Error: {str(e)}", file=sys.stderr)
            return 1

    if (
        parsed.get("addCommand") or
        parsed.get("removeCommand") or
        parsed.get("deleteCommand") or
        parsed.get("binCommand") or
        parsed.get("popCommand") or
        parsed.get("pullCommand") or
        parsed.get("pushCommand")
    ):
        sub_name = parsed["subcommand"]
        if not parsed.get("popCommand") and not parsed.get("binCommand") and not parsed.get("pullCommand") and not parsed.get("removeHardCommand") and len(parsed["actionPaths"]) == 0:
            if not parsed.get("pushCommand"):
                print(f'Error: No paths provided for "{sub_name}".', file=sys.stderr)
                return 1

        if parsed.get("addCommand"):
            git_add_files(parsed["actionPaths"], cwd)
            print(f"Staged {', '.join(parsed['actionPaths'])}.")
            return 0

        if parsed.get("removeCommand"):
            if parsed.get("removeHardCommand"):
                git_reset_hard("HEAD", cwd)
                print("Hard reset to HEAD.")
                return 0
            git_restore_staged(parsed["actionPaths"], cwd)
            print(f"Unstaged {', '.join(parsed['actionPaths'])}.")
            return 0

        if parsed.get("deleteCommand"):
            delete_paths(parsed["actionPaths"], cwd)
            print(f"Deleted {', '.join(parsed['actionPaths'])}.")
            return 0

        if parsed.get("binCommand"):
            git_reset_soft(cwd)
            print("Soft reset HEAD~1 and kept your changes.")
            return 0

        if parsed.get("popCommand"):
            stash_ref = resolve_stash_ref(parsed["stashIndex"])
            from .services.git import git_stash_pop
            git_stash_pop(parsed["stashIndex"], cwd)
            print(f"Popped {stash_ref}.")
            return 0

        if parsed.get("pullCommand"):
            git_pull(cwd, parsed["pullRemote"], parsed["pullBranch"])
            rem_str = f" from {parsed['pullRemote']}" if parsed['pullRemote'] else ""
            br_str = f" {parsed['pullBranch']}" if parsed['pullBranch'] else ""
            print(f"Pulled{rem_str}{br_str}.")
            return 0

        git_push(cwd, parsed["pushRemote"], parsed["pushBranch"])
        rem_str = f" to {parsed['pushRemote']}" if parsed['pushRemote'] else ""
        br_str = f" {parsed['pushBranch']}" if parsed['pushBranch'] else ""
        print(f"Pushed{rem_str}{br_str}.")
        return 0

    runtime_options = resolve_runtime_options(parsed, config)
    mode = parsed.get("mode") or resolve_configured_analysis_mode(config)

    if mode == "commit":
        commit_data = fetch_working_tree_data(cwd)
        if len(commit_data.get("filesChanged", [])) == 0 or commit_data.get("diff") == "":
            print("Working tree is clean. Nothing to commit.")
            return 0

        res = generate_explanation({
            "mode": "commit",
            "commitData": commit_data,
            "providerOverride": runtime_options["provider"],
            "modelOverride": runtime_options["model"],
            "maxDiffLines": runtime_options["maxDiffLines"],
            "noCache": runtime_options["noCache"],
            "stream": False
        })
        explanation = res["explanation"]
        response_meta = res["responseMeta"]
        prompt_meta = res["promptMeta"]

        plan = reconcile_commit_plan(parse_commit_plan(explanation), cwd)

        if not plan.get("reason_to_commit") or len(plan.get("commits", [])) == 0:
            print("No meaningful commit grouping recommended.")
            return 0

        print(format_commit_plan(plan))

        if parsed.get("execute") and not parsed.get("dryRun"):
            confirmed = ask_question("\nThis will create new commits from your working tree changes. Continue? (yes/no) > ")
            if confirmed.lower() != "yes":
                print("Aborted.")
                return 0

            execute_commit_plan(plan, cwd)
            print(f"\nCommit complete. Created {len(plan['commits'])} commits.")
        else:
            print("\nThis is a preview. Run with --execute to apply the commit plan.")

        if runtime_options["verbose"]:
            sys.stdout.write(format_footer({"responseMeta": response_meta, "promptMeta": prompt_meta, "options": runtime_options}))
        return 0

    if mode == "merge" or parsed.get("merge"):
        if parsed.get("commitRef"):
            print("Error: --merge works from the current branch and does not accept a commit ref.", file=sys.stderr)
            return 1

        plan = finalize_release_merge_plan(build_release_merge_plan(cwd))
        if len(plan.get("windows", [])) == 0:
            print("No unreleased release commits detected. Nothing to merge.")
            return 0

        print(format_release_merge_plan(plan))

        if parsed.get("execute") and not parsed.get("dryRun"):
            confirmed = ask_question(f"\nThis will create {len(plan['windows'])} release commit(s) on {plan['releaseBranch']}. Continue? (yes/no) > ")
            if confirmed.lower() != "yes":
                print("Aborted.")
                return 0

            execute_release_merge(plan, cwd)
            print(f"\nRelease promotion complete. Created {len(plan['windows'])} release commit(s) on {plan['releaseBranch']}.")
        else:
            print(f"\nThis is a preview. Run with --execute to create release commits on {plan['releaseBranch']}.")
        return 0

    if mode == "tag" or parsed.get("tag"):
        if parsed.get("commitRef"):
            print("Error: --tag works from the current branch and does not accept a commit ref.", file=sys.stderr)
            return 1

        plan = finalize_release_tag_plan(build_release_tag_plan(cwd))
        if len(plan.get("tags", [])) == 0:
            print("No unreleased release tags detected. Nothing to tag.")
            return 0

        print(format_release_tag_plan(plan))

        if parsed.get("execute") and not parsed.get("dryRun"):
            confirmed = ask_question(f"\nThis will create {len(plan['tags'])} release tag(s). Continue? (yes/no) > ")
            if confirmed.lower() != "yes":
                print("Aborted.")
                return 0

            execute_release_tag_plan(plan, cwd)
            print(f"\nRelease tagging complete. Created {len(plan['tags'])} release tag(s).")
        else:
            print("\nThis is a preview. Run with --execute to create release tags.")
        return 0

    target_ref = resolve_target_ref(parsed, cwd)

    if mode == "blame":
        blame_file = parsed.get("blameFile")
        if not blame_file:
            print("Error: --blame requires a file path.", file=sys.stderr)
            return 1

        commit_data = fetch_blame_data(blame_file, cwd)
        can_stream = runtime_options["stream"] and runtime_options["format"] == "plain"
        stream_started = False

        if runtime_options["stream"] and not can_stream and not runtime_options["quiet"]:
            print(f"Streaming is only supported with plain output. Ignoring --stream for {runtime_options['format']} format.", file=sys.stderr)

        def on_start_cb(start_data):
            nonlocal stream_started
            if not runtime_options["quiet"] and not stream_started:
                sys.stdout.write(
                    format_preamble({
                        "mode": "blame",
                        "commitData": commit_data,
                        "promptMeta": start_data["promptMeta"],
                        "options": runtime_options
                    })
                )
                stream_started = True

        res = generate_explanation({
            "mode": "blame",
            "commitData": commit_data,
            "providerOverride": runtime_options["provider"],
            "modelOverride": runtime_options["model"],
            "maxDiffLines": runtime_options["maxDiffLines"],
            "noCache": runtime_options["noCache"],
            "stream": can_stream,
            "onStart": on_start_cb if can_stream else None,
            "onChunk": (lambda chunk: sys.stdout.write(chunk)) if can_stream else None
        })
        explanation = res["explanation"]
        response_meta = res["responseMeta"]
        prompt_meta = res["promptMeta"]

        rendered_output = render_final_output({
            "runtimeOptions": runtime_options,
            "mode": "blame",
            "commitData": commit_data,
            "explanation": explanation,
            "responseMeta": response_meta,
            "promptMeta": prompt_meta
        })

        if can_stream:
            sys.stdout.write("\n")
            if runtime_options["verbose"]:
                sys.stdout.write(format_footer({"responseMeta": response_meta, "promptMeta": prompt_meta, "options": runtime_options}))
        else:
            print(rendered_output)

        if runtime_options["clipboard"]:
            copy_to_clipboard(rendered_output)
            if not runtime_options["quiet"]:
                print("Copied output to clipboard.", file=sys.stderr)
        return 0

    if mode == "conflict":
        diff_file = parsed.get("diffFile")
        commit_data = fetch_conflict_data(cwd, diff_file)
        can_stream = runtime_options["stream"] and runtime_options["format"] == "plain"
        stream_started = False

        if runtime_options["stream"] and not can_stream and not runtime_options["quiet"]:
            print(f"Streaming is only supported with plain output. Ignoring --stream for {runtime_options['format']} format.", file=sys.stderr)

        def on_start_cb(start_data):
            nonlocal stream_started
            if not runtime_options["quiet"] and not stream_started:
                sys.stdout.write(
                    format_preamble({
                        "mode": "conflict",
                        "commitData": commit_data,
                        "promptMeta": start_data["promptMeta"],
                        "options": runtime_options
                    })
                )
                stream_started = True

        res = generate_explanation({
            "mode": "conflict",
            "commitData": commit_data,
            "providerOverride": runtime_options["provider"],
            "modelOverride": runtime_options["model"],
            "maxDiffLines": runtime_options["maxDiffLines"],
            "noCache": runtime_options["noCache"],
            "stream": can_stream,
            "onStart": on_start_cb if can_stream else None,
            "onChunk": (lambda chunk: sys.stdout.write(chunk)) if can_stream else None
        })
        explanation = res["explanation"]
        response_meta = res["responseMeta"]
        prompt_meta = res["promptMeta"]

        rendered_output = render_final_output({
            "runtimeOptions": runtime_options,
            "mode": "conflict",
            "commitData": commit_data,
            "explanation": explanation,
            "responseMeta": response_meta,
            "promptMeta": prompt_meta
        })

        if can_stream:
            sys.stdout.write("\n")
            if runtime_options["verbose"]:
                sys.stdout.write(format_footer({"responseMeta": response_meta, "promptMeta": prompt_meta, "options": runtime_options}))
        else:
            print(rendered_output)

        if runtime_options["clipboard"]:
            copy_to_clipboard(rendered_output)
            if not runtime_options["quiet"]:
                print("Copied output to clipboard.", file=sys.stderr)
        return 0

    if mode == "stash":
        commit_data = fetch_stash_data(parsed.get("stashRef"), cwd, parsed.get("diffFile"))
        can_stream = runtime_options["stream"] and runtime_options["format"] == "plain"
        stream_started = False

        if runtime_options["stream"] and not can_stream and not runtime_options["quiet"]:
            print(f"Streaming is only supported with plain output. Ignoring --stream for {runtime_options['format']} format.", file=sys.stderr)

        def on_start_cb(start_data):
            nonlocal stream_started
            if not runtime_options["quiet"] and not stream_started:
                sys.stdout.write(
                    format_preamble({
                        "mode": "stash",
                        "commitData": commit_data,
                        "promptMeta": start_data["promptMeta"],
                        "options": runtime_options
                    })
                )
                stream_started = True

        res = generate_explanation({
            "mode": "stash",
            "commitData": commit_data,
            "providerOverride": runtime_options["provider"],
            "modelOverride": runtime_options["model"],
            "maxDiffLines": runtime_options["maxDiffLines"],
            "noCache": runtime_options["noCache"],
            "stream": can_stream,
            "onStart": on_start_cb if can_stream else None,
            "onChunk": (lambda chunk: sys.stdout.write(chunk)) if can_stream else None
        })
        explanation = res["explanation"]
        response_meta = res["responseMeta"]
        prompt_meta = res["promptMeta"]

        rendered_output = render_final_output({
            "runtimeOptions": runtime_options,
            "mode": "stash",
            "commitData": commit_data,
            "explanation": explanation,
            "responseMeta": response_meta,
            "promptMeta": prompt_meta
        })

        if can_stream:
            sys.stdout.write("\n")
            if runtime_options["verbose"]:
                sys.stdout.write(format_footer({"responseMeta": response_meta, "promptMeta": prompt_meta, "options": runtime_options}))
        else:
            print(rendered_output)

        if runtime_options["clipboard"]:
            copy_to_clipboard(rendered_output)
            if not runtime_options["quiet"]:
                print("Copied output to clipboard.", file=sys.stderr)
        return 0

    if not target_ref:
        print_help()
        return 1

    diff_file = parsed.get("diffFile")
    commit_data = fetch_commit_data_for_file(target_ref, diff_file, cwd) if diff_file else fetch_commit_data(target_ref, cwd)

    if mode == "split":
        if commit_data.get("analysisType") != "commit":
            print("Error: --split only supports analyzing a single commit.", file=sys.stderr)
            return 1

        res = generate_explanation({
            "mode": "split",
            "commitData": commit_data,
            "providerOverride": runtime_options["provider"],
            "modelOverride": runtime_options["model"],
            "maxDiffLines": runtime_options["maxDiffLines"],
            "noCache": runtime_options["noCache"],
            "stream": False
        })
        explanation = res["explanation"]
        response_meta = res["responseMeta"]
        prompt_meta = res["promptMeta"]

        plan = reconcile_split_plan(parse_split_plan(explanation), commit_data.get("filesChanged", []))

        if not plan.get("reason_to_split") or len(plan.get("commits", [])) == 0:
            print("This commit is already atomic. No split recommended.")
            return 0

        print(format_split_plan(plan))

        if parsed.get("execute") and not parsed.get("dryRun"):
            reviewed_plan = await review_split_plan_interactively(plan) if parsed.get("interactive") else plan
            if reviewed_plan is None:
                print("Aborted.")
                return 0

            if parsed.get("interactive"):
                print("")
                print(format_split_plan(reviewed_plan))

            validate_split_execution_target(commit_data["commitId"], cwd)
            confirmed = ask_question("\nThis will rewrite git history. Continue? (yes/no) > ")
            if confirmed.lower() != "yes":
                print("Aborted.")
                return 0

            execute_split(reviewed_plan, commit_data["commitId"], cwd)
            print(f"\nSplit complete. Created {len(reviewed_plan['commits'])} commits.")
        else:
            print("\nThis is a preview. Run with --execute to apply the split.")

        if runtime_options["verbose"]:
            sys.stdout.write(format_footer({"responseMeta": response_meta, "promptMeta": prompt_meta, "options": runtime_options}))
        return 0

    can_stream = runtime_options["stream"] and runtime_options["format"] == "plain"
    stream_started = False

    if runtime_options["stream"] and not can_stream and not runtime_options["quiet"]:
        print(f"Streaming is only supported with plain output. Ignoring --stream for {runtime_options['format']} format.", file=sys.stderr)

    def on_start_cb(start_data):
        nonlocal stream_started
        if not runtime_options["quiet"] and not stream_started:
            sys.stdout.write(
                format_preamble({
                    "mode": mode,
                    "commitData": commit_data,
                    "promptMeta": start_data["promptMeta"],
                    "options": runtime_options
                })
            )
            stream_started = True

    res = generate_explanation({
        "mode": mode,
        "commitData": commit_data,
        "providerOverride": runtime_options["provider"],
        "modelOverride": runtime_options["model"],
        "maxDiffLines": runtime_options["maxDiffLines"],
        "noCache": runtime_options["noCache"],
        "stream": can_stream,
        "onStart": on_start_cb if can_stream else None,
        "onChunk": (lambda chunk: sys.stdout.write(chunk)) if can_stream else None
    })
    explanation = res["explanation"]
    response_meta = res["responseMeta"]
    prompt_meta = res["promptMeta"]

    if can_stream:
        sys.stdout.write("\n")
        if runtime_options["verbose"]:
            sys.stdout.write(format_footer({"responseMeta": response_meta, "promptMeta": prompt_meta, "options": runtime_options}))
        
        rendered_output = render_final_output({
            "runtimeOptions": runtime_options,
            "mode": mode,
            "commitData": commit_data,
            "explanation": explanation,
            "responseMeta": response_meta,
            "promptMeta": prompt_meta
        })
    else:
        rendered_output = render_final_output({
            "runtimeOptions": runtime_options,
            "mode": mode,
            "commitData": commit_data,
            "explanation": explanation,
            "responseMeta": response_meta,
            "promptMeta": prompt_meta
        })
        print(rendered_output)

    if runtime_options["clipboard"]:
        copy_to_clipboard(rendered_output)
        if not runtime_options["quiet"]:
            print("Copied output to clipboard.", file=sys.stderr)

    return 0

if __name__ == "__main__":
    sys.exit(main())
