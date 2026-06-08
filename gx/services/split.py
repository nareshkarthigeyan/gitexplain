import json
import re
import time
from typing import Any, Dict, List, Optional
from .git import (
    create_commit_from_tree,
    delete_paths,
    get_commit_metadata,
    get_commit_parents,
    get_current_branch_name,
    get_current_head_sha,
    git_cherry_pick,
    git_cherry_pick_abort,
    git_cherry_pick_no_commit,
    git_add_files,
    git_create_branch,
    git_checkout,
    git_checkout_detached,
    git_checkout_orphan,
    git_commit,
    git_delete_branch,
    git_force_branch,
    git_remove_cached_all,
    git_rebase_abort,
    git_rebase_rebase_merges_onto,
    git_reset_hard,
    git_unstage_all,
    has_staged_changes,
    is_ancestor_commit,
    is_working_tree_clean,
    list_commits_after,
    list_commits_after_topo,
    list_files_in_ref,
    resolve_tree_sha,
    run_git_command_unchecked,
    resolve_commit_sha
)
from .color import ANSI, colorize

def extract_json_payload(explanation: str) -> str:
    fenced_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', explanation, re.IGNORECASE)
    if fenced_match:
        return fenced_match.group(1).strip()

    start_index = explanation.find("{")
    end_index = explanation.rfind("}")

    if start_index == -1 or end_index == -1 or end_index < start_index:
        raise RuntimeError("Failed to parse split plan: no JSON object found in model response.")

    return explanation[start_index:end_index + 1]

def is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and value.strip() != ""

def validate_commit_entry(entry: Any, index: int) -> None:
    if not isinstance(entry, dict):
        raise RuntimeError(f"Failed to parse split plan: commit {index + 1} must be an object.")

    if not isinstance(entry.get("order"), int):
        raise RuntimeError(f"Failed to parse split plan: commit {index + 1} is missing a numeric order.")

    if not is_non_empty_string(entry.get("message")):
        raise RuntimeError(f"Failed to parse split plan: commit {index + 1} is missing a message.")

    if not isinstance(entry.get("files"), list) or not all(is_non_empty_string(f) for f in entry["files"]):
        raise RuntimeError(f"Failed to parse split plan: commit {index + 1} must include a files array.")

    if not is_non_empty_string(entry.get("description")):
        raise RuntimeError(f"Failed to parse split plan: commit {index + 1} is missing a description.")

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

def normalize_split_plan(plan: Dict[str, Any]) -> Dict[str, Any]:
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
            f"Duplicate file assignments were removed from later split groups: {', '.join(unique_deduped)}."
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
            "description": "Captures remaining test file changes that were not assigned to an earlier split group."
        }

    if all(file.startswith("docs/") or file.lower() == "readme.md" for file in files):
        return {
            "message": "docs: include remaining documentation updates",
            "description": "Captures remaining documentation changes that were not assigned to an earlier split group."
        }

    return {
        "message": "chore: include remaining commit changes",
        "description": "Captures files from the original commit that were not assigned to an earlier split group."
    }

def parse_split_plan(explanation: str) -> Dict[str, Any]:
    try:
        parsed = json.loads(extract_json_payload(explanation))
    except Exception as error:
        raise RuntimeError(f"Failed to parse split plan JSON: {str(error)}")

    if not isinstance(parsed, dict):
        raise RuntimeError("Failed to parse split plan: top-level JSON must be an object.")

    if "original_summary" not in parsed or not isinstance(parsed["original_summary"], str):
        raise RuntimeError("Failed to parse split plan: missing original_summary string.")

    if "reason_to_split" not in parsed or (parsed["reason_to_split"] is not None and not isinstance(parsed["reason_to_split"], str)):
        raise RuntimeError("Failed to parse split plan: reason_to_split must be a string or null.")

    if "commits" not in parsed or not isinstance(parsed["commits"], list):
        raise RuntimeError("Failed to parse split plan: commits must be an array.")

    for idx, entry in enumerate(parsed["commits"]):
        validate_commit_entry(entry, idx)

    return normalize_split_plan(parsed)

def reconcile_split_plan(plan: Dict[str, Any], files_changed: List[str]) -> Dict[str, Any]:
    commit_files = sorted(list(set(files_changed)))
    commit_file_set = set(commit_files)
    planned_files = get_plan_files(plan)
    extra_files = [file for file in planned_files if file not in commit_file_set]
    missing_files = [file for file in commit_files if file not in planned_files]

    warnings = list(plan.get("warnings", []))
    commits = []
    for commit in sort_plan_commits(plan):
        commits.append({
            **commit,
            "files": [f for f in commit.get("files", []) if f not in extra_files]
        })
    commits = [c for c in commits if len(c["files"]) > 0]

    if extra_files:
        warnings.append(f"Files not present in the target commit were removed from the split plan: {', '.join(extra_files)}.")

    if missing_files:
        fallback = summarize_file_kinds(missing_files)
        warnings.append(f"Missing files were added to a final fallback split group: {', '.join(missing_files)}.")
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

