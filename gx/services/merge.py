import re
from typing import Any, Dict, List, Optional, Set, Tuple
from .git import (
    create_commit_from_tree,
    get_commit_metadata,
    get_current_branch_name,
    get_default_base_ref,
    get_merge_base,
    git_checkout,
    git_create_branch,
    git_create_annotated_tag,
    git_delete_branch,
    git_force_branch,
    git_delete_tag,
    is_working_tree_clean,
    list_branch_commits,
    list_commits_after,
    list_tags,
    list_tag_targets,
    local_branch_exists,
    resolve_tree_sha,
    resolve_commit_sha,
    run_git_command
)
from .color import ANSI, colorize

RELEASE_BRANCH = "release"
VERSION_PATTERN = re.compile(r'\b\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?\b')
RELEASE_SUBJECT_PATTERN = re.compile(r'^release\s+(.+)$', re.IGNORECASE)
SEMVER_PATTERN = re.compile(r'^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$')
INTEGER_PATTERN = re.compile(r'^\d+$')
TAG_VERSION_PATTERN = re.compile(r'^v?(\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?|\d+)$')

def unique(values: List[Any]) -> List[Any]:
    seen = set()
    res = []
    for v in values:
        if v not in seen:
            seen.add(v)
            res.append(v)
    return res

def format_version_tag(version: str) -> str:
    return f"v{version}"

def extract_versions(line: str) -> List[str]:
    return unique(VERSION_PATTERN.findall(line))

def strip_diff_prefix(line: str) -> str:
    return line[1:].strip()

def parse_diff_path(line: str) -> Optional[str]:
    match = re.match(r'^diff --git a/(.+?) b/(.+)$', line)
    return match.group(2) if match else None

def is_exact_filename(file_path: Optional[str], filename: str) -> bool:
    if not file_path:
        return False
    return file_path == filename or file_path.endswith(f"/{filename}")

def extract_version_candidate(file_path: Optional[str], line: str) -> Optional[str]:
    trimmed = line.strip()
    if not file_path or trimmed == "":
        return None

    if is_exact_filename(file_path, "package.json"):
        m = re.match(r'^"version"\s*:\s*"([^"]+)"[,]?$', trimmed)
        return m.group(1) if m else None

    if is_exact_filename(file_path, "pubspec.yaml"):
        m = re.match(r'^version:\s*([^\s#]+)$', trimmed)
        return m.group(1) if m else None

    if is_exact_filename(file_path, "Cargo.toml"):
        m = re.match(r'^version\s*=\s*"([^"]+)"$', trimmed)
        return m.group(1) if m else None

    if is_exact_filename(file_path, "pom.xml"):
        m = re.match(r'^<version>([^<]+)</version>$', trimmed)
        return m.group(1) if m else None

    if file_path.endswith(".csproj"):
        m1 = re.match(r'^<Version>([^<]+)</Version>$', trimmed)
        m2 = re.match(r'^<ApplicationDisplayVersion>([^<]+)</ApplicationDisplayVersion>$', trimmed)
        m3 = re.match(r'^<ApplicationVersion>([^<]+)</ApplicationVersion>$', trimmed)
        return (m1.group(1) if m1 else (m2.group(1) if m2 else (m3.group(1) if m3 else None)))

    if is_exact_filename(file_path, "Info.plist"):
        m = re.match(r'^<string>([^<]+)</string>$', trimmed)
        return m.group(1) if m else None

    if file_path.endswith("AndroidManifest.xml"):
        m1 = re.search(r'versionName="([^"]+)"', trimmed)
        m2 = re.search(r'versionCode="([^"]+)"', trimmed)
        return (m1.group(1) if m1 else (m2.group(1) if m2 else None))

    if file_path.endswith("build.gradle") or file_path.endswith("build.gradle.kts"):
        m1 = re.match(r'^versionName\s*[= ]\s*["\']?([^"\'\s]+)["\']?$', trimmed)
        m2 = re.match(r'^versionCode\s*[= ]\s*["\']?([^"\'\s]+)["\']?$', trimmed)
        m3 = re.match(r'^version\s*=\s*["\']([^"\']+)["\']$', trimmed)
        return (m1.group(1) if m1 else (m2.group(1) if m2 else (m3.group(1) if m3 else None)))

    if is_exact_filename(file_path, "gradle.properties"):
        m1 = re.match(r'^(?:VERSION_NAME|versionName)\s*=\s*(\S+)$', trimmed)
        m2 = re.match(r'^(?:VERSION_CODE|versionCode)\s*=\s*(\S+)$', trimmed)
        return (m1.group(1) if m1 else (m2.group(1) if m2 else None))

    if (
        is_exact_filename(file_path, "VERSION") or
        is_exact_filename(file_path, ".version") or
        is_exact_filename(file_path, "version.txt")
    ):
        return trimmed if (SEMVER_PATTERN.match(trimmed) or INTEGER_PATTERN.match(trimmed)) else None

    return None

