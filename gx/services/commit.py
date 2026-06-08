import json
import re
from typing import Any, Dict, List, Optional, Set
from .git import (
    delete_paths,
    fetch_working_tree_data,
    get_current_head_sha,
    git_add_all,
    git_add_files,
    git_commit,
    git_reset_hard,
    git_stash_apply,
    git_stash_drop,
    git_stash_push,
    git_unstage_all,
    get_latest_stash_ref,
    has_staged_changes,
    is_working_tree_clean,
    path_exists_in_ref,
    resolve_tree_sha,
    write_current_index_tree
)
from .color import ANSI, colorize

def extract_json_payload(explanation: str) -> str:
    fenced_match = re.search(r'```[A-Za-z0-9_-]*\s*([\s\S]*?)\s*```', explanation)
    if fenced_match:
        return fenced_match.group(1).strip()

    start_index = explanation.find("{")
    end_index = explanation.rfind("}")

    if start_index == -1 or end_index == -1 or end_index < start_index:
        raise RuntimeError("Failed to parse commit plan: no JSON object found in model response.")

    return explanation[start_index:end_index + 1]

def is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and value.strip() != ""

def strip_markdown(text: str) -> str:
    res = text
    res = re.sub(r'`([^`]+)`', r'\1', res)
    res = re.sub(r'\*\*([^*]+)\*\*', r'\1', res)
    res = re.sub(r'__([^_]+)__', r'\1', res)
    res = re.sub(r'\*([^*]+)\*', r'\1', res)
    res = re.sub(r'_([^_]+)_', r'\1', res)
    return res.strip()

def parse_files_line(value: str) -> List[str]:
    return [strip_markdown(file).strip() for file in re.split(r'[,\n]', value) if strip_markdown(file).strip()]

def parse_text_commit_plan(explanation: str) -> Dict[str, Any]:
    lines = [line.rstrip() for line in explanation.splitlines()]
    commits = []
    working_tree_summary = None
    reason_to_commit = None
    current_commit = None

    def push_current_commit():
        nonlocal current_commit
        if not current_commit:
            return
        commits.append({
            "order": current_commit["order"],
            "message": current_commit["message"],
            "files": current_commit["files"],
            "description": current_commit["description"]
        })
        current_commit = None

    for raw_line in lines:
        line = strip_markdown(raw_line.strip())
        if line == "":
            continue

        if re.match(r'^(working tree summary|summary)\s*:', line, re.IGNORECASE):
            working_tree_summary = re.sub(r'^(working tree summary|summary)\s*:', '', line, flags=re.IGNORECASE).strip()
            continue

        if re.match(r'^(reason to commit|reason)\s*:', line, re.IGNORECASE):
            reason_to_commit = re.sub(r'^(reason to commit|reason)\s*:', '', line, flags=re.IGNORECASE).strip() or None
            continue

        commit_match = re.match(r'^(?:[-*]\s*)?(\d+)\.\s+(.+)$', line)
        if commit_match:
            push_current_commit()
            current_commit = {
                "order": int(commit_match.group(1)),
                "message": commit_match.group(2).strip(),
                "files": [],
                "description": ""
            }
            continue

        if not current_commit:
            continue

        if re.match(r'^files?\s*:', line, re.IGNORECASE):
            files_content = re.sub(r'^files?\s*:', '', line, flags=re.IGNORECASE)
            current_commit["files"].extend(parse_files_line(files_content))
            continue

        if re.match(r'^(why|description)\s*:', line, re.IGNORECASE):
            current_commit["description"] = re.sub(r'^(why|description)\s*:', '', line, flags=re.IGNORECASE).strip()
            continue

        if current_commit["description"]:
            current_commit["description"] = f"{current_commit['description']} {line}".strip()

    push_current_commit()

    if not working_tree_summary or len(commits) == 0:
        raise RuntimeError("Failed to parse commit plan: no JSON object found in model response.")

    return {
        "working_tree_summary": working_tree_summary,
        "reason_to_commit": reason_to_commit,
        "commits": commits
    }

def validate_commit_entry(entry: Any, index: int) -> None:
    if not isinstance(entry, dict):
        raise RuntimeError(f"Failed to parse commit plan: commit {index + 1} must be an object.")

    if not isinstance(entry.get("order"), int):
        raise RuntimeError(f"Failed to parse commit plan: commit {index + 1} is missing a numeric order.")

    if not is_non_empty_string(entry.get("message")):
        raise RuntimeError(f"Failed to parse commit plan: commit {index + 1} is missing a message.")

    if not isinstance(entry.get("files"), list) or not all(is_non_empty_string(f) for f in entry["files"]):
        raise RuntimeError(f"Failed to parse commit plan: commit {index + 1} must include a files array.")

    if not is_non_empty_string(entry.get("description")):
        raise RuntimeError(f"Failed to parse commit plan: commit {index + 1} is missing a description.")

