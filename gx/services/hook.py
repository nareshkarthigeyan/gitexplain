import os
from pathlib import Path
from .git import run_git_command

HOOK_MARKER = "# gx-hook"
FALLBACK_HOOK_MARKER = "# gitxplain-hook"

def build_hook_script(hook_name: str, output_dir: str) -> str:
    if hook_name == "post-commit":
        return f"""#!/bin/sh
{HOOK_MARKER}
gx HEAD --summary --markdown --quiet > "{os.path.join(output_dir, 'last-explanation.md')}" 2>/dev/null || true
"""
    if hook_name == "post-merge":
        return f"""#!/bin/sh
{HOOK_MARKER}
gx HEAD --summary --markdown --quiet > "{os.path.join(output_dir, 'last-merge-explanation.md')}" 2>/dev/null || true
"""
    if hook_name == "pre-push":
        return f"""#!/bin/sh
{HOOK_MARKER}
gx HEAD --security --markdown --quiet > "{os.path.join(output_dir, 'last-pre-push-security.md')}" 2>/dev/null || true
"""
    raise ValueError(f'Unsupported hook "{hook_name}". Supported hooks: post-commit, post-merge, pre-push.')

def install_hook(cwd: str, hook_name: str = "post-commit") -> str:
    git_dir = run_git_command(["rev-parse", "--git-dir"], cwd)
    hook_dir = Path(cwd).joinpath(git_dir, "hooks").resolve()
    
    primary_output_dir = Path(cwd).joinpath(git_dir, "gx").resolve()
    fallback_output_dir = Path(cwd).joinpath(git_dir, "gitxplain").resolve()
    if not primary_output_dir.exists() and fallback_output_dir.exists():
        output_dir = fallback_output_dir
    else:
        output_dir = primary_output_dir
        
    hook_path = hook_dir / hook_name

    hook_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    script = build_hook_script(hook_name, str(output_dir))

    if hook_path.exists():
        with open(hook_path, "r", encoding="utf-8") as f:
            existing = f.read()
        if HOOK_MARKER not in existing and FALLBACK_HOOK_MARKER not in existing:
            raise RuntimeError(
                f"Hook {hook_name} already exists at {hook_path}. Refusing to overwrite a non-gx hook."
            )

    with open(hook_path, "w", encoding="utf-8") as f:
        f.write(script)
    
    os.chmod(hook_path, 0o755)
    return str(hook_path)
