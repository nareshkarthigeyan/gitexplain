import os
import re
import subprocess
import tempfile
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from .color import ANSI, colorize

def run_git_command(args: List[str], cwd: str) -> str:
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as error:
        stderr = error.stderr.strip() if error.stderr else ""
        raise RuntimeError(stderr or f"Git command failed: git {' '.join(args)}")

def run_git_command_with_input(args: List[str], cwd: str, text_input: str) -> str:
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            input=text_input,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as error:
        stderr = error.stderr.strip() if error.stderr else ""
        raise RuntimeError(stderr or f"Git command failed: git {' '.join(args)}")

def run_git_command_with_input_and_env(args: List[str], cwd: str, text_input: str, env: Dict[str, str]) -> str:
    try:
        full_env = {**os.environ, **env}
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            input=text_input,
            capture_output=True,
            text=True,
            env=full_env,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as error:
        stderr = error.stderr.strip() if error.stderr else ""
        raise RuntimeError(stderr or f"Git command failed: git {' '.join(args)}")

def run_git_command_unchecked(args: List[str], cwd: str) -> Dict[str, Any]:
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True
        )
        return {
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "exitCode": result.returncode
        }
    except Exception as e:
        return {
            "stdout": "",
            "stderr": str(e),
            "exitCode": 1
        }

def list_git_subcommands() -> Set[str]:
    try:
        result = subprocess.run(
            ["git", "help", "-a"],
            capture_output=True,
            text=True,
            check=True
        )
        output = result.stdout
    except FileNotFoundError:
        raise RuntimeError("git is not installed or not available in PATH.")
    except subprocess.CalledProcessError as error:
        stderr = error.stderr.strip() if error.stderr else ""
        raise RuntimeError(stderr or "Unable to list git subcommands.")

    subcommands = set()
    for line in output.splitlines():
        match = re.match(r'^\s{3}([a-z0-9][a-z0-9-]*)\s{2,}', line, re.IGNORECASE)
        if match:
            subcommands.add(match.group(1))
    return subcommands

def run_native_git_passthrough(args: List[str], cwd: str) -> int:
    result = subprocess.run(["git"] + args, cwd=cwd)
    return result.returncode

def is_git_repository(cwd: str) -> bool:
    try:
        return run_git_command(["rev-parse", "--is-inside-work-tree"], cwd) == "true"
    except Exception:
        return False

def parse_files_changed(raw: str) -> List[str]:
    return [line.strip() for line in raw.splitlines() if line.strip()]

def parse_stats_line(stats_raw: str) -> str:
    for line in stats_raw.splitlines():
        trimmed = line.strip()
        if re.search(r'changed|insertions?\(\+\)|deletions?\(-\)', trimmed):
            return trimmed
    return "No change statistics available."

def parse_commit_log(log_raw: str) -> List[Dict[str, str]]:
    commits = []
    for line in log_raw.splitlines():
        if not line.strip():
            continue
        parts = line.split("\u001f")
        hsh = parts[0]
        subject = parts[1] if len(parts) > 1 else ""
        body = parts[2] if len(parts) > 2 else ""
        commits.append({"hash": hsh, "subject": subject, "body": body})
    return commits

def build_commit_message(commits: List[Dict[str, str]]) -> str:
    parts = []
    for commit in commits:
        msg = f"{commit['hash'][:7]} {commit['subject']}"
        if commit.get("body"):
            msg += f"\n{commit['body']}"
        parts.append(msg)
    return "\n\n".join(parts)

def is_range_ref(ref: str) -> bool:
    return ".." in ref

def get_default_base_ref(cwd: str) -> str:
    for candidate in ["main", "master", "origin/main", "origin/master"]:
        try:
            run_git_command(["rev-parse", "--verify", candidate], cwd)
            return candidate
        except Exception:
            continue
    raise RuntimeError("Could not detect a default base branch. Pass --branch <base-ref> explicitly.")

def build_branch_range(base_ref: str, cwd: str) -> str:
    merge_base = run_git_command(["merge-base", base_ref, "HEAD"], cwd)
    return f"{merge_base}..HEAD"

def is_working_tree_clean(cwd: str) -> bool:
    result = run_git_command_unchecked(["status", "--porcelain"], cwd)
    if result["exitCode"] != 0:
        raise RuntimeError(result["stderr"] or "Unable to determine working tree status.")
    return result["stdout"] == ""

def resolve_commit_sha(ref: str, cwd: str) -> str:
    return run_git_command(["rev-parse", ref], cwd)

def get_current_head_sha(cwd: str) -> str:
    return run_git_command(["rev-parse", "HEAD"], cwd)

