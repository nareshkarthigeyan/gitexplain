import json
import os
import time
from typing import Any, Callable, Dict, Optional, Tuple
import requests

from .cache import create_cache_key, read_cache, write_cache
from .prompt import build_prompt
from .usage import append_usage_record, estimate_cost_usd, resolve_pricing

SUPPORTED_PROVIDERS = {
    "openai",
    "groq",
    "openrouter",
    "gemini",
    "ollama",
    "chutes",
    "anthropic",
    "mistral",
    "azure-openai"
}

SYSTEM_PROMPT = "You explain Git commits clearly and accurately for developers."
REQUEST_TIMEOUT_SEC = 30.0
REQUEST_RETRIES = 2
RETRYABLE_STATUS_CODES = {408, 425, 429, 500, 502, 503, 504}

def get_provider_config(provider_override: Optional[str] = None, model_override: Optional[str] = None) -> Dict[str, Any]:
    provider = (provider_override or os.environ.get("LLM_PROVIDER") or "openai").lower()

    if provider not in SUPPORTED_PROVIDERS:
        raise ValueError(
            f'Unsupported provider "{provider}". Supported providers: {", ".join(sorted(SUPPORTED_PROVIDERS))}.'
        )

    if provider == "openai":
        return {
            "provider": provider,
            "apiKey": os.environ.get("OPENAI_API_KEY"),
            "baseUrl": os.environ.get("OPENAI_BASE_URL") or "https://api.openai.com/v1",
            "model": model_override or os.environ.get("OPENAI_MODEL") or os.environ.get("LLM_MODEL") or "gpt-4.1-mini"
        }

    if provider == "groq":
        return {
            "provider": provider,
            "apiKey": os.environ.get("GROQ_API_KEY"),
            "baseUrl": os.environ.get("GROQ_BASE_URL") or "https://api.groq.com/openai/v1",
            "model": model_override or os.environ.get("GROQ_MODEL") or os.environ.get("LLM_MODEL") or "llama-3.3-70b-versatile"
        }

    if provider == "openrouter":
        return {
            "provider": provider,
            "apiKey": os.environ.get("OPENROUTER_API_KEY"),
            "baseUrl": os.environ.get("OPENROUTER_BASE_URL") or "https://openrouter.ai/api/v1",
            "model": model_override or os.environ.get("OPENROUTER_MODEL") or os.environ.get("LLM_MODEL") or "openai/gpt-4.1-mini"
        }

    if provider == "gemini":
        return {
            "provider": provider,
            "apiKey": os.environ.get("GEMINI_API_KEY"),
            "baseUrl": os.environ.get("GEMINI_BASE_URL") or "https://generativelanguage.googleapis.com/v1beta",
            "model": model_override or os.environ.get("GEMINI_MODEL") or os.environ.get("LLM_MODEL") or "gemini-2.5-flash"
        }

    if provider == "chutes":
        return {
            "provider": provider,
            "apiKey": os.environ.get("CHUTES_API_KEY"),
            "baseUrl": os.environ.get("CHUTES_BASE_URL") or "https://llm.chutes.ai/v1",
            "model": model_override or os.environ.get("CHUTES_MODEL") or os.environ.get("LLM_MODEL") or "deepseek-ai/DeepSeek-V3-0324"
        }

    if provider == "anthropic":
        return {
            "provider": provider,
            "apiKey": os.environ.get("ANTHROPIC_API_KEY"),
            "baseUrl": os.environ.get("ANTHROPIC_BASE_URL") or "https://api.anthropic.com/v1",
            "model": model_override or os.environ.get("ANTHROPIC_MODEL") or os.environ.get("LLM_MODEL") or "claude-3-5-haiku-latest"
        }

    if provider == "mistral":
        return {
            "provider": provider,
            "apiKey": os.environ.get("MISTRAL_API_KEY"),
            "baseUrl": os.environ.get("MISTRAL_BASE_URL") or "https://api.mistral.ai/v1",
            "model": model_override or os.environ.get("MISTRAL_MODEL") or os.environ.get("LLM_MODEL") or "mistral-small-latest"
        }

    if provider == "azure-openai":
        deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT") or model_override or os.environ.get("AZURE_OPENAI_MODEL") or os.environ.get("LLM_MODEL")
        return {
            "provider": provider,
            "apiKey": os.environ.get("AZURE_OPENAI_API_KEY"),
            "baseUrl": os.environ.get("AZURE_OPENAI_BASE_URL"),
            "model": os.environ.get("AZURE_OPENAI_MODEL") or deployment,
            "deployment": deployment,
            "apiVersion": os.environ.get("AZURE_OPENAI_API_VERSION") or "2024-10-21"
        }

    # Default: ollama
    return {
        "provider": provider,
        "apiKey": os.environ.get("OLLAMA_API_KEY") or "ollama",
        "baseUrl": os.environ.get("OLLAMA_BASE_URL") or "http://127.0.0.1:11434/v1",
        "model": model_override or os.environ.get("OLLAMA_MODEL") or os.environ.get("LLM_MODEL") or "llama3.2"
    }

