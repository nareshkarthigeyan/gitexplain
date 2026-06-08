import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

def get_usage_log_path() -> str:
    primary = Path.home() / ".gx" / "usage.jsonl"
    fallback = Path.home() / ".gitxplain" / "usage.jsonl"
    if not primary.exists() and fallback.exists():
        return str(fallback)
    return str(primary)

def get_usage_log_file() -> str:
    return get_usage_log_path()

def read_records() -> List[Dict[str, Any]]:
    file_path = Path(get_usage_log_path())
    if not file_path.exists():
        return []
    records = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                trimmed = line.strip()
                if trimmed:
                    records.append(json.loads(trimmed))
    except Exception:
        pass
    return records

def parse_numeric(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    return 0.0

def normalize_usage_metrics(usage: Any) -> Dict[str, int]:
    if not usage or not isinstance(usage, dict):
        return {
            "inputTokens": 0,
            "outputTokens": 0,
            "totalTokens": 0
        }

    input_tokens = int(
        parse_numeric(usage.get("prompt_tokens")) or
        parse_numeric(usage.get("input_tokens")) or
        parse_numeric(usage.get("promptTokenCount"))
    )
    output_tokens = int(
        parse_numeric(usage.get("completion_tokens")) or
        parse_numeric(usage.get("output_tokens")) or
        parse_numeric(usage.get("candidatesTokenCount"))
    )
    total_tokens = int(
        parse_numeric(usage.get("total_tokens")) or
        parse_numeric(usage.get("totalTokenCount")) or
        (input_tokens + output_tokens)
    )

    return {
        "inputTokens": input_tokens,
        "outputTokens": output_tokens,
        "totalTokens": total_tokens
    }

def parse_env_price(env_key: str) -> Optional[float]:
    raw = os.environ.get(env_key)
    if raw is None or raw == "":
        return None
    try:
        parsed = float(raw)
        if parsed >= 0:
            return parsed
    except ValueError:
        pass
    return None

def resolve_pricing(config: Dict[str, Any]) -> Optional[Dict[str, float]]:
    provider = config.get("provider", "openai")
    model = config.get("model", "default")

    def clean_key(s: str) -> str:
        import re
        return re.sub(r'[^A-Z0-9]+', '_', str(s).upper())

    provider_key = clean_key(provider)
    model_key = clean_key(model)

    input_per_million = (
        parse_env_price(f"{provider_key}_{model_key}_INPUT_COST_PER_MTOK") or
        parse_env_price(f"{provider_key}_INPUT_COST_PER_MTOK") or
        parse_env_price("LLM_INPUT_COST_PER_MTOK")
    )
    output_per_million = (
        parse_env_price(f"{provider_key}_{model_key}_OUTPUT_COST_PER_MTOK") or
        parse_env_price(f"{provider_key}_OUTPUT_COST_PER_MTOK") or
        parse_env_price("LLM_OUTPUT_COST_PER_MTOK")
    )

    if input_per_million is None or output_per_million is None:
        return None

    return {
        "inputPerMillion": input_per_million,
        "outputPerMillion": output_per_million
    }

def estimate_cost_usd(usage: Any, pricing: Optional[Dict[str, float]]) -> Optional[float]:
    if not pricing:
        return None

    metrics = normalize_usage_metrics(usage)
    cost_usd = (
        (metrics["inputTokens"] / 1_000_000.0) * pricing["inputPerMillion"] +
        (metrics["outputTokens"] / 1_000_000.0) * pricing["outputPerMillion"]
    )
    return cost_usd

def append_usage_record(data: Dict[str, Any]) -> None:
    provider = data.get("provider")
    model = data.get("model")
    usage = data.get("usage")
    latency_ms = data.get("latencyMs")
    estimated_cost_usd_val = data.get("estimatedCostUsd")

    metrics = normalize_usage_metrics(usage)
    if metrics["totalTokens"] == 0 and estimated_cost_usd_val is None:
        return

    file_path = Path(get_usage_log_path())
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    record = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "provider": provider,
        "model": model,
        "usage": metrics,
        "latencyMs": latency_ms,
        "estimatedCostUsd": estimated_cost_usd_val
    }

    with open(file_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")

def get_usage_stats() -> Dict[str, Any]:
    records = read_records()
    summary = {
        "requestCount": 0,
        "inputTokens": 0,
        "outputTokens": 0,
        "totalTokens": 0,
        "estimatedCostUsd": 0.0
    }
    for record in records:
        summary["requestCount"] += 1
        usage = record.get("usage", {})
        summary["inputTokens"] += int(parse_numeric(usage.get("inputTokens")))
        summary["outputTokens"] += int(parse_numeric(usage.get("outputTokens")))
        summary["totalTokens"] += int(parse_numeric(usage.get("totalTokens")))
        summary["estimatedCostUsd"] += parse_numeric(record.get("estimatedCostUsd"))
    return summary

def clear_usage_log() -> int:
    file_path = Path(get_usage_log_path())
    count = len(read_records())
    if file_path.exists():
        try:
            file_path.unlink()
        except Exception:
            pass
    return count