def get_current_branch_name(cwd: str) -> str:
    return run_git_command(["rev-parse", "--abbrev-ref", "HEAD"], cwd)

def resolve_tree_sha(ref: str, cwd: str, runner=None) -> str:
    run_fn = runner if runner else run_git_command
    return run_fn(["rev-parse", f"{ref}^{{tree}}"], cwd)

def get_merge_base(left_ref: str, right_ref: str, cwd: str) -> str:
    return run_git_command(["merge-base", left_ref, right_ref], cwd)

def path_exists_in_ref(ref: str, file_path: str, cwd: str) -> bool:
    result = run_git_command_unchecked(["cat-file", "-e", f"{ref}:{file_path}"], cwd)
    return result["exitCode"] == 0

def git_reset_soft(cwd: str) -> str:
    return run_git_command(["reset", "--soft", "HEAD~1"], cwd)

def git_unstage_all(cwd: str) -> str:
    return run_git_command(["reset", "HEAD", "--", "."], cwd)

def git_add_files(files: List[str], cwd: str) -> str:
    return run_git_command(["add"] + files, cwd)

def git_restore_staged(files: List[str], cwd: str) -> str:
    return run_git_command(["restore", "--staged", "--"] + files, cwd)

def delete_paths(files: List[str], cwd: str) -> None:
    for file in files:
        target_path = Path(cwd).joinpath(file).resolve()
        # Security check to prevent deleting files outside cwd
        if target_path == Path(cwd).resolve() or not str(target_path).startswith(str(Path(cwd).resolve()) + os.sep):
            raise RuntimeError(f"Refusing to delete path outside the repository: {file}")

        if target_path.exists():
            if target_path.is_dir():
                shutil.rmtree(target_path)
            else:
                target_path.unlink()

def git_commit(message: str, cwd: str) -> str:
    return run_git_command(["commit", "-m", message], cwd)

def git_push(cwd: str, remote: Optional[str] = None, branch: Optional[str] = None, runner=None) -> str:
    args = ["push"]
    if remote:
        args.append(remote)
    if branch:
        args.append(branch)
    run_fn = runner if runner else run_git_command
    return run_fn(args, cwd)

def git_pull(cwd: str, remote: Optional[str] = None, branch: Optional[str] = None, runner=None) -> str:
    args = ["pull"]
    if remote:
        args.append(remote)
    if branch:
        args.append(branch)
    run_fn = runner if runner else run_git_command
    return run_fn(args, cwd)

def git_create_annotated_tag(tag_name: str, ref: str, message: str, cwd: str) -> str:
    return run_git_command(["tag", "-a", tag_name, ref, "-m", message], cwd)

def git_delete_tag(tag_name: str, cwd: str) -> str:
    return run_git_command(["tag", "-d", tag_name], cwd)

def list_tags(cwd: str) -> List[str]:
    output = run_git_command(["tag", "--list"], cwd)
    return [line.strip() for line in output.splitlines() if line.strip()]

def list_tag_targets(cwd: str) -> List[Dict[str, str]]:
    result = run_git_command_unchecked(["show-ref", "--tags", "-d"], cwd)
    if result["exitCode"] != 0:
        return []

    output = result["stdout"]
    tag_targets = {}

    for line in output.splitlines():
        trimmed = line.strip()
        if not trimmed:
            continue
        parts = trimmed.split(" ")
        if len(parts) < 2:
            continue
        sha, ref = parts[0], parts[1]
        if not ref.startswith("refs/tags/"):
            continue

        raw_tag_name = ref[len("refs/tags/"):]
        is_dereferenced = raw_tag_name.endswith("^{}")
        tag_name = raw_tag_name[:-3] if is_dereferenced else raw_tag_name
        existing = tag_targets.get(tag_name, {})

        tag_targets[tag_name] = {
            "tagName": tag_name,
            "tagSha": existing.get("tagSha") if is_dereferenced else sha,
            "targetSha": sha if is_dereferenced else existing.get("targetSha", sha)
        }

    return list(tag_targets.values())

def has_staged_changes(cwd: str) -> bool:
    result = run_git_command_unchecked(["diff", "--cached", "--quiet"], cwd)
    if result["exitCode"] == 0:
        return False
    if result["exitCode"] == 1:
        return True
    raise RuntimeError(result["stderr"] or "Unable to determine whether staged changes exist.")

def git_add_all(cwd: str) -> str:
    return run_git_command(["add", "--all"], cwd)

def get_repository_log(cwd: str, limit: Optional[int] = None, runner=None) -> str:
    args = ["log", "--reverse", "--date=short", "--pretty=format:%h %ad %an %s"]
    if limit is not None:
        args.insert(2, f"--max-count={limit}")
    run_fn = runner if runner else run_git_command
    return run_fn(args, cwd)