def rank_version_value(value: str) -> int:
    if SEMVER_PATTERN.match(value):
        return 2
    if INTEGER_PATTERN.match(value):
        return 1
    return 0

def select_release_version(values: List[str]) -> Optional[str]:
    sorted_vals = sorted(values, key=rank_version_value, reverse=True)
    return sorted_vals[0] if sorted_vals else None

def detect_version_changes(diff: str) -> Dict[str, Any]:
    removed_versions = []
    added_versions = []
    current_file = None

    for line in diff.splitlines():
        diff_path = parse_diff_path(line)
        if diff_path:
            current_file = diff_path
            continue

        if line.startswith("---") or line.startswith("+++"):
            continue

        if line.startswith("-"):
            candidate = extract_version_candidate(current_file, strip_diff_prefix(line))
            if candidate:
                removed_versions.append(candidate)
            continue

        if line.startswith("+"):
            candidate = extract_version_candidate(current_file, strip_diff_prefix(line))
            if candidate:
                added_versions.append(candidate)

    removed = unique(removed_versions)
    added = unique(added_versions)
    from_versions = [v for v in removed if v not in added]
    to_versions = [v for v in added if v not in removed]

    return {
        "from": from_versions,
        "to": to_versions,
        "hasVersionChange": len(from_versions) > 0 and len(to_versions) > 0,
        "releaseVersion": select_release_version(to_versions)
    }

def get_release_version(change: Dict[str, Any]) -> Optional[str]:
    return change.get("releaseVersion")

def get_commit_subject(ref: str, cwd: str) -> str:
    return run_git_command(["log", "-1", "--pretty=format:%s", ref], cwd)

def get_commit_files(ref: str, cwd: str) -> List[str]:
    output = run_git_command(["show", "--pretty=format:", "--name-only", ref], cwd)
    return [line.strip() for line in output.splitlines() if line.strip()]

def get_commit_diff(ref: str, cwd: str) -> str:
    return run_git_command(["show", "--format=", ref], cwd)

def inspect_commit(sha: str, cwd: str) -> Dict[str, Any]:
    subject = get_commit_subject(sha, cwd)
    diff = get_commit_diff(sha, cwd)
    version_change = detect_version_changes(diff)

    return {
        "sha": sha,
        "shortSha": sha[:7],
        "subject": subject,
        "files": get_commit_files(sha, cwd),
        "versionChange": version_change,
        "releaseVersion": get_release_version(version_change)
    }

def summarize_version_pair(change: Dict[str, Any]) -> str:
    return f"{', '.join(change.get('from', []))} -> {', '.join(change.get('to', []))}"

def get_released_versions(release_commits: List[Dict[str, Any]]) -> Set[str]:
    explicit_versions = []
    for commit in release_commits:
        match = RELEASE_SUBJECT_PATTERN.match(commit["subject"])
        if match:
            explicit_versions.append(match.group(1).strip())

    fallback_versions = [commit["releaseVersion"] for commit in release_commits if commit.get("releaseVersion")]
    return set(explicit_versions + fallback_versions)

def extract_tagged_versions(tag_names: List[str]) -> Set[str]:
    versions = []
    for tag in tag_names:
        match = TAG_VERSION_PATTERN.match(tag)
        if match:
            versions.append(match.group(1))
    return set(versions)