def validate_unique_file_assignments(commits: List[Dict[str, Any]], error_prefix: str) -> None:
    seen_files = {}
    for commit in commits:
        for file in commit.get("files", []):
            previous_order = seen_files.get(file)
            if previous_order is not None:
                raise RuntimeError(
                    f"{error_prefix}: file \"{file}\" appears in both commit {previous_order} and commit {commit['order']}."
                )
            seen_files[file] = commit["order"]

def sort_plan_commits(plan: Dict[str, Any]) -> List[Dict[str, Any]]:
    return sorted(plan.get("commits", []), key=lambda x: x.get("order", 0))

def get_plan_files(plan: Dict[str, Any]) -> List[str]:
    files = []
    seen = set()
    for commit in sort_plan_commits(plan):
        for file in commit.get("files", []):
            if file not in seen:
                seen.add(file)
                files.append(file)
    return files

def normalize_commit_plan(plan: Dict[str, Any]) -> Dict[str, Any]:
    seen_files = set()
    normalized_commits = []
    deduped_files = []

    for commit in sort_plan_commits(plan):
        files = []
        for file in commit.get("files", []):
            if file in seen_files:
                deduped_files.append(file)
                continue
            seen_files.add(file)
            files.append(file)

        if len(files) == 0:
            continue

        normalized_commits.append({
            **commit,
            "files": files
        })

    warnings = list(plan.get("warnings", []))
    if deduped_files:
        unique_deduped = sorted(list(set(deduped_files)))
        warnings.append(
            f"Duplicate file assignments were removed from later commit groups: {', '.join(unique_deduped)}."
        )

    return {
        **plan,
        "commits": [
            {**commit, "order": idx + 1} for idx, commit in enumerate(normalized_commits)
        ],
        "warnings": warnings
    }

def summarize_file_kinds(files: List[str]) -> Dict[str, str]:
    if all(file.startswith("test/") or file.endswith(".test.js") or file.endswith("_test.py") for file in files):
        return {
            "message": "test: include remaining test updates",
            "description": "Captures remaining test file changes that were not assigned to an earlier commit."
        }

    if all(file.startswith("docs/") or file.lower() == "readme.md" for file in files):
        return {
            "message": "docs: include remaining documentation updates",
            "description": "Captures remaining documentation changes that were not assigned to an earlier commit."
        }

    return {
        "message": "chore: include remaining working tree changes",
        "description": "Captures files that were changed in the working tree but were not assigned to an earlier commit group."
    }

def build_coverage_details(plan: Dict[str, Any], cwd: str) -> Dict[str, Any]:
    working_tree_data = fetch_working_tree_data(cwd)
    changed_files = set(working_tree_data.get("filesChanged", []))
    planned_files = set(get_plan_files(plan))

    return {
        "changedFiles": working_tree_data.get("filesChanged", []),
        "missingFiles": [file for file in changed_files if file not in planned_files],
        "extraFiles": [file for file in planned_files if file not in changed_files]
    }

def reconcile_commit_plan(plan: Dict[str, Any], cwd: str) -> Dict[str, Any]:
    details = build_coverage_details(plan, cwd)
    missing_files = details["missingFiles"]
    extra_files = details["extraFiles"]

    warnings = list(plan.get("warnings", []))
    commits = []
    for commit in sort_plan_commits(plan):
        commits.append({
            **commit,
            "files": [f for f in commit.get("files", []) if f not in extra_files]
        })
    commits = [c for c in commits if len(c["files"]) > 0]

    if extra_files:
        warnings.append(f"Files not present in the working tree were removed from the plan: {', '.join(extra_files)}.")

    if missing_files:
        fallback = summarize_file_kinds(missing_files)
        warnings.append(f"Missing files were added to a final fallback commit: {', '.join(missing_files)}.")
        commits.append({
            "order": len(commits) + 1,
            "message": fallback["message"],
            "files": missing_files,
            "description": fallback["description"]
        })

    return {
        **plan,
        "commits": [{**commit, "order": idx + 1} for idx, commit in enumerate(commits)],
        "warnings": warnings
    }

def validate_plan_coverage(plan: Dict[str, Any], cwd: str) -> None:
    details = build_coverage_details(plan, cwd)
    missing_files = details["missingFiles"]
    extra_files = details["extraFiles"]

    if len(missing_files) == 0 and len(extra_files) == 0:
        return

    parts = []
    if missing_files:
        parts.append(f"Missing files: {', '.join(missing_files)}")
    if extra_files:
        parts.append(f"Unexpected files: {', '.join(extra_files)}")

    raise RuntimeError(f"Commit plan must cover each changed file exactly once. {'. '.join(parts)}")

def get_files_absent_from_ref(files: List[str], ref: str, cwd: str) -> List[str]:
    return [file for file in files if not path_exists_in_ref(ref, file, cwd)]