def describe_status_code(code: str, area: str) -> Optional[str]:
    normalized = "" if code == " " else code
    if not normalized:
        return None

    labels = {
        "M": "staged modification" if area == "index" else "unstaged modification",
        "A": "staged new file" if area == "index" else "added in working tree",
        "D": "staged deletion" if area == "index" else "unstaged deletion",
        "R": "staged rename" if area == "index" else "unstaged rename",
        "C": "staged copy" if area == "index" else "unstaged copy",
        "U": "merge conflict",
        "?": "untracked"
    }
    return labels.get(normalized, f"{'index' if area == 'index' else 'working tree'} change ({normalized})")

def colorize_status_label(label: str) -> str:
    if label.startswith("staged "):
        return colorize(label, ANSI.green)
    if label.startswith("unstaged ") or "untracked" in label or "conflict" in label or "change (" in label:
        return colorize(label, ANSI.red)
    if label == "clean":
        return colorize(label, ANSI.green)
    return label

def format_status_entry(line: str) -> Optional[str]:
    if not line:
        return None

    if line.startswith("?? "):
        return f"- {line[3:]}: {colorize_status_label('untracked')}"

    if line.startswith("## "):
        return line[3:]

    if len(line) < 3:
        return None

    index_code = line[0]
    worktree_code = line[1]
    path_str = line[3:].strip()
    statuses = [
        describe_status_code(index_code, "index"),
        describe_status_code(worktree_code, "worktree")
    ]
    statuses = [s for s in statuses if s]

    if not statuses:
        return f"- {path_str}: {colorize_status_label('clean')}"

    status_str = ", ".join(colorize_status_label(s) for s in statuses)
    return f"- {path_str}: {status_str}"

def get_repository_status(cwd: str, runner=None) -> str:
    run_fn = runner if runner else run_git_command
    raw = run_fn(["status", "--short", "--branch"], cwd)

    if not raw:
        return "Working tree is clean."

    lines = [line for line in raw.splitlines() if line]
    branch_line = next((line for line in lines if line.startswith("## ")), None)
    entries = []
    for line in lines:
        if line.startswith("## "):
            continue
        entry = format_status_entry(line)
        if entry:
            entries.append(entry)

    if not entries:
        return f"{branch_line[3:]}\n\nWorking tree is clean." if branch_line else "Working tree is clean."

    parts = []
    if branch_line:
        parts.append(branch_line[3:])
    parts.append("")
    parts.append("Changes:")
    parts.extend(entries)
    return "\n".join(parts)

def get_commit_parents(ref: str, cwd: str) -> List[str]:
    output = run_git_command(["show", "-s", "--format=%P", ref], cwd)
    return [p.strip() for p in output.split(" ") if p.strip()]

def get_commit_metadata(ref: str, cwd: str) -> Dict[str, str]:
    output = run_git_command(
        ["show", "-s", "--format=%an%x1f%ae%x1f%aI%x1f%cn%x1f%ce%x1f%cI%x1f%B", ref],
        cwd
    )
    parts = output.split("\u001f")
    author_name = parts[0] if len(parts) > 0 else ""
    author_email = parts[1] if len(parts) > 1 else ""
    author_date = parts[2] if len(parts) > 2 else ""
    committer_name = parts[3] if len(parts) > 3 else ""
    committer_email = parts[4] if len(parts) > 4 else ""
    committer_date = parts[5] if len(parts) > 5 else ""
    message = "\u001f".join(parts[6:]) if len(parts) > 6 else ""

    return {
        "authorName": author_name,
        "authorEmail": author_email,
        "authorDate": author_date,
        "committerName": committer_name,
        "committerEmail": committer_email,
        "committerDate": committer_date,
        "message": message
    }

def list_commits_after(base_ref: str, head_ref: str, cwd: str) -> List[str]:
    output = run_git_command(["rev-list", "--reverse", f"{base_ref}..{head_ref}"], cwd)
    return [line.strip() for line in output.splitlines() if line.strip()]

def list_commits_after_topo(base_ref: str, head_ref: str, cwd: str) -> List[str]:
    output = run_git_command(["rev-list", "--reverse", "--topo-order", f"{base_ref}..{head_ref}"], cwd)
    return [line.strip() for line in output.splitlines() if line.strip()]

def list_branch_commits(ref: str, cwd: str) -> List[str]:
    output = run_git_command(["rev-list", "--reverse", ref], cwd)
    return [line.strip() for line in output.splitlines() if line.strip()]