def format_split_plan(plan: Dict[str, Any]) -> str:
    lines = [
        colorize("Split Plan", ANSI.bold + ANSI.cyan),
        f"{colorize('Original Summary:', ANSI.bold + ANSI.cyan)} {plan.get('original_summary')}",
        f"{colorize('Reason To Split:', ANSI.bold + ANSI.cyan)} {plan.get('reason_to_split') or 'Already atomic'}"
    ]

    warnings = plan.get("warnings", [])
    if warnings:
        for warning in warnings:
            lines.append(f"{colorize('Warning:', ANSI.bold + ANSI.yellow)} {warning}")

    commits = plan.get("commits", [])
    if not commits:
        lines.append(colorize("No split recommended.", ANSI.green))
        return "\n".join(lines)

    for commit in sort_plan_commits(plan):
        lines.append("")
        lines.append(colorize(f"{commit['order']}. {commit['message']}", ANSI.bold + ANSI.yellow))
        lines.append(f"{colorize('Files:', ANSI.bold + ANSI.cyan)} {', '.join(commit.get('files', []))}")
        lines.append(f"{colorize('Why:', ANSI.bold + ANSI.cyan)} {commit.get('description')}")

    return "\n".join(lines)

def build_recovery_message(original_head_sha: str) -> str:
    return "\n".join([
        "Split execution failed. To recover:",
        f"- Find the original HEAD in `git reflog` (expected SHA: {original_head_sha})",
        f"- Restore it with `git reset --hard {original_head_sha}`"
    ])

def get_dirty_working_tree_summary(cwd: str) -> Optional[str]:
    result = run_git_command_unchecked(["status", "--short"], cwd)
    if result["exitCode"] != 0 or result["stdout"] == "":
        return None

    lines = [line.strip() for line in result["stdout"].splitlines() if line.strip()]
    return "\n".join(lines[:10])