def build_release_windows(source_commits: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    windows = []
    window_start_index = 0
    active_version = None

    for index, commit in enumerate(source_commits):
        if not commit.get("releaseVersion"):
            continue

        if active_version is None:
            active_version = commit["releaseVersion"]
            continue

        if commit["releaseVersion"] == active_version:
            continue

        previous_index = index - 1
        windows.append({
            "version": active_version,
            "commits": source_commits[window_start_index:previous_index + 1],
            "startRef": source_commits[window_start_index]["shortSha"] if window_start_index < len(source_commits) else None,
            "endRef": source_commits[previous_index]["shortSha"] if previous_index >= 0 else None
        })
        window_start_index = index
        active_version = commit["releaseVersion"]

    if active_version is not None:
        windows.append({
            "version": active_version,
            "commits": source_commits[window_start_index:],
            "startRef": source_commits[window_start_index]["shortSha"] if window_start_index < len(source_commits) else None,
            "endRef": source_commits[-1]["shortSha"] if source_commits else None
        })

    return windows

def select_latest_windows_per_version(windows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen_versions = set()
    latest_windows = []

    for window in reversed(windows):
        version = window.get("version")
        if not version or version in seen_versions:
            continue
        seen_versions.add(version)
        latest_windows.append(window)

    latest_windows.reverse()
    return latest_windows

def select_release_windows(source_commits: List[Dict[str, Any]], release_commits: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    if release_commits is None:
        release_commits = []

    windows = build_release_windows(source_commits)
    released_versions = get_released_versions(release_commits)
    unreleased_windows = [w for w in windows if w.get("version") not in released_versions]

    latest_detected = windows[-1].get("version") if windows else None
    return {
        "windows": unreleased_windows,
        "releasedVersions": list(released_versions),
        "latestDetectedVersion": latest_detected
    }

def select_release_tags(source_commits: List[Dict[str, Any]], existing_tag_names: List[str] = None, existing_tag_targets: List[Dict[str, str]] = None) -> Dict[str, Any]:
    if existing_tag_names is None:
        existing_tag_names = []
    if existing_tag_targets is None:
        existing_tag_targets = []

    windows = select_latest_windows_per_version(build_release_windows(source_commits))
    tagged_versions = extract_tagged_versions(existing_tag_names)
    
    existing_tag_by_version = {}
    for tag in existing_tag_targets:
        match = TAG_VERSION_PATTERN.match(tag.get("tagName", ""))
        version = match.group(1) if match else None
        if version:
            existing_tag_by_version[version] = tag

    tags = []
    for window in windows:
        target_commit = window["commits"][-1] if window["commits"] else None
        existing_tag = existing_tag_by_version.get(window["version"])
        existing_target_sha = existing_tag.get("targetSha") if existing_tag else None
        window_commit_shas = {commit["sha"] for commit in window["commits"]}

        needs_move = (
            existing_target_sha is not None and
            target_commit is not None and
            existing_target_sha in window_commit_shas and
            existing_target_sha != target_commit["sha"]
        )

        tag_info = {
            **window,
            "version": window["version"],
            "tagName": existing_tag.get("tagName") if existing_tag else format_version_tag(window["version"]),
            "existingTagName": existing_tag.get("tagName") if existing_tag else None,
            "existingTargetSha": existing_target_sha,
            "needsMove": needs_move,
            "targetSha": target_commit["sha"] if target_commit else None,
            "targetShortSha": target_commit["shortSha"] if target_commit else None,
            "targetSubject": target_commit["subject"] if target_commit else None
        }
        tags.append(tag_info)

    filtered_tags = []
    for tag in tags:
        if (tag["version"] not in tagged_versions or tag["needsMove"]) and tag["targetSha"] is not None:
            filtered_tags.append(tag)

    latest_detected = windows[-1].get("version") if windows else None
    return {
        "tags": filtered_tags,
        "taggedVersions": list(tagged_versions),
        "latestDetectedVersion": latest_detected
    }

def find_latest_tagged_source_version(source_commits: List[Dict[str, Any]], tagged_versions: List[str]) -> Optional[str]:
    tagged = set(tagged_versions)
    versions = [w.get("version") for w in select_latest_windows_per_version(build_release_windows(source_commits))]
    matching = [v for v in versions if v and v in tagged]
    return matching[-1] if matching else None

def build_release_tag_plan_for_source(source_branch: str, source_ref: str, cwd: str) -> Dict[str, Any]:
    source_commits = [inspect_commit(sha, cwd) for sha in list_branch_commits(source_ref, cwd)]
    existing_tag_names = list_tags(cwd)
    existing_tag_targets = list_tag_targets(cwd)
    selection = select_release_tags(source_commits, existing_tag_names, existing_tag_targets)

    return {
        "sourceBranch": source_branch,
        "baseRef": source_ref,
        "mergeBase": None,
        "releaseExists": local_branch_exists(RELEASE_BRANCH, cwd),
        "taggedVersions": selection["taggedVersions"],
        "latestDetectedVersion": selection["latestDetectedVersion"],
        "latestTaggedVersion": find_latest_tagged_source_version(source_commits, selection["taggedVersions"]),
        "tags": selection["tags"]
    }

def select_release_tags_from_release_commits(release_commits: List[Dict[str, Any]], existing_tag_names: List[str] = None) -> Dict[str, Any]:
    if existing_tag_names is None:
        existing_tag_names = []

    tagged_versions = extract_tagged_versions(existing_tag_names)
    tags = []
    
    for commit in release_commits:
        match = RELEASE_SUBJECT_PATTERN.match(commit["subject"])
        version = match.group(1).strip() if match else None
        if version and version not in tagged_versions:
            tags.append({
                "version": version,
                "tagName": format_version_tag(version),
                "startRef": commit["shortSha"],
                "endRef": commit["shortSha"],
                "targetSha": commit["sha"],
                "targetShortSha": commit["shortSha"],
                "targetSubject": commit["subject"],
                "commits": [commit]
            })

    detected_versions = []
    for commit in release_commits:
        match = RELEASE_SUBJECT_PATTERN.match(commit["subject"])
        if match:
            detected_versions.append(match.group(1).strip())

    latest_detected = detected_versions[-1] if detected_versions else None
    return {
        "tags": tags,
        "taggedVersions": list(tagged_versions),
        "latestDetectedVersion": latest_detected
    }

def get_release_track_source_commit_shas(release_exists: bool, base_ref: str, source_ref: str, cwd: str) -> Dict[str, Any]:
    if not release_exists:
        return {
            "mergeBase": None,
            "sourceCommitShas": list_branch_commits(source_ref, cwd)
        }

    try:
        merge_base = get_merge_base(base_ref, source_ref, cwd)
        return {
            "mergeBase": merge_base,
            "sourceCommitShas": list_commits_after(merge_base, source_ref, cwd)
        }
    except Exception:
        return {
            "mergeBase": None,
            "sourceCommitShas": list_branch_commits(source_ref, cwd)
        }

def build_release_merge_plan_for_source(source_branch: str, source_ref: str, cwd: str) -> Dict[str, Any]:
    release_exists = local_branch_exists(RELEASE_BRANCH, cwd)
    base_ref = RELEASE_BRANCH if release_exists else get_default_base_ref(cwd)
    track_info = get_release_track_source_commit_shas(release_exists, base_ref, source_ref, cwd)
    merge_base = track_info["mergeBase"]
    source_commit_shas = track_info["sourceCommitShas"]

    source_commits = [inspect_commit(sha, cwd) for sha in source_commit_shas]
    release_commits = [inspect_commit(sha, cwd) for sha in list_branch_commits(RELEASE_BRANCH, cwd)] if release_exists else []
    selection = select_release_windows(source_commits, release_commits)

    return {
        "releaseBranch": RELEASE_BRANCH,
        "sourceBranch": source_branch,
        "baseRef": base_ref,
        "mergeBase": merge_base,
        "releaseExists": release_exists,
        "releasedVersions": selection["releasedVersions"],
        "latestDetectedVersion": selection["latestDetectedVersion"],
        "windows": selection["windows"],
        "createFromRef": RELEASE_BRANCH if release_exists else None
    }

def build_release_merge_plan(cwd: str) -> Dict[str, Any]:
    source_branch = get_current_branch_name(cwd)
    if source_branch == RELEASE_BRANCH:
        raise RuntimeError(f'Already on "{RELEASE_BRANCH}". Switch to a source branch before running --merge.')

    return build_release_merge_plan_for_source(source_branch, "HEAD", cwd)

def build_release_tag_plan(cwd: str) -> Dict[str, Any]:
    source_branch = get_current_branch_name(cwd)
    if source_branch == RELEASE_BRANCH:
        raise RuntimeError(f'Already on "{RELEASE_BRANCH}". Switch to a source branch before running --tag.')

    return build_release_tag_plan_for_source(source_branch, "HEAD", cwd)

def finalize_release_merge_plan(plan: Dict[str, Any]) -> Dict[str, Any]:
    return {
        **plan,
        "totalCommits": sum(len(w.get("commits", [])) for w in plan.get("windows", []))
    }

def finalize_release_tag_plan(plan: Dict[str, Any]) -> Dict[str, Any]:
    return {
        **plan,
        "totalCommits": sum(len(t.get("commits", [])) for t in plan.get("tags", []))
    }

def find_latest_release_version(release_commits: List[Dict[str, Any]]) -> Optional[str]:
    versions = []
    for commit in release_commits:
        match = RELEASE_SUBJECT_PATTERN.match(commit["subject"])
        if match:
            versions.append(match.group(1).strip())
    return versions[-1] if versions else None

def build_drift_status(source_ref: str, source_label: str, release_exists: bool, cwd: str) -> Dict[str, Any]:
    if not release_exists:
        return {
            "hasReleaseBranch": False,
            "disconnectedHistory": False,
            "sourceOnlyCount": len(list_branch_commits(source_ref, cwd)),
            "releaseOnlyCount": 0,
            "summary": f'Release branch "{RELEASE_BRANCH}" does not exist yet.'
        }

    try:
        merge_base = get_merge_base(source_ref, RELEASE_BRANCH, cwd)
        source_only = len(list_commits_after(merge_base, source_ref, cwd))
        release_only = len(list_commits_after(merge_base, RELEASE_BRANCH, cwd))

        if source_only == 0 and release_only == 0:
            summary = f"{source_label} and {RELEASE_BRANCH} point at the same history."
        else:
            summary = f"{source_label} has {source_only} unique commit(s); {RELEASE_BRANCH} has {release_only} unique commit(s)."

        return {
            "hasReleaseBranch": True,
            "disconnectedHistory": False,
            "mergeBase": merge_base,
            "sourceOnlyCount": source_only,
            "releaseOnlyCount": release_only,
            "summary": summary
        }
    except Exception:
        return {
            "hasReleaseBranch": True,
            "disconnectedHistory": True,
            "mergeBase": None,
            "sourceOnlyCount": len(list_branch_commits(source_ref, cwd)),
            "releaseOnlyCount": len(list_branch_commits(RELEASE_BRANCH, cwd)),
            "summary": f"{source_label} and {RELEASE_BRANCH} do not share a merge base. This is expected when the release branch is orphaned."
        }

def get_next_recommended_action(params: Dict[str, Any]) -> str:
    release_exists = params.get("releaseExists")
    merge_plan = params.get("mergePlan", {})
    missing_tag_count = params.get("missingTagCount", 0)

    window_count = len(merge_plan.get("windows", []))

    if not release_exists and window_count > 0:
        return f"Run `gx --merge --execute` to create {RELEASE_BRANCH} and promote {window_count} unreleased version(s)."

    if not release_exists and missing_tag_count > 0:
        return f"Run `gx --tag --execute` to create {missing_tag_count} missing version tag(s) on the current branch."

    if not release_exists:
        return f"No {RELEASE_BRANCH} branch exists yet, and no releasable version bumps were detected."

    if window_count > 0 and missing_tag_count > 0:
        return f"Run `gx --merge --execute` to update {RELEASE_BRANCH}, and `gx --tag --execute` to create {missing_tag_count} missing version tag(s)."

    if window_count > 0:
        return f"Run `gx --merge --execute` to promote {window_count} unreleased version(s) to {RELEASE_BRANCH}."

    if missing_tag_count > 0:
        return f"Run `gx --tag --execute` to create {missing_tag_count} missing version tag(s)."

    return "No action required. Release branch and tags are up to date."

def build_release_status(cwd: str) -> Dict[str, Any]:
    current_branch = get_current_branch_name(cwd)
    release_exists = local_branch_exists(RELEASE_BRANCH, cwd)
    source_branch = get_default_base_ref(cwd) if current_branch == RELEASE_BRANCH else current_branch
    source_ref = source_branch if current_branch == RELEASE_BRANCH else "HEAD"
    
    merge_plan = finalize_release_merge_plan(build_release_merge_plan_for_source(source_branch, source_ref, cwd))
    release_commits = [inspect_commit(sha, cwd) for sha in list_branch_commits(RELEASE_BRANCH, cwd)] if release_exists else []
    tag_plan = finalize_release_tag_plan(build_release_tag_plan_for_source(source_branch, source_ref, cwd))
    drift = build_drift_status(source_ref, source_branch, release_exists, cwd)
    missing_tag_versions = [tag["tagName"] for tag in tag_plan.get("tags", [])]
    unmerged_versions = [w["version"] for w in merge_plan.get("windows", [])]

    return {
        "sourceBranch": source_branch,
        "sourceRef": source_ref,
        "releaseBranch": RELEASE_BRANCH,
        "releaseExists": release_exists,
        "currentBranch": current_branch,
        "health": "needs attention" if (not release_exists or len(unmerged_versions) > 0 or len(missing_tag_versions) > 0) else "healthy",
        "latestSourceVersion": merge_plan.get("latestDetectedVersion"),
        "latestReleaseVersion": find_latest_release_version(release_commits),
        "latestTaggedVersion": tag_plan.get("latestTaggedVersion"),
        "unmergedVersions": unmerged_versions,
        "missingTagVersions": missing_tag_versions,
        "drift": drift,
        "mergePlan": merge_plan,
        "tagPlan": tag_plan,
        "nextRecommendedAction": get_next_recommended_action({
            "releaseExists": release_exists,
            "mergePlan": merge_plan,
            "missingTagCount": len(missing_tag_versions)
        })
    }

def format_release_merge_plan(plan: Dict[str, Any]) -> str:
    lines = [
        colorize("Release Merge Plan", ANSI.bold + ANSI.cyan),
        f"{colorize('Source Branch:', ANSI.bold + ANSI.cyan)} {plan.get('sourceBranch')}",
        f"{colorize('Target Branch:', ANSI.bold + ANSI.cyan)} {plan.get('releaseBranch')}",
        f"{colorize('Base Ref:', ANSI.bold + ANSI.cyan)} {plan.get('baseRef')}",
        f"{colorize('Released Versions:', ANSI.bold + ANSI.cyan)} {', '.join(plan.get('releasedVersions', [])) if plan.get('releasedVersions') else 'none'}",
        f"{colorize('Latest Detected Version:', ANSI.bold + ANSI.cyan)} {plan.get('latestDetectedVersion') or 'none'}"
    ]

    windows = plan.get("windows", [])
    if not windows:
        lines.append(colorize("No unreleased release commits detected. Nothing to merge.", ANSI.green))
        return "\n".join(lines)

    for window in windows:
        lines.append("")
        lines.append(colorize(f"release {window['version']}", ANSI.bold + ANSI.yellow))
        lines.append(f"{colorize('Commit Range:', ANSI.bold + ANSI.cyan)} {window.get('startRef')}..{window.get('endRef')}")

        for commit in window.get("commits", []):
            lines.append(f"{colorize(commit['shortSha'], ANSI.bold + ANSI.cyan)} {commit['subject']}")
            if commit.get("versionChange", {}).get("hasVersionChange"):
                lines.append(f"  {colorize('Version:', ANSI.bold + ANSI.cyan)} {summarize_version_pair(commit['versionChange'])}")

    return "\n".join(lines)

def format_release_tag_plan(plan: Dict[str, Any]) -> str:
    lines = [
        colorize("Release Tag Plan", ANSI.bold + ANSI.cyan),
        f"{colorize('Source Branch:', ANSI.bold + ANSI.cyan)} {plan.get('sourceBranch')}",
        f"{colorize('Base Ref:', ANSI.bold + ANSI.cyan)} {plan.get('baseRef')}",
        f"{colorize('Tagged Versions:', ANSI.bold + ANSI.cyan)} {', '.join(plan.get('taggedVersions', [])) if plan.get('taggedVersions') else 'none'}",
        f"{colorize('Latest Detected Version:', ANSI.bold + ANSI.cyan)} {plan.get('latestDetectedVersion') or 'none'}"
    ]

    tags = plan.get("tags", [])
    if not tags:
        lines.append(colorize("No release tag changes detected. Nothing to tag.", ANSI.green))
        return "\n".join(lines)

    for tag in tags:
        lines.append("")
        action_label = "move tag" if tag.get("needsMove") else "tag"
        lines.append(colorize(f"{action_label} {tag['tagName']}", ANSI.bold + ANSI.yellow))
        lines.append(f"{colorize('Commit Range:', ANSI.bold + ANSI.cyan)} {tag.get('startRef')}..{tag.get('endRef')}")
        lines.append(f"{colorize('Target Commit:', ANSI.bold + ANSI.cyan)} {tag.get('targetShortSha')} {tag.get('targetSubject')}")
        if tag.get("needsMove"):
            lines.append(f"{colorize('Action:', ANSI.bold + ANSI.cyan)} move existing tag to the latest commit for {tag['tagName']}")

        for commit in tag.get("commits", []):
            lines.append(f"{colorize(commit['shortSha'], ANSI.bold + ANSI.cyan)} {commit['subject']}")
            if commit.get("versionChange", {}).get("hasVersionChange"):
                lines.append(f"  {colorize('Version:', ANSI.bold + ANSI.cyan)} {summarize_version_pair(commit['versionChange'])}")

    return "\n".join(lines)

def format_release_status(status: Dict[str, Any]) -> str:
    lines = [
        colorize("Release Status", ANSI.bold + ANSI.cyan),
        f"{colorize('Source Branch:', ANSI.bold + ANSI.cyan)} {status.get('sourceBranch')}",
        f"{colorize('Release Branch:', ANSI.bold + ANSI.cyan)} {status.get('releaseBranch')}",
        f"{colorize('Current Branch:', ANSI.bold + ANSI.cyan)} {status.get('currentBranch')}",
        f"{colorize('Overall:', ANSI.bold + ANSI.cyan)} {status.get('health')}",
        f"{colorize('Latest Source Version:', ANSI.bold + ANSI.cyan)} {status.get('latestSourceVersion') or 'none'}",
        f"{colorize('Latest Release Version:', ANSI.bold + ANSI.cyan)} {status.get('latestReleaseVersion') or 'none'}",
        f"{colorize('Latest Tagged Version:', ANSI.bold + ANSI.cyan)} {status.get('latestTaggedVersion') or 'none'}"
    ]

    lines.append("")
    lines.append(colorize("Unmerged Version Bumps", ANSI.bold + ANSI.yellow))
    windows = status.get("mergePlan", {}).get("windows", [])
    if not windows:
        lines.append("none")
    else:
        for window in windows:
            lines.append(f"- {window['version']} ({window.get('startRef')}..{window.get('endRef')})")

    lines.append("")
    lines.append(colorize("Missing Release Tags", ANSI.bold + ANSI.yellow))
    tags = status.get("tagPlan", {}).get("tags", [])
    if not tags:
        lines.append("none")
    else:
        for tag in tags:
            lines.append(f"- {tag['tagName']} -> {tag.get('targetShortSha')} {tag.get('targetSubject')}")

    lines.append("")
    lines.append(colorize("Branch Drift", ANSI.bold + ANSI.yellow))
    drift = status.get("drift", {})
    lines.append(drift.get("summary", ""))
    lines.append(f"- Commits only on {status.get('sourceBranch')}: {drift.get('sourceOnlyCount', 0)}")
    lines.append(f"- Commits only on {status.get('releaseBranch')}: {drift.get('releaseOnlyCount', 0)}")

    lines.append("")
    lines.append(f"{colorize('Next Recommended Action:', ANSI.bold + ANSI.cyan)} {status.get('nextRecommendedAction')}")

    return "\n".join(lines)

def build_recovery_message(original_branch: str, original_release_sha: Optional[str], created_release_branch: bool) -> str:
    lines = ["Release promotion failed. Recovery steps:"]
    if created_release_branch:
        lines.append(f"- Return to {original_branch} with `git checkout {original_branch}`")
        lines.append(f"- Delete the temporary {RELEASE_BRANCH} branch with `git branch -D {RELEASE_BRANCH}`")
    else:
        lines.append(f"- Reset {RELEASE_BRANCH} back to {original_release_sha} with `git reset --hard {original_release_sha}`")
        lines.append(f"- Return to {original_branch} with `git checkout {original_branch}`")
    return "\n".join(lines)

def build_release_commit_metadata(ref: str, version: str, cwd: str) -> Dict[str, str]:
    metadata = get_commit_metadata(ref, cwd)
    return {
        **metadata,
        "message": f"release {version}"
    }

def execute_release_merge(plan: Dict[str, Any], cwd: str) -> None:
    if not plan.get("windows"):
        raise RuntimeError("No unreleased release commits detected. Nothing to merge.")

    if not is_working_tree_clean(cwd):
        raise RuntimeError("Working tree must be clean before executing a release merge.")

    original_branch = get_current_branch_name(cwd)
    release_exists = local_branch_exists(RELEASE_BRANCH, cwd)
    original_release_sha = resolve_commit_sha(RELEASE_BRANCH, cwd) if release_exists else None
    updated_release_sha = original_release_sha

    created_release_branch = False

    try:
        for window in plan.get("windows", []):
            target_commit = window["commits"][-1] if window["commits"] else None
            if not target_commit or not target_commit.get("sha"):
                raise RuntimeError(f"Unable to determine the source commit for release {window.get('version')}.")

            tree_sha = resolve_tree_sha(target_commit["sha"], cwd)
            metadata = build_release_commit_metadata(target_commit["sha"], window["version"], cwd)
            parents = [] if updated_release_sha is None else [updated_release_sha]
            updated_release_sha = create_commit_from_tree(tree_sha, parents, metadata, cwd)

        if updated_release_sha is None or updated_release_sha == original_release_sha:
            raise RuntimeError("Release merge did not create any new commits.")

        if release_exists:
            git_force_branch(RELEASE_BRANCH, updated_release_sha, cwd)
        else:
            git_create_branch(RELEASE_BRANCH, updated_release_sha, cwd)
            created_release_branch = True

        git_checkout(RELEASE_BRANCH, cwd)
    except Exception as error:
        try:
            if release_exists:
                git_force_branch(RELEASE_BRANCH, original_release_sha, cwd)
        except Exception:
            pass

        try:
            git_checkout(original_branch, cwd)
        except Exception:
            pass

        try:
            if created_release_branch:
                git_delete_branch(RELEASE_BRANCH, cwd)
        except Exception:
            pass

        print(str(error))
        print(build_recovery_message(original_branch, original_release_sha, created_release_branch))
        raise RuntimeError("Release merge aborted.")

def execute_release_tag_plan(plan: Dict[str, Any], cwd: str) -> None:
    if not plan.get("tags"):
        raise RuntimeError("No release tag changes detected. Nothing to tag.")

    for tag in plan.get("tags", []):
        if tag.get("needsMove") and tag.get("existingTagName"):
            git_delete_tag(tag["existingTagName"], cwd)
        
        git_create_annotated_tag(tag["tagName"], tag["targetSha"], f"release {tag['version']}", cwd)