def list_files_in_ref(ref: str, cwd: str) -> List[str]:
    output = run_git_command(["ls-tree", "-r", "--name-only", ref], cwd)
    return [line.strip() for line in output.splitlines() if line.strip()]

def is_ancestor_commit(ancestor_ref: str, descendant_ref: str, cwd: str) -> bool:
    result = run_git_command_unchecked(["merge-base", "--is-ancestor", ancestor_ref, descendant_ref], cwd)
    if result["exitCode"] == 0:
        return True
    if result["exitCode"] == 1:
        return False
    raise RuntimeError(result["stderr"] or "Unable to determine commit ancestry.")

def git_reset_hard(ref: str, cwd: str, runner=None) -> str:
    run_fn = runner if runner else run_git_command
    return run_fn(["reset", "--hard", ref], cwd)

def git_cherry_pick_no_commit(ref: str, cwd: str) -> str:
    return run_git_command(["cherry-pick", "--no-commit", ref], cwd)

def git_cherry_pick(ref: str, cwd: str) -> str:
    return run_git_command(["cherry-pick", ref], cwd)

def git_cherry_pick_record_source(ref: str, cwd: str) -> str:
    return run_git_command(["cherry-pick", "-x", ref], cwd)

def git_merge(ref: str, cwd: str, message: Optional[str] = None) -> str:
    args = ["merge", "--no-ff", ref]
    if message is not None:
        args.extend(["-m", message])
    return run_git_command(args, cwd)

def git_cherry_pick_abort(cwd: str) -> bool:
    result = run_git_command_unchecked(["cherry-pick", "--abort"], cwd)
    return result["exitCode"] == 0

def git_merge_abort(cwd: str) -> bool:
    result = run_git_command_unchecked(["merge", "--abort"], cwd)
    return result["exitCode"] == 0

def local_branch_exists(branch_name: str, cwd: str) -> bool:
    result = run_git_command_unchecked(["show-ref", "--verify", "--quiet", f"refs/heads/{branch_name}"], cwd)
    return result["exitCode"] == 0

def git_checkout(ref: str, cwd: str) -> str:
    return run_git_command(["checkout", ref], cwd)

def git_checkout_detached(ref: str, cwd: str) -> str:
    return run_git_command(["checkout", "--detach", ref], cwd)

def git_create_branch(branch_name: str, start_point: str, cwd: str) -> str:
    return run_git_command(["branch", branch_name, start_point], cwd)

def git_checkout_new_branch(branch_name: str, start_point: str, cwd: str) -> str:
    return run_git_command(["checkout", "-b", branch_name, start_point], cwd)

def git_checkout_orphan(branch_name: str, cwd: str) -> str:
    return run_git_command(["checkout", "--orphan", branch_name], cwd)

def git_delete_branch(branch_name: str, cwd: str) -> str:
    return run_git_command(["branch", "-D", branch_name], cwd)

def git_force_branch(branch_name: str, ref: str, cwd: str) -> str:
    return run_git_command(["branch", "-f", branch_name, ref], cwd)

def git_rebase_rebase_merges_onto(new_base: str, upstream: str, cwd: str, strategy_option: Optional[str] = None) -> str:
    args = ["rebase", "--rebase-merges"]
    if strategy_option:
        args.extend(["-X", strategy_option])
    args.extend(["--onto", new_base, upstream])
    return run_git_command(args, cwd)

def git_rebase_abort(cwd: str) -> bool:
    result = run_git_command_unchecked(["rebase", "--abort"], cwd)
    return result["exitCode"] == 0

def git_remove_cached_all(cwd: str) -> str:
    return run_git_command(["rm", "-r", "--cached", "--ignore-unmatch", "."], cwd)

def create_empty_root_commit(message: str, cwd: str) -> str:
    empty_tree = run_git_command_with_input(["mktree"], cwd, "")
    return run_git_command(["commit-tree", empty_tree, "-m", message], cwd)