def build_recovery_message(original_head_sha: str, stash_ref: Optional[str]) -> str:
    lines = [
        "Commit execution failed. To recover:",
        f"- Reset back to the original HEAD with `git reset --hard {original_head_sha}`"
    ]
    if stash_ref:
        lines.append(f"- Reapply your original working tree with `git stash apply --index {stash_ref}`")
    return "\n".join(lines)

def parse_commit_plan(explanation: str) -> Dict[str, Any]:
    try:
        parsed = json.loads(extract_json_payload(explanation))
    except Exception as error:
        try:
            parsed = parse_text_commit_plan(explanation)
        except Exception:
            raise RuntimeError(f"Failed to parse commit plan JSON: {str(error)}")

    if not isinstance(parsed, dict):
        raise RuntimeError("Failed to parse commit plan: top-level JSON must be an object.")

    if "working_tree_summary" not in parsed or not isinstance(parsed["working_tree_summary"], str):
        raise RuntimeError("Failed to parse commit plan: missing working_tree_summary string.")

    if "reason_to_commit" not in parsed or (parsed["reason_to_commit"] is not None and not isinstance(parsed["reason_to_commit"], str)):
        raise RuntimeError("Failed to parse commit plan: reason_to_commit must be a string or null.")

    if "commits" not in parsed or not isinstance(parsed["commits"], list):
        raise RuntimeError("Failed to parse commit plan: commits must be an array.")

    for idx, entry in enumerate(parsed["commits"]):
        validate_commit_entry(entry, idx)

    return normalize_commit_plan(parsed)

def format_commit_plan(plan: Dict[str, Any]) -> str:
    lines = [
        colorize("Commit Plan", ANSI.bold + ANSI.cyan),
        f"{colorize('Working Tree Summary:', ANSI.bold + ANSI.cyan)} {plan.get('working_tree_summary')}",
        f"{colorize('Reason To Commit:', ANSI.bold + ANSI.cyan)} {plan.get('reason_to_commit') or 'No commit needed'}"
    ]

    warnings = plan.get("warnings", [])
    if warnings:
        for warning in warnings:
            lines.append(f"{colorize('Warning:', ANSI.bold + ANSI.yellow)} {warning}")

    commits = plan.get("commits", [])
    if not commits:
        lines.append(colorize("No commit recommended.", ANSI.green))
        return "\n".join(lines)

    for commit in sort_plan_commits(plan):
        lines.append("")
        lines.append(colorize(f"{commit['order']}. {commit['message']}", ANSI.bold + ANSI.yellow))
        lines.append(f"{colorize('Files:', ANSI.bold + ANSI.cyan)} {', '.join(commit.get('files', []))}")
        lines.append(f"{colorize('Why:', ANSI.bold + ANSI.cyan)} {commit.get('description')}")

    return "\n".join(lines)

def execute_commit_plan(plan: Dict[str, Any], cwd: str) -> None:
    if is_working_tree_clean(cwd):
        raise RuntimeError("Working tree is already clean. Nothing to commit.")

    validate_plan_coverage(plan, cwd)

    original_head_sha = get_current_head_sha(cwd)
    new_files = get_files_absent_from_ref(get_plan_files(plan), original_head_sha, cwd)
    stash_ref = None

    try:
        git_stash_push("gitxplain-autocommit-backup", cwd)
        stash_ref = get_latest_stash_ref(cwd)

        if not stash_ref:
            raise RuntimeError("Failed to create a backup stash before committing.")

        git_stash_apply(stash_ref, cwd)
        git_add_all(cwd)
        expected_tree_sha = write_current_index_tree(cwd)
        git_unstage_all(cwd)

        for commit in sort_plan_commits(plan):
            git_add_files(commit.get("files", []), cwd)

            if not has_staged_changes(cwd):
                raise RuntimeError(
                    f"Commit plan execution failed: commit {commit['order']} ({commit['message']}) does not stage any new changes."
                )

            git_commit(commit["message"], cwd)

        final_head_tree_sha = resolve_tree_sha("HEAD", cwd)
        if final_head_tree_sha != expected_tree_sha:
            raise RuntimeError(
                "Commit verification failed: the rewritten HEAD tree does not match the original working tree."
            )

        git_stash_drop(stash_ref, cwd)
    except Exception as error:
        git_reset_hard(original_head_sha, cwd)

        if new_files:
            try:
                delete_paths(new_files, cwd)
            except Exception:
                print("Failed to remove temporary untracked files created during commit execution.")

        if stash_ref:
            try:
                git_stash_apply(stash_ref, cwd)
            except Exception:
                print("Failed to restore original working tree from the backup stash.")

        print(str(error))
        print(build_recovery_message(original_head_sha, stash_ref))
        raise RuntimeError("Commit execution aborted.")
