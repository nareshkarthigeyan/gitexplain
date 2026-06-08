import os
import re
from pathlib import Path
from typing import Any, Dict, Tuple

PROMPT_DIR = Path(__file__).resolve().parent.parent / "prompts"

PROMPT_FILES = {
    "full": "master.txt",
    "summary": "summary.txt",
    "issues": "issue.txt",
    "fix": "junior.txt",
    "impact": "impact.txt",
    "lines": "lines.txt",
    "review": "review.txt",
    "security": "security.txt",
    "split": "split.txt",
    "commit": "commit.txt",
    "changelog": "changelog.txt",
    "refactor": "refactor.txt",
    "test-suggest": "test-suggest.txt",
    "pr-description": "pr-description.txt",
    "blame": "blame.txt",
    "stash": "stash.txt",
    "conflict": "conflict.txt",
    "performance": "performance.txt",
    "database": "database.txt",
    "docs": "docs.txt",
    "api-docs": "api-docs.txt",
    "coverage": "coverage.txt",
    "mutation": "mutation.txt"
}

def fill_template(template: str, values: Dict[str, Any]) -> str:
    result = template
    for key, value in values.items():
        result = result.replace(f"{{{{{key}}}}}", str(value))
    return result

def truncate_diff(diff: str, max_diff_lines: int) -> Dict[str, Any]:
    diff_lines = diff.split("\n")

    if len(diff_lines) <= max_diff_lines:
        return {
            "diff": diff,
            "truncated": False,
            "diffLineCount": len(diff_lines),
            "keptDiffLines": len(diff_lines),
            "warning": None
        }

    kept_lines = diff_lines[:max_diff_lines]
    truncated_diff_content = "\n".join(kept_lines) + f"\n\n[Diff truncated: kept {max_diff_lines} of {len(diff_lines)} lines.]"
    return {
        "diff": truncated_diff_content,
        "truncated": True,
        "diffLineCount": len(diff_lines),
        "keptDiffLines": max_diff_lines,
        "warning": f"Diff truncated to {max_diff_lines} of {len(diff_lines)} lines before sending to the model."
    }

def build_range_prelude(commit_data: Dict[str, Any]) -> str:
    if commit_data.get("analysisType") != "range":
        return ""

    commits = commit_data.get("commits", [])
    commit_list_lines = [f"- {commit['hash'][:7]} {commit['subject']}" for commit in commits]
    return (
        "This analysis covers a range of commits rather than a single commit.\n"
        "Treat the output like a changelog or release summary when appropriate.\n"
        f"Commit Count: {commit_data.get('commitCount')}\n"
        f"Commit List:\n" + "\n".join(commit_list_lines) + "\n\n"
    )

def is_diff_metadata_line(line: str) -> bool:
    return (
        line.startswith("diff --git ") or
        line.startswith("index ") or
        line.startswith("--- ") or
        line.startswith("+++ ") or
        line.startswith("@@ ")
    )

def strip_comment_prefix(line: str) -> str:
    # Removes leading comment indicators: //, /*, *, */, #, <!--, -->, ;
    return re.sub(r'^(?://+|/\*+|\*+/?|#+|<!--|-->|;+)', '', line).strip()

def is_comment_like_line(line: str) -> bool:
    trimmed = line.strip()
    if trimmed == "":
        return True
    if re.match(r'^(?://+|/\*+|\*+/?|#+|<!--|-->|;+)', trimmed):
        return True
    return False

def classify_diff(diff: str) -> Dict[str, str]:
    added_or_removed_lines = []
    for line in diff.split("\n"):
        if (line.startswith("+") or line.startswith("-")) and not is_diff_metadata_line(line):
            added_or_removed_lines.append(line[1:])

    if not added_or_removed_lines:
        return {
            "summary": "No content changes detected beyond diff metadata."
        }

    non_comment_lines = []
    for line in added_or_removed_lines:
        if is_comment_like_line(line):
            continue
        if strip_comment_prefix(line) != "":
            non_comment_lines.append(line)

    if not non_comment_lines:
        return {
            "summary": (
                "All changed lines appear to be comments or whitespace. "
                "Treat this as a non-behavioral documentation/annotation update unless the diff proves otherwise."
            )
        }

    return {
        "summary": "Changed lines include executable or data content. Do not assume the edit is comments-only."
    }

def build_prompt(mode: str, commit_data: Dict[str, Any], options: Dict[str, Any] = None) -> Tuple[str, Dict[str, Any]]:
    if options is None:
        options = {}

    filename = PROMPT_FILES.get(mode, PROMPT_FILES["full"])
    prompt_path = PROMPT_DIR / filename

    with open(prompt_path, "r", encoding="utf-8") as f:
        template = f.read()

    max_diff_lines = options.get("maxDiffLines", 800)
    if max_diff_lines is None:
        max_diff_lines = 800

    truncation = truncate_diff(commit_data.get("diff", ""), max_diff_lines)
    diff_classification = classify_diff(truncation["diff"])

    prelude = build_range_prelude(commit_data)
    prompt = fill_template(f"{prelude}{template}", {
        "commit_message": commit_data.get("commitMessage", ""),
        "files_changed": "\n".join(commit_data.get("filesChanged", [])),
        "stats": commit_data.get("stats", ""),
        "diff": truncation["diff"],
        "change_hints": diff_classification["summary"]
    })

    return prompt, {
        "truncated": truncation["truncated"],
        "diffLineCount": truncation["diffLineCount"],
        "keptDiffLines": truncation["keptDiffLines"],
        "warnings": [truncation["warning"]] if truncation["warning"] else []
    }
