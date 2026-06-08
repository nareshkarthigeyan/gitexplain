import datetime
import math
import re
from typing import Any, Dict, List, Optional
from .git import fetch_commit_data, get_repository_log, run_git_command

def parse_log_output(output: str) -> List[Dict[str, str]]:
    if not output:
        return []
    commits = []
    for line in output.splitlines():
        trimmed = line.strip()
        if not trimmed:
            continue
        parts = trimmed.split(" ")
        if len(parts) >= 2:
            sha = parts[0]
            date = parts[1]
            author = " ".join(parts[2:-1]) if len(parts) > 3 else ""
            message = parts[-1] if len(parts) > 2 else ""
            commits.append({
                "sha": sha,
                "date": date,
                "author": author,
                "message": message
            })
    return commits

def filter_by_date_range(commits: List[Dict[str, str]], since: Optional[str], until: Optional[str]) -> List[Dict[str, str]]:
    if not since and not until:
        return commits

    def parse_date(date_str: str) -> Optional[datetime.date]:
        try:
            return datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return None

    since_date = parse_date(since) if since else None
    until_date = parse_date(until) if until else None

    filtered = []
    for commit in commits:
        commit_date = parse_date(commit["date"])
        if not commit_date:
            continue
        if since_date and commit_date < since_date:
            continue
        if until_date and commit_date > until_date:
            continue
        filtered.append(commit)
    return filtered

def calculate_relevance(message: str, keywords: List[str]) -> float:
    message_lower = message.lower()
    score = 0.0
    for keyword in keywords:
        if keyword in message_lower:
            score += len(keyword)
    return score

def fallback_text_search(query: str, commits: List[Dict[str, str]]) -> Dict[str, Any]:
    query_lower = query.lower()
    keywords = [word for word in query_lower.split() if len(word) > 2]

    results = []
    for commit in commits:
        if any(keyword in commit["message"].lower() for keyword in keywords):
            relevance = calculate_relevance(commit["message"], keywords)
            results.append({
                "sha": commit["sha"],
                "message": commit["message"],
                "author": commit["author"],
                "date": commit["date"],
                "relevance": relevance
            })

    # Sort by relevance descending
    results.sort(key=lambda x: x["relevance"], reverse=True)

    return {
        "results": results,
        "query": query,
        "total": len(results),
        "fallback": True
    }

async def semantic_search(query: str, cwd: str, options: Dict[str, Any] = None) -> Dict[str, Any]:
    if options is None:
        options = {}
    limit = options.get("limit", 50)
    author = options.get("author")
    since = options.get("since")
    until = options.get("until")

    log_output = get_repository_log(cwd, limit)
    commits = parse_log_output(log_output)

    if author:
        commits = [c for c in commits if author.lower() in c["author"].lower()]

    commits = filter_by_date_range(commits, since, until)

    if not commits:
        return {
            "results": [],
            "query": query,
            "total": 0
        }

    return fallback_text_search(query, commits)

async def filter_by_file_pattern(commits: List[Dict[str, str]], file_pattern: str, cwd: str) -> List[Dict[str, str]]:
    filtered = []
    for commit in commits:
        try:
            files_raw = run_git_command(["diff", "--name-only", f"{commit['sha']}^..{commit['sha']}"], cwd)
            files = [f.strip() for f in files_raw.splitlines() if f.strip()]
            if file_pattern in files or any(re.search(file_pattern, f) for f in files):
                filtered.append(commit)
        except Exception:
            # Fallback to keep the commit if diff fails
            filtered.append(commit)
    return filtered

async def pattern_search(pattern: str, cwd: str, options: Dict[str, Any] = None) -> Dict[str, Any]:
    if options is None:
        options = {}
    limit = options.get("limit", 50)
    file_pattern = options.get("pattern")
    case_insensitive = options.get("caseInsensitive", False)

    grep_args = ["log", "--all", "--grep", pattern, "--pretty=format:%h %ad %an %s"]
    if limit:
        grep_args.append(f"--max-count={limit}")
    if case_insensitive:
        grep_args.append("--regexp-ignore-case")

    try:
        log_output = run_git_command(grep_args, cwd)
        commits = parse_log_output(log_output)

        if file_pattern:
            commits = await filter_by_file_pattern(commits, file_pattern, cwd)

        results = []
        for commit in commits:
            results.append({
                "sha": commit["sha"],
                "message": commit["message"],
                "author": commit["author"],
                "date": commit["date"],
                "matchType": "message"
            })

        return {
            "results": results,
            "pattern": pattern,
            "total": len(results)
        }
    except Exception as error:
        return {
            "results": [],
            "pattern": pattern,
            "total": 0,
            "error": str(error)
        }

