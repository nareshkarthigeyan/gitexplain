import hashlib
import json
import os
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

CACHE_TTL_MS = 7 * 24 * 60 * 60 * 1000
MAX_CACHE_FILES = 200

def get_cache_dir() -> Path:
    primary = Path.home() / ".gx" / "cache"
    fallback = Path.home() / ".gitxplain" / "cache"
    if not primary.exists() and fallback.exists():
        return fallback
    return primary

def get_cache_directory() -> str:
    return str(get_cache_dir())

def create_cache_key(parts: Any) -> str:
    # Sort keys to ensure deterministic JSON representation
    serialized = json.dumps(parts, sort_keys=True)
    hasher = hashlib.sha256()
    hasher.update(serialized.encode("utf-8"))
    return hasher.hexdigest()

def get_cache_path(cache_key: str) -> Path:
    return get_cache_dir() / f"{cache_key}.json"

def list_cache_entries() -> List[Dict[str, Any]]:
    directory = get_cache_dir()
    if not directory.exists():
        return []

    entries = []
    for item in directory.glob("*.json"):
        try:
            stat = item.stat()
            entries.append({
                "filePath": item,
                "mtimeMs": stat.st_mtime * 1000,
                "sizeBytes": stat.st_size
            })
        except Exception:
            pass

    # Sort by mtimeMs ascending (oldest first)
    entries.sort(key=lambda x: x["mtimeMs"])
    return entries

def is_expired(mtime_ms: float) -> bool:
    current_time_ms = time.time() * 1000
    return (current_time_ms - mtime_ms) > CACHE_TTL_MS

def prune_cache() -> None:
    entries = list_cache_entries()

    # First, remove expired ones
    for entry in entries:
        if is_expired(entry["mtimeMs"]):
            try:
                entry["filePath"].unlink()
            except Exception:
                pass

    # Refresh list and prune overflow
    remaining = list_cache_entries()
    overflow_count = max(0, len(remaining) - MAX_CACHE_FILES)
    for entry in remaining[:overflow_count]:
        try:
            entry["filePath"].unlink()
        except Exception:
            pass

def read_cache(cache_key: str) -> Optional[Any]:
    file_path = get_cache_path(cache_key)
    if not file_path.exists():
        return None

    try:
        stat = file_path.stat()
        mtime_ms = stat.st_mtime * 1000
        if is_expired(mtime_ms):
            try:
                file_path.unlink()
            except Exception:
                pass
            return None

        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def write_cache(cache_key: str, value: Any) -> None:
    directory = get_cache_dir()
    directory.mkdir(parents=True, exist_ok=True)
    file_path = get_cache_path(cache_key)

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(value, f, indent=2)
        prune_cache()
    except Exception:
        pass

def clear_cache() -> int:
    directory = get_cache_dir()
    entries = list_cache_entries()
    if directory.exists():
        try:
            shutil.rmtree(directory)
        except Exception:
            pass
    return len(entries)

def get_cache_stats() -> Dict[str, Any]:
    entries = list_cache_entries()
    if not entries:
        return {
            "entryCount": 0,
            "totalSizeBytes": 0,
            "oldestEntryIso": None,
            "newestEntryIso": None
        }

    def ms_to_iso(ms: float) -> str:
        return datetime.utcfromtimestamp(ms / 1000.0).isoformat() + "Z"

    return {
        "entryCount": len(entries),
        "totalSizeBytes": sum(entry["sizeBytes"] for entry in entries),
        "oldestEntryIso": ms_to_iso(entries[0]["mtimeMs"]),
        "newestEntryIso": ms_to_iso(entries[-1]["mtimeMs"])
    }
