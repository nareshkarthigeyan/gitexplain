import os
from pathlib import Path

def load_env_file(cwd: str = None) -> None:
    if cwd is None:
        cwd = os.getcwd()
    try:
        # Get directory of env.py
        file_dir = Path(__file__).resolve().parent
        # Go up two levels to get package/project root
        project_dir = file_dir.parent.parent
        env_path = project_dir / ".env"

        cwd_env_path = Path(cwd) / ".env"
        final_env_path = None

        if env_path.exists():
            final_env_path = env_path
        elif cwd_env_path.exists():
            final_env_path = cwd_env_path

        if final_env_path and final_env_path.exists():
            with open(final_env_path, "r", encoding="utf-8") as f:
                content = f.read()
            for line in content.splitlines():
                trimmed = line.strip()
                if trimmed and not trimmed.startswith("#"):
                    if "=" in trimmed:
                        key, *value_parts = trimmed.split("=")
                        value = "=".join(value_parts).strip()
                        # Remove leading/trailing quotes
                        if len(value) >= 2 and (
                            (value.startswith('"') and value.endswith('"')) or
                            (value.startswith("'") and value.endswith("'"))
                        ):
                            value = value[1:-1].strip()
                        key = key.strip()
                        if key and value and key not in os.environ:
                            os.environ[key] = value
    except Exception:
        # Silently ignore errors
        pass