def validate_provider_config(config: Dict[str, Any]) -> None:
    if not config.get("model"):
        raise ValueError(f'No model configured for provider "{config.get("provider")}".')

    if config.get("provider") == "azure-openai":
        if not config.get("baseUrl"):
            raise ValueError('Missing base URL for provider "azure-openai". Set AZURE_OPENAI_BASE_URL.')
        if not config.get("deployment"):
            raise ValueError('Missing deployment for provider "azure-openai". Set AZURE_OPENAI_DEPLOYMENT.')

    if config.get("provider") != "ollama" and not config.get("apiKey"):
        raise ValueError(f'Missing API key for provider "{config.get("provider")}".')

def build_openai_compatible_headers(config: Dict[str, Any]) -> Dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if config.get("provider") == "azure-openai":
        headers["api-key"] = config.get("apiKey", "")
    else:
        headers["Authorization"] = f"Bearer {config.get('apiKey', '')}"

    if config.get("provider") == "openrouter":
        headers["HTTP-Referer"] = os.environ.get("OPENROUTER_SITE_URL") or "https://github.com"
        headers["X-Title"] = os.environ.get("OPENROUTER_APP_NAME") or "gx"

    return headers

def extract_usage(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    return data.get("usage")

def extract_openai_content(data: Dict[str, Any]) -> str:
    choices = data.get("choices", [])
    if choices and len(choices) > 0:
        content = choices[0].get("message", {}).get("content", "")
        return content.strip() or "No explanation returned by the model."
    return "No explanation returned by the model."

def extract_gemini_text(data: Dict[str, Any]) -> str:
    candidates = data.get("candidates", [])
    if candidates and len(candidates) > 0:
        parts = candidates[0].get("content", {}).get("parts", [])
        return "\n".join(part.get("text", "") for part in parts if part.get("text")).strip()
    return ""

def extract_anthropic_content(data: Dict[str, Any]) -> str:
    content = data.get("content", [])
    text_parts = []
    for item in content:
        if item.get("type") == "text" and isinstance(item.get("text"), str):
            text_parts.append(item["text"])
    return "\n".join(text_parts).strip()

def send_request_with_retry(method: str, url: str, headers: Dict[str, str], json_data: Dict[str, Any], stream: bool = False) -> requests.Response:
    for attempt in range(REQUEST_RETRIES + 1):
        try:
            response = requests.request(
                method,
                url,
                headers=headers,
                json=json_data,
                timeout=REQUEST_TIMEOUT_SEC,
                stream=stream
            )
            if response.status_code in RETRYABLE_STATUS_CODES and attempt < REQUEST_RETRIES:
                time.sleep(0.25 * (attempt + 1))
                continue
            return response
        except (requests.Timeout, requests.ConnectionError) as error:
            if attempt >= REQUEST_RETRIES:
                if isinstance(error, requests.Timeout):
                    raise RuntimeError(f"Request timed out after {int(REQUEST_TIMEOUT_SEC * 1000)}ms.")
                raise error
            time.sleep(0.25 * (attempt + 1))
    raise RuntimeError("Request failed after retries.")

def consume_sse_stream(response: requests.Response, get_chunk_text: Callable[[Dict[str, Any]], str], on_chunk: Optional[Callable[[str], None]]) -> str:
    full_text = ""
    # Iterate over stream lines
    for line in response.iter_lines(decode_unicode=True):
        if not line:
            continue
        trimmed = line.strip()
        if trimmed.startswith("data:"):
            data_content = trimmed[5:].strip()
            if data_content == "[DONE]":
                continue
            try:
                parsed = json.loads(data_content)
                chunk_text = get_chunk_text(parsed)
                if chunk_text:
                    full_text += chunk_text
                    if on_chunk:
                        on_chunk(chunk_text)
            except Exception:
                continue
    return full_text.strip()

def request_openai_compatible(config: Dict[str, Any], prompt: str, options: Dict[str, Any]) -> Dict[str, Any]:
    started_at = int(time.time() * 1000)
    
    if config.get("provider") == "azure-openai":
        import urllib.parse
        deployment = urllib.parse.quote(config.get("deployment", ""))
        api_ver = urllib.parse.quote(config.get("apiVersion", ""))
        endpoint = f"{config.get('baseUrl')}/openai/deployments/{deployment}/chat/completions?api-version={api_ver}"
    else:
        endpoint = f"{config.get('baseUrl')}/chat/completions"

    body = {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2,
        "stream": options.get("stream") is True
    }

    if config.get("provider") != "azure-openai":
        body["model"] = config.get("model")

    response = send_request_with_retry(
        "POST",
        endpoint,
        headers=build_openai_compatible_headers(config),
        json_data=body,
        stream=options.get("stream") is True
    )

    if not response.ok:
        raise RuntimeError(f"{config.get('provider')} request failed ({response.status_code}): {response.text}")

    if options.get("stream"):
        def get_chunk_text(data):
            choices = data.get("choices", [])
            if not choices:
                return ""
            delta = choices[0].get("delta", {})
            content = delta.get("content")
            if isinstance(content, str):
                return content
            elif isinstance(content, list):
                return "".join(item.get("text", "") for item in content)
            return ""

        explanation = consume_sse_stream(response, get_chunk_text, options.get("onChunk"))
        return {
            "explanation": explanation,
            "responseMeta": {
                "provider": config.get("provider"),
                "model": config.get("model"),
                "cacheHit": False,
                "latencyMs": int(time.time() * 1000) - started_at,
                "usage": None
            }
        }

    data = response.json()
    return {
        "explanation": extract_openai_content(data),
        "responseMeta": {
            "provider": config.get("provider"),
            "model": config.get("model"),
            "cacheHit": False,
            "latencyMs": int(time.time() * 1000) - started_at,
            "usage": extract_usage(data)
        }
    }

def request_anthropic(config: Dict[str, Any], prompt: str, options: Dict[str, Any]) -> Dict[str, Any]:
    started_at = int(time.time() * 1000)
    headers = {
        "Content-Type": "application/json",
        "x-api-key": config.get("apiKey", ""),
        "anthropic-version": "2023-06-01"
    }
    body = {
        "model": config.get("model"),
        "system": SYSTEM_PROMPT,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 2048,
        "temperature": 0.2,
        "stream": options.get("stream") is True
    }

    response = send_request_with_retry(
        "POST",
        f"{config.get('baseUrl')}/messages",
        headers=headers,
        json_data=body,
        stream=options.get("stream") is True
    )

    if not response.ok:
        raise RuntimeError(f"anthropic request failed ({response.status_code}): {response.text}")

    if options.get("stream"):
        def get_chunk_text(data):
            if data.get("type") == "content_block_delta":
                return data.get("delta", {}).get("text", "")
            return ""

        explanation = consume_sse_stream(response, get_chunk_text, options.get("onChunk"))
        return {
            "explanation": explanation,
            "responseMeta": {
                "provider": config.get("provider"),
                "model": config.get("model"),
                "cacheHit": False,
                "latencyMs": int(time.time() * 1000) - started_at,
                "usage": None
            }
        }

    data = response.json()
    return {
        "explanation": extract_anthropic_content(data) or "No explanation returned by the model.",
        "responseMeta": {
            "provider": config.get("provider"),
            "model": config.get("model"),
            "cacheHit": False,
            "latencyMs": int(time.time() * 1000) - started_at,
            "usage": data.get("usage")
        }
    }

def request_gemini(config: Dict[str, Any], prompt: str, options: Dict[str, Any]) -> Dict[str, Any]:
    started_at = int(time.time() * 1000)
    import urllib.parse
    api_key_escaped = urllib.parse.quote(config.get("apiKey", ""))
    
    if options.get("stream"):
        endpoint = f"{config.get('baseUrl')}/models/{config.get('model')}:streamGenerateContent?alt=sse&key={api_key_escaped}"
    else:
        endpoint = f"{config.get('baseUrl')}/models/{config.get('model')}:generateContent?key={api_key_escaped}"

    headers = {"Content-Type": "application/json"}
    body = {
        "systemInstruction": {
            "parts": [{"text": SYSTEM_PROMPT}]
        },
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt}]
            }
        ],
        "generationConfig": {
            "temperature": 0.2
        }
    }

    response = send_request_with_retry(
        "POST",
        endpoint,
        headers=headers,
        json_data=body,
        stream=options.get("stream") is True
    )

    if not response.ok:
        raise RuntimeError(f"gemini request failed ({response.status_code}): {response.text}")

    if options.get("stream"):
        explanation = consume_sse_stream(response, extract_gemini_text, options.get("onChunk"))
        return {
            "explanation": explanation,
            "responseMeta": {
                "provider": config.get("provider"),
                "model": config.get("model"),
                "cacheHit": False,
                "latencyMs": int(time.time() * 1000) - started_at,
                "usage": None
            }
        }

    data = response.json()
    return {
        "explanation": extract_gemini_text(data).strip() or "No explanation returned by the model.",
        "responseMeta": {
            "provider": config.get("provider"),
            "model": config.get("model"),
            "cacheHit": False,
            "latencyMs": int(time.time() * 1000) - started_at,
            "usage": data.get("usageMetadata")
        }
    }