def validate_split_execution_target(
    commit_id: str,
    cwd: str,
    helpers: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    if helpers is None:
        helpers = {
            "resolveCommitSha": resolve_commit_sha,
            "getCurrentHeadSha": get_current_head_sha,
            "getCommitParents": get_commit_parents,
            "isAncestorCommit": is_ancestor_commit
        }

    target_sha = helpers["resolveCommitSha"](commit_id, cwd)
    current_head_sha = helpers["getCurrentHeadSha"](cwd)

    if not helpers["isAncestorCommit"](target_sha, current_head_sha, cwd):
        raise RuntimeError(f"Commit {commit_id} is not reachable from the current HEAD.")

    parents = helpers["getCommitParents"](target_sha, cwd)
    if len(parents) > 1:
        raise RuntimeError("Only non-merge commits can be split. Merge commits have multiple parents.")

    return {
        "targetSha": target_sha,
        "currentHeadSha": current_head_sha,
        "parentSha": parents[0] if parents else None,
        "isHeadTarget": target_sha == current_head_sha
    }

def create_temp_root_split_branch_name() -> str:
    return f"gitxplain-split-root-{int(time.time() * 1000)}"

def restore_original_pointer(original_branch: str, original_head_sha: str, cwd: str) -> None:
    if original_branch == "HEAD":
        git_checkout_detached(original_head_sha, cwd)
        return
    git_checkout(original_branch, cwd)
    git_reset_hard(original_head_sha, cwd)

def finalize_root_split_branch(temp_branch: str, original_branch: str, rewritten_head_sha: str, cwd: str) -> None:
    if original_branch == "HEAD":
        git_checkout_detached(rewritten_head_sha, cwd)
        git_delete_branch(temp_branch, cwd)
        return

    git_force_branch(original_branch, rewritten_head_sha, cwd)
    git_checkout(original_branch, cwd)
    git_delete_branch(temp_branch, cwd)

def replay_descendants_from_original_trees(target_sha: str, original_head_sha: str, split_tip_sha: str, cwd: str) -> str:
    descendant_shas = list_commits_after_topo(target_sha, original_head_sha, cwd)
    rewritten = {target_sha: split_tip_sha}

    for original_sha in descendant_shas:
        original_parents = get_commit_parents(original_sha, cwd)
        rewritten_parents = [rewritten.get(p, p) for p in original_parents]
        tree_sha = resolve_tree_sha(original_sha, cwd)
        metadata = get_commit_metadata(original_sha, cwd)
        rewritten_sha = create_commit_from_tree(tree_sha, rewritten_parents, metadata, cwd)
        rewritten[original_sha] = rewritten_sha

    return rewritten.get(original_head_sha, split_tip_sha)

def execute_split(plan: Dict[str, Any], commit_id: str, cwd: str) -> None:
    target_info = validate_split_execution_target(commit_id, cwd)
    target_sha = target_info["targetSha"]
    current_head_sha = target_info["currentHeadSha"]
    parent_sha = target_info["parentSha"]

    original_head_sha = current_head_sha
    original_target_tree_sha = resolve_tree_sha(target_sha, cwd)
    original_head_tree_sha = resolve_tree_sha("HEAD", cwd)
    ordered_commits = sort_plan_commits(plan)
    original_branch = get_current_branch_name(cwd)

    root_split_temp_branch = None
    root_split_original_branch = None

    try:
        if not is_working_tree_clean(cwd):
            dirty_summary = get_dirty_working_tree_summary(cwd)
            msg = (
                f"Working tree must be clean before executing a split.\nUncommitted changes:\n{dirty_summary}"
                if dirty_summary else "Working tree must be clean before executing a split."
            )
            raise RuntimeError(msg)

        commits_to_replay = list_commits_after(target_sha, original_head_sha, cwd)

        if parent_sha is None:
            temp_branch = create_temp_root_split_branch_name()
            original_head_files = list_files_in_ref("HEAD", cwd)
            root_split_original_branch = original_branch
            root_split_temp_branch = temp_branch

            git_checkout_orphan(temp_branch, cwd)
            git_remove_cached_all(cwd)
            delete_paths(original_head_files, cwd)
            git_cherry_pick_no_commit(target_sha, cwd)

            for commit in ordered_commits:
                git_unstage_all(cwd)
                git_add_files(commit.get("files", []), cwd)

                if not has_staged_changes(cwd):
                    raise RuntimeError(
                        f"Split plan execution failed: commit {commit['order']} ({commit['message']}) does not stage any new changes."
                    )

                git_commit(commit["message"], cwd)
        else:
            git_reset_hard(parent_sha, cwd)
            git_cherry_pick_no_commit(target_sha, cwd)

            for commit in ordered_commits:
                git_unstage_all(cwd)
                git_add_files(commit.get("files", []), cwd)

                if not has_staged_changes(cwd):
                    raise RuntimeError(
                        f"Split plan execution failed: commit {commit['order']} ({commit['message']}) does not stage any new changes."
                    )

                git_commit(commit["message"], cwd)

        split_tip_sha = get_current_head_sha(cwd)
        split_tip_tree_sha = resolve_tree_sha(split_tip_sha, cwd)

        if split_tip_tree_sha != original_target_tree_sha:
            raise RuntimeError(
                "Split verification failed: the split commit stack does not reproduce the original target commit tree."
            )

        rewritten_head_sha = split_tip_sha
        if commits_to_replay:
            rewritten_head_sha = replay_descendants_from_original_trees(target_sha, original_head_sha, split_tip_sha, cwd)

            if root_split_temp_branch:
                finalize_root_split_branch(root_split_temp_branch, root_split_original_branch, rewritten_head_sha, cwd)
            else:
                if original_branch != "HEAD":
                    git_reset_hard(rewritten_head_sha, cwd)
                else:
                    git_checkout_detached(rewritten_head_sha, cwd)
        elif root_split_temp_branch:
            finalize_root_split_branch(root_split_temp_branch, root_split_original_branch, split_tip_sha, cwd)
        elif original_branch == "HEAD":
            git_checkout_detached(split_tip_sha, cwd)

        rewritten_head_tree_sha = resolve_tree_sha("HEAD", cwd)
        if rewritten_head_tree_sha != original_head_tree_sha:
            raise RuntimeError(
                "Split verification failed: the rewritten HEAD tree does not match the original HEAD tree."
            )
    except Exception as error:
        git_cherry_pick_abort(cwd)

        try:
            if root_split_temp_branch:
                restore_original_pointer(root_split_original_branch or "HEAD", original_head_sha, cwd)
                git_delete_branch(root_split_temp_branch, cwd)
            else:
                run_git_command_unchecked(["reset", "--hard", original_head_sha], cwd)
        except Exception:
            run_git_command_unchecked(["reset", "--hard", original_head_sha], cwd)

        print(str(error))
        print(build_recovery_message(original_head_sha))
        raise RuntimeError("Split execution aborted.")
