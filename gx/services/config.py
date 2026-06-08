import json
import os
from pathlib import Path
from typing import Any, Dict

ENV_CONFIG_KEYS = {
    "LLM_PROVIDER",
    "LLM_MODEL",
    "OPENAI_API_KEY",
    "OPENAI_MODEL",
    "OPENAI_BASE_URL",
    "GROQ_API_KEY",
    "GROQ_MODEL",
    "GROQ_BASE_URL",
    "OPENROUTER_API_KEY",
    "OPENROUTER_MODEL",
    "OPENROUTER_BASE_URL",
    "OPENROUTER_SITE_URL",
    "OPENROUTER_APP_NAME",
    "GEMINI_API_KEY",
    "GEMINI_MODEL",
    "GEMINI_BASE_URL",
    "OLLAMA_API_KEY",
    "OLLAMA_MODEL",
    "OLLAMA_BASE_URL",
    "CHUTES_API_KEY",
    "CHUTES_MODEL",
    "CHUTES_BASE_URL",
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_MODEL",
    "ANTHROPIC_BASE_URL",
    "MISTRAL_API_KEY",
    "MISTRAL_MODEL",
    "MISTRAL_BASE_URL",
    "AZURE_OPENAI_API_KEY",
    "AZURE_OPENAI_MODEL",
    "AZURE_OPENAI_BASE_URL",
    "AZURE_OPENAI_DEPLOYMENT",
    "AZURE_OPENAI_API_VERSION",
    "LLM_INPUT_COST_PER_MTOK",
    "LLM_OUTPUT_COST_PER_MTOK"
}

PROVIDER_API_KEY_FIELDS = {
    "openai": "OPENAI_API_KEY",
    "groq": "GROQ_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "ollama": "OLLAMA_API_KEY",
    "chutes": "CHUTES_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "mistral": "MISTRAL_API_KEY",
    "azure-openai": "AZURE_OPENAI_API_KEY"
}

def read_json_config(file_path: str) -> Dict[str, Any]:
    path = Path(file_path)
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as error:
        raise RuntimeError(f"Failed to parse config file {file_path}: {str(error)}")

def get_user_config_path() -> str:
    primary = Path.home() / ".gx" / "config.json"
    fallback = Path.home() / ".gitxplain" / "config.json"
    if not primary.exists() and fallback.exists():
        return str(fallback)
    return str(primary)

def load_user_config() -> Dict[str, Any]:
    return read_json_config(get_user_config_path())

def load_config(cwd: str) -> Dict[str, Any]:
    user_config_path = get_user_config_path()
    
    project_config_paths = [
        Path(cwd) / ".gitxplainrc",
        Path(cwd) / ".gitxplainrc.json",
        Path(cwd) / ".gxrc",
        Path(cwd) / ".gxrc.json"
    ]

    config = {}
    config.update(read_json_config(user_config_path))
    for p_path in project_config_paths:
        config.update(read_json_config(str(p_path)))
    return config

def apply_config_environment(config: Dict[str, Any]) -> None:
    for key, value in config.items():
        if key not in ENV_CONFIG_KEYS:
            continue
        if isinstance(value, str) and value != "" and not os.environ.get(key):
            os.environ[key] = value

def get_provider_api_key_field(provider: str) -> str:
    if not provider:
        return None
    return PROVIDER_API_KEY_FIELDS.get(provider.lower())

def write_user_config(next_config: Dict[str, Any]) -> str:
    config_path = get_user_config_path()
    path = Path(config_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(next_config, f, indent=2)
        f.write("\n")
    return config_path

def update_user_config(updates: Dict[str, Any]) -> Dict[str, Any]:
    current_config = load_user_config()
    next_config = {**current_config, **updates}
    config_path = write_user_config(next_config)
    return {"configPath": config_path, "config": next_config}