async def code_pattern_search(pattern: str, cwd: str, options: Dict[str, Any] = None) -> Dict[str, Any]:
    if options is None:
        options = {}
    limit = options.get("limit", 20)
    file_type = options.get("fileType")

    grep_args = ["log", "--all", "-S", pattern, "--pretty=format:%h %ad %an %s"]
    if limit:
        grep_args.append(f"--max-count={limit}")
    if file_type:
        grep_args.extend(["--", f"*.{file_type}"])

    try:
        log_output = run_git_command(grep_args, cwd)
        commits = parse_log_output(log_output)

        results_with_diff = []
        # Get diff for first 10 commits
        for commit in commits[:10]:
            try:
                commit_data = fetch_commit_data(commit["sha"], cwd)
                results_with_diff.append({
                    "sha": commit["sha"],
                    "message": commit["message"],
                    "author": commit["author"],
                    "date": commit["date"],
                    "diff": commit_data.get("diff", "")[:500],
                    "matchType": "code"
                })
            except Exception:
                results_with_diff.append({
                    "sha": commit["sha"],
                    "message": commit["message"],
                    "author": commit["author"],
                    "date": commit["date"],
                    "diff": "",
                    "matchType": "code"
                })

        return {
            "results": results_with_diff,
            "pattern": pattern,
            "total": len(commits)
        }
    except Exception as error:
        return {
            "results": [],
            "pattern": pattern,
            "total": 0,
            "error": str(error)
        }

def group_by_time_period(commits: List[Dict[str, str]], granularity: str) -> List[Dict[str, Any]]:
    groups = {}

    def parse_commit_date(date_str: str) -> datetime.datetime:
        try:
            return datetime.datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            return datetime.datetime.utcnow()

    for commit in commits:
        date = parse_commit_date(commit["date"])
        
        if granularity == "hourly":
            key = date.strftime("%Y-%m-%dT%H")
        elif granularity == "daily":
            key = date.strftime("%Y-%m-%d")
        elif granularity == "weekly":
            # Start of week (Sunday)
            week_start = date - datetime.timedelta(days=(date.weekday() + 1) % 7)
            key = week_start.strftime("%Y-%m-%d")
        elif granularity == "monthly":
            key = date.strftime("%Y-%m")
        else:
            key = date.strftime("%Y-%m-%d")

        if key not in groups:
            groups[key] = {
                "period": key,
                "commits": [],
                "count": 0
            }
        groups[key]["commits"].append(commit)
        groups[key]["count"] += 1

    sorted_groups = sorted(groups.values(), key=lambda x: x["period"])
    return sorted_groups

def get_date_range(commits: List[Dict[str, str]]) -> Optional[Dict[str, str]]:
    if not commits:
        return None

    def parse_date(date_str: str) -> datetime.date:
        try:
            return datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return datetime.date.today()

    dates = [parse_date(c["date"]) for c in commits]
    return {
        "start": min(dates).strftime("%Y-%m-%d"),
        "end": max(dates).strftime("%Y-%m-%d")
    }

def calculate_average_per_period(timeline: List[Dict[str, Any]]) -> float:
    if not timeline:
        return 0.0
    total = sum(period["count"] for period in timeline)
    return round(total / len(timeline), 1)

def get_most_active_period(timeline: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not timeline:
        return None
    most_active = timeline[0]
    for period in timeline:
        if period["count"] > most_active["count"]:
            most_active = period
    return most_active

async def author_activity_timeline(author: str, cwd: str, options: Dict[str, Any] = None) -> Dict[str, Any]:
    if options is None:
        options = {}
    since = options.get("since")
    until = options.get("until")
    granularity = options.get("granularity", "daily")

    log_args = ["log", "--all", "--author", author, "--pretty=format:%h %ad %an %s", "--date=iso"]
    if since:
        log_args.append(f"--since={since}")
    if until:
        log_args.append(f"--until={until}")

    try:
        log_output = run_git_command(log_args, cwd)
        commits = parse_log_output(log_output)
        timeline = group_by_time_period(commits, granularity)

        stats = {
            "totalCommits": len(commits),
            "dateRange": get_date_range(commits),
            "averagePerPeriod": calculate_average_per_period(timeline),
            "mostActivePeriod": get_most_active_period(timeline)
        }

        return {
            "author": author,
            "timeline": timeline,
            "stats": stats,
            "granularity": granularity
        }
    except Exception as error:
        return {
            "author": author,
            "timeline": [],
            "stats": None,
            "error": str(error)
        }