def create_commit_from_tree(tree_sha: str, parent_shas: List[str], metadata: Dict[str, str], cwd: str) -> str:
    args = ["commit-tree", tree_sha]
    for parent_sha in parent_shas:
        args.extend(["-p", parent_sha])

    with tempfile.TemporaryDirectory(prefix="gitxplain-commit-tree-") as temp_dir:
        message_path = Path(temp_dir) / "message.txt"
        msg = metadata["message"]
        if not msg.endswith("\n"):
            msg += "\n"
        with open(message_path, "w", encoding="utf-8") as f:
            f.write(msg)
        args.extend(["-F", str(message_path)])

        env = {
            "GIT_AUTHOR_NAME": metadata["authorName"],
            "GIT_AUTHOR_EMAIL": metadata["authorEmail"],
            "GIT_AUTHOR_DATE": metadata["authorDate"],
            "GIT_COMMITTER_NAME": metadata["committerName"],
            "GIT_COMMITTER_EMAIL": metadata["committerEmail"],
            "GIT_COMMITTER_DATE": metadata["committerDate"]
        }
        
        try:
            full_env = {**os.environ, **env}
            result = subprocess.run(
                ["git"] + args,
                cwd=cwd,
                capture_output=True,
                text=True,
                env=full_env,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as error:
            stderr = error.stderr.strip() if error.stderr else ""
            raise RuntimeError(stderr or f"Git command failed: git {' '.join(args)}")

def write_current_index_tree(cwd: str) -> str:
    return run_git_command(["write-tree"], cwd)

def git_stash_push(message: str, cwd: str) -> str:
    return run_git_command(["stash", "push", "--include-untracked", "--message", message], cwd)

def git_stash_apply(stash_ref: str, cwd: str) -> str:
    return run_git_command(["stash", "apply", "--index", stash_ref], cwd)

def git_stash_drop(stash_ref: str, cwd: str) -> str:
    return run_git_command(["stash", "drop", stash_ref], cwd)

def resolve_stash_ref(index: Any = None) -> str:
    if index is None:
        return "stash@{0}"

    if isinstance(index, str) and re.match(r'^stash@\{\d+\}$', index.strip()):
        return index.strip()

    try:
        parsed = int(str(index))
        if parsed >= 0:
            return f"stash@{{{parsed}}}"
    except ValueError:
        pass
    raise RuntimeError(f"Invalid stash index: {index}")

def git_stash_pop(index: Any, cwd: str) -> str:
    stash_ref = resolve_stash_ref(index)
    return run_git_command(["stash", "pop", "--index", stash_ref], cwd)

def get_latest_stash_ref(cwd: str) -> Optional[str]:
    output = run_git_command(["stash", "list", "--format=%gd"], cwd)
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    return lines[0] if lines else None

def get_unchecked_command_output(args: List[str], cwd: str) -> str:
    result = run_git_command_unchecked(args, cwd)
    return result["stdout"]

def parse_unique_files(*groups: str) -> List[str]:
    unique_files = []
    seen = set()
    for group in groups:
        for line in group.splitlines():
            trimmed = line.strip()
            if trimmed and trimmed not in seen:
                seen.add(trimmed)
                unique_files.append(trimmed)
    return unique_files

def build_file_scoped_display_ref(target_ref: str, file_path: str) -> str:
    return f"{target_ref} :: {file_path}"

def extract_conflict_blocks(file_content: str) -> List[Dict[str, Any]]:
    lines = file_content.splitlines()
    blocks = []
    index = 0

    while index < len(lines):
        if not lines[index].startswith("<<<<<<<"):
            index += 1
            continue

        start_line = index + 1
        current_label = lines[index][len("<<<<<<<"):].strip() or "current"
        index += 1

        current_lines = []
        while index < len(lines) and not lines[index].startswith("======="):
            current_lines.append(lines[index])
            index += 1

        if index >= len(lines):
            break

        index += 1
        incoming_lines = []
        while index < len(lines) and not lines[index].startswith(">>>>>>>"):
            incoming_lines.append(lines[index])
            index += 1

        if index >= len(lines):
            break

        incoming_label = lines[index][len(">>>>>>>"):].strip() or "incoming"
        end_line = index + 1
        index += 1

        blocks.append({
            "startLine": start_line,
            "endLine": end_line,
            "currentLabel": current_label,
            "incomingLabel": incoming_label,
            "currentText": "\n".join(current_lines),
            "incomingText": "\n".join(incoming_lines)
        })

    return blocks

def build_conflict_analysis_diff(conflicts: List[Dict[str, Any]]) -> str:
    file_diffs = []
    for file_conflict in conflicts:
        block_texts = []
        for idx, block in enumerate(file_conflict["blocks"]):
            block_texts.append(
                f"Conflict {idx + 1} ({file_conflict['filePath']}:{block['startLine']}-{block['endLine']})\n"
                f"Current Side ({block['currentLabel']}):\n"
                f"{block['currentText'] or '<empty>'}\n"
                f"Incoming Side ({block['incomingLabel']}):\n"
                f"{block['incomingText'] or '<empty>'}"
            )
        file_diffs.append(f"File: {file_conflict['filePath']}\n" + "\n\n".join(block_texts))
    return "\n\n".join(file_diffs)

def format_iso_date_from_unix_timestamp(value: str) -> str:
    try:
        timestamp_ms = int(value) * 1000
    except ValueError:
        return "unknown-date"
    return datetime.utcfromtimestamp(timestamp_ms / 1000.0).strftime('%Y-%m-%d')

def parse_blame_porcelain(porcelain: str) -> List[Dict[str, Any]]:
    records = []
    lines = porcelain.splitlines()
    index = 0

    while index < len(lines):
        header = lines[index].strip()
        if not header:
            index += 1
            continue

        header_match = re.match(r'^(\^?[0-9a-f]{7,40})\s+\d+\s+(\d+)\s+(\d+)$', header, re.IGNORECASE)
        if not header_match:
            index += 1
            continue

        commit_sha, final_line_raw, line_count_raw = header_match.groups()
        record = {
            "commitSha": commit_sha,
            "finalLine": int(final_line_raw),
            "lineCount": int(line_count_raw),
            "author": "Unknown Author",
            "authorMail": "",
            "authorTime": "",
            "summary": "",
            "code": ""
        }

        index += 1
        while index < len(lines):
            line = lines[index]
            if line.startswith("\t"):
                record["code"] = line[1:]
                index += 1
                break

            if line.startswith("author "):
                record["author"] = line[len("author "):].strip()
            elif line.startswith("author-mail "):
                record["authorMail"] = line[len("author-mail "):].strip()
            elif line.startswith("author-time "):
                record["authorTime"] = line[len("author-time "):].strip()
            elif line.startswith("summary "):
                record["summary"] = line[len("summary "):].strip()

            index += 1

        records.append(record)

    return records

def build_blame_analysis_diff(file_path: str, records: List[Dict[str, Any]]) -> str:
    by_author = {}

    for record in records:
        key = f"{record['author']}|{record['authorMail']}"
        if key not in by_author:
            by_author[key] = {
                "author": record["author"],
                "authorMail": record["authorMail"],
                "lineCount": 0,
                "commitShas": set(),
                "summaries": set()
            }
        existing = by_author[key]
        existing["lineCount"] += 1
        existing["commitShas"].add(record["commitSha"])
        if record["summary"]:
            existing["summaries"].add(record["summary"])

    sorted_authors = sorted(by_author.values(), key=lambda x: x["lineCount"], reverse=True)
    author_section_lines = []
    for entry in sorted_authors:
        mail_str = f" {entry['authorMail']}" if entry['authorMail'] else ""
        notable = "; ".join(list(entry['summaries'])[:3]) or "n/a"
        author_section_lines.append(
            f"- {entry['author']}{mail_str}: {entry['lineCount']} line(s), {len(entry['commitShas'])} commit(s), notable commits: {notable}"
        )
    author_section = "\n".join(author_section_lines)

    line_section_lines = []
    for record in records:
        end_line = record["finalLine"] + record["lineCount"] - 1
        line_label = f"L{record['finalLine']}-L{end_line}" if record["lineCount"] > 1 else f"L{record['finalLine']}"
        short_sha = record["commitSha"].replace("^", "")[:8]
        author_date = format_iso_date_from_unix_timestamp(record["authorTime"])
        line_section_lines.append(
            f"{line_label} | {record['author']} | {author_date} | {short_sha} | {record['summary'] or 'no summary'} | {record['code']}"
        )
    line_section = "\n".join(line_section_lines)

    return "\n".join([
        f"Blame summary for {file_path}",
        "",
        "Authors:",
        author_section or "- none",
        "",
        "Line annotations:",
        line_section
    ])

def fetch_working_tree_data(cwd: str) -> Dict[str, Any]:
    staged_diff = get_unchecked_command_output(["diff", "--cached"], cwd)
    unstaged_diff = get_unchecked_command_output(["diff"], cwd)
    tracked_files = get_unchecked_command_output(["diff", "--name-only", "HEAD"], cwd)
    untracked_files = get_unchecked_command_output(["ls-files", "--others", "--exclude-standard"], cwd)
    tracked_stats = get_unchecked_command_output(["diff", "--stat", "HEAD"], cwd)

    untracked_list = [line.strip() for line in untracked_files.splitlines() if line.strip()]

    untracked_diff_parts = []
    for file in untracked_list:
        result = run_git_command_unchecked(["diff", "--no-index", "--", "/dev/null", file], cwd)
        if result["stdout"]:
            untracked_diff_parts.append(result["stdout"])
    untracked_diff = "\n".join(untracked_diff_parts)

    files_changed = parse_unique_files(tracked_files, untracked_files)
    diff = "\n".join([d for d in [staged_diff, unstaged_diff, untracked_diff] if d]).strip()
    tracked_stats_line = parse_stats_line(tracked_stats)
    untracked_stats_line = f"{len(untracked_list)} untracked file{'s' if len(untracked_list) != 1 else ''}" if untracked_list else None

    return {
        "analysisType": "workingTree",
        "targetRef": "working-tree",
        "displayRef": "working-tree",
        "commitId": None,
        "commitCount": 0,
        "commits": [],
        "commitMessage": "Uncommitted working tree changes",
        "diff": diff,
        "filesChanged": files_changed,
        "stats": "; ".join([s for s in [tracked_stats_line, untracked_stats_line] if s])
    }

def fetch_blame_data(file_path: str, cwd: str, runner=None) -> Dict[str, Any]:
    run_fn = runner if runner else run_git_command
    porcelain = run_fn(["blame", "--line-porcelain", "--", file_path], cwd)
    records = parse_blame_porcelain(porcelain)
    author_count = len(set(f"{r['author']}|{r['authorMail']}" for r in records))

    return {
        "analysisType": "blame",
        "targetRef": f"blame:{file_path}",
        "displayRef": file_path,
        "commitId": None,
        "commitCount": len(records),
        "commits": [],
        "commitMessage": f"Blame analysis for {file_path}",
        "diff": build_blame_analysis_diff(file_path, records),
        "filesChanged": [file_path],
        "stats": f"{len(records)} line annotation{'s' if len(records) != 1 else ''} across {author_count} author{'s' if author_count != 1 else ''}"
    }

def fetch_stash_data(stash_ref: Optional[str] = None, cwd: str = "", file_path: Optional[str] = None, runner=None) -> Dict[str, Any]:
    run_fn = runner if runner else run_git_command
    resolved_stash_ref = resolve_stash_ref(stash_ref)
    file_args = ["--", file_path] if file_path else []
    
    commit_message = run_fn(["log", "-1", "--pretty=format:%gs", resolved_stash_ref], cwd)
    diff = run_fn(["stash", "show", "-p", resolved_stash_ref] + file_args, cwd)
    files_changed_raw = run_fn(["stash", "show", "--name-only", resolved_stash_ref] + file_args, cwd)
    stats_raw = run_fn(["stash", "show", "--stat", resolved_stash_ref] + file_args, cwd)

    return {
        "analysisType": "stash",
        "targetRef": resolved_stash_ref,
        "displayRef": build_file_scoped_display_ref(resolved_stash_ref, file_path) if file_path else resolved_stash_ref,
        "commitId": resolved_stash_ref,
        "commitCount": 1,
        "commits": [{"hash": resolved_stash_ref, "subject": commit_message, "body": commit_message}],
        "commitMessage": commit_message or f"Stash entry {resolved_stash_ref}",
        "diff": diff,
        "filesChanged": parse_files_changed(files_changed_raw),
        "stats": parse_stats_line(stats_raw)
    }

def fetch_conflict_data(cwd: str, file_path: Optional[str] = None, runner=None) -> Dict[str, Any]:
    run_fn = runner if runner else run_git_command
    file_args = ["--", file_path] if file_path else []
    conflicted_files_raw = run_fn(["diff", "--name-only", "--diff-filter=U"] + file_args, cwd)
    conflicted_files = parse_files_changed(conflicted_files_raw)

    if not conflicted_files:
        raise RuntimeError(f"No unresolved merge conflicts found for {file_path}." if file_path else "No unresolved merge conflicts found in the working tree.")

    conflicts = []
    for relative_path in conflicted_files:
        absolute_path = Path(cwd) / relative_path
        with open(absolute_path, "r", encoding="utf-8") as f:
            content = f.read()
        blocks = extract_conflict_blocks(content)
        if blocks:
            conflicts.append({
                "filePath": relative_path,
                "blocks": blocks
            })

    if not conflicts:
        raise RuntimeError(f"Conflict markers were not found in {file_path}." if file_path else "Git reports unresolved conflicts, but no conflict markers were found in the conflicted files.")

    conflict_count = sum(len(entry["blocks"]) for entry in conflicts)

    return {
        "analysisType": "conflict",
        "targetRef": f"conflict:{file_path}" if file_path else "conflict",
        "displayRef": file_path if file_path else "working-tree conflicts",
        "commitId": None,
        "commitCount": conflict_count,
        "commits": [],
        "commitMessage": f"Merge conflict analysis for {file_path}" if file_path else "Merge conflict analysis for the working tree",
        "diff": build_conflict_analysis_diff(conflicts),
        "filesChanged": [entry["filePath"] for entry in conflicts],
        "stats": f"{conflict_count} conflict block{'s' if conflict_count != 1 else ''} across {len(conflicts)} file{'s' if len(conflicts) != 1 else ''}"
    }

def fetch_single_commit_data(commit_id: str, cwd: str, runner) -> Dict[str, Any]:
    commit_message = runner(["log", "-1", "--pretty=format:%B", commit_id], cwd)
    diff = runner(["diff", f"{commit_id}^!"], cwd)
    files_changed_raw = runner(["show", "--pretty=format:", "--name-only", commit_id], cwd)
    stats_raw = runner(["show", "--stat", "--oneline", "--format=%h %s", commit_id], cwd)
    subject = runner(["log", "-1", "--pretty=format:%s", commit_id], cwd)

    return {
        "analysisType": "commit",
        "targetRef": commit_id,
        "displayRef": commit_id,
        "commitId": commit_id,
        "commitCount": 1,
        "commits": [{"hash": commit_id, "subject": subject, "body": commit_message}],
        "commitMessage": commit_message,
        "diff": diff,
        "filesChanged": parse_files_changed(files_changed_raw),
        "stats": parse_stats_line(stats_raw)
    }

def fetch_single_commit_file_data(commit_id: str, file_path: str, cwd: str, runner) -> Dict[str, Any]:
    commit_message = runner(["log", "-1", "--pretty=format:%B", commit_id], cwd)
    diff = runner(["diff", f"{commit_id}^!", "--", file_path], cwd)
    files_changed_raw = runner(["show", "--pretty=format:", "--name-only", commit_id, "--", file_path], cwd)
    stats_raw = runner(["show", "--stat", "--oneline", "--format=%h %s", commit_id, "--", file_path], cwd)
    subject = runner(["log", "-1", "--pretty=format:%s", commit_id], cwd)

    return {
        "analysisType": "commit",
        "targetRef": commit_id,
        "displayRef": build_file_scoped_display_ref(commit_id, file_path),
        "commitId": commit_id,
        "commitCount": 1,
        "commits": [{"hash": commit_id, "subject": subject, "body": commit_message}],
        "commitMessage": commit_message,
        "diff": diff,
        "filesChanged": parse_files_changed(files_changed_raw),
        "stats": parse_stats_line(stats_raw)
    }

def fetch_range_data(range_ref: str, cwd: str, runner) -> Dict[str, Any]:
    diff = runner(["diff", range_ref], cwd)
    files_changed_raw = runner(["diff", "--name-only", range_ref], cwd)
    stats_raw = runner(["diff", "--stat", range_ref], cwd)
    commit_log_raw = runner(
        ["log", "--reverse", "--pretty=format:%H%x1f%s%x1f%B", range_ref],
        cwd
    )

    commits = parse_commit_log(commit_log_raw)
    if not commits:
        raise RuntimeError(f"No commits found in range {range_ref}")

    return {
        "analysisType": "range",
        "targetRef": range_ref,
        "displayRef": range_ref,
        "commitId": None,
        "commitCount": len(commits),
        "commits": commits,
        "commitMessage": build_commit_message(commits),
        "diff": diff,
        "filesChanged": parse_files_changed(files_changed_raw),
        "stats": parse_stats_line(stats_raw)
    }

def fetch_range_file_data(range_ref: str, file_path: str, cwd: str, runner) -> Dict[str, Any]:
    diff = runner(["diff", range_ref, "--", file_path], cwd)
    files_changed_raw = runner(["diff", "--name-only", range_ref, "--", file_path], cwd)
    stats_raw = runner(["diff", "--stat", range_ref, "--", file_path], cwd)
    commit_log_raw = runner(
        ["log", "--reverse", "--pretty=format:%H%x1f%s%x1f%B", range_ref, "--", file_path],
        cwd
    )

    commits = parse_commit_log(commit_log_raw)
    if not commits:
        raise RuntimeError(f"No commits found in range {range_ref} for file {file_path}")

    return {
        "analysisType": "range",
        "targetRef": range_ref,
        "displayRef": build_file_scoped_display_ref(range_ref, file_path),
        "commitId": None,
        "commitCount": len(commits),
        "commits": commits,
        "commitMessage": build_commit_message(commits),
        "diff": diff,
        "filesChanged": parse_files_changed(files_changed_raw),
        "stats": parse_stats_line(stats_raw)
    }

def fetch_commit_data(target_ref: str, cwd: str, runner=run_git_command) -> Dict[str, Any]:
    if is_range_ref(target_ref):
        return fetch_range_data(target_ref, cwd, runner)
    else:
        return fetch_single_commit_data(target_ref, cwd, runner)

def fetch_commit_data_for_file(target_ref: str, file_path: str, cwd: str, runner=run_git_command) -> Dict[str, Any]:
    if is_range_ref(target_ref):
        return fetch_range_file_data(target_ref, file_path, cwd, runner)
    else:
        return fetch_single_commit_file_data(target_ref, file_path, cwd, runner)