def generate_explanation(params: Dict[str, Any]) -> Dict[str, Any]:
    mode = params.get("mode")
    commit_data = params.get("commitData", {})
    provider_override = params.get("providerOverride")
    model_override = params.get("modelOverride")
    max_diff_lines = params.get("maxDiffLines")
    no_cache = params.get("noCache", False)
    stream = params.get("stream", False)
    on_chunk = params.get("onChunk")
    on_start = params.get("onStart")

    config = get_provider_config(provider_override, model_override)
    validate_provider_config(config)

    prompt, prompt_meta = build_prompt(mode, commit_data, {"maxDiffLines": max_diff_lines})
    
    if on_start:
        on_start({
            "promptMeta": prompt_meta,
            "provider": config.get("provider"),
            "model": config.get("model")
        })

    cache_key = create_cache_key({
        "targetRef": commit_data.get("targetRef"),
        "mode": mode,
        "provider": config.get("provider"),
        "model": config.get("model"),
        "prompt": prompt
    })

    cached = None if no_cache else read_cache(cache_key)

    if cached:
        response_meta = cached.get("responseMeta", {})
        response_meta["cacheHit"] = True
        return {
            "explanation": cached.get("explanation"),
            "promptMeta": prompt_meta,
            "responseMeta": response_meta
        }

    request_options = {"stream": stream, "onChunk": on_chunk}
    provider = config.get("provider")

    if provider == "gemini":
        result = request_gemini(config, prompt, request_options)
    elif provider == "anthropic":
        result = request_anthropic(config, prompt, request_options)
    else:
        result = request_openai_compatible(config, prompt, request_options)

    pricing = resolve_pricing(config)
    estimated_cost = estimate_cost_usd(result["responseMeta"]["usage"], pricing)
    result["responseMeta"]["estimatedCostUsd"] = estimated_cost

    append_usage_record({
        "provider": result["responseMeta"]["provider"],
        "model": result["responseMeta"]["model"],
        "usage": result["responseMeta"]["usage"],
        "latencyMs": result["responseMeta"]["latencyMs"],
        "estimatedCostUsd": estimated_cost
    })

    if not no_cache:
        write_cache(cache_key, {
            "explanation": result["explanation"],
            "responseMeta": result["responseMeta"]
        })

    return {
        "explanation": result["explanation"],
        "promptMeta": prompt_meta,
        "responseMeta": result["responseMeta"]
    }
