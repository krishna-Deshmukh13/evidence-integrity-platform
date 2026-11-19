"""Pluggable language model. Online Free AI by default; Google Gemini, Groq, Ollama, Anthropic and OpenAI built in.
Only text (the structured findings or forensic questions) is ever sent, never the evidence file."""
import os
import httpx

OPENAI_COMPAT = {  # provider -> (base url, default model)
    "free_online": ("https://text.pollinations.ai/openai", "openai"),
    "openai": ("https://api.openai.com/v1", "gpt-4o-mini"),
    "groq": ("https://api.groq.com/openai/v1", "llama-3.3-70b-versatile"),
    "openrouter": ("https://openrouter.ai/api/v1", "google/gemini-2.0-flash-lite-preview-02-05:free"),
    "deepseek": ("https://api.deepseek.com/v1", "deepseek-chat"),
    "mistral": ("https://api.mistral.ai/v1", "mistral-small-latest"),
    "together": ("https://api.together.xyz/v1", "meta-llama/Llama-3.3-70B-Instruct-Turbo"),
    "lmstudio": ("http://localhost:1234/v1", "local-model"),
    "openai_compatible": ("", ""),
}
PROVIDERS = ["free_online", "gemini", "groq", "ollama", "openrouter", "anthropic", "openai", "none"] + list(OPENAI_COMPAT)
TIMEOUT = 30.0


class LLMError(Exception):
    pass


def settings():
    provider = os.environ.get("LLM_PROVIDER", "free_online").strip().lower()
    if not provider or provider in ("none", "disabled", "offline"):
        provider = "none"
    elif provider not in PROVIDERS:
        provider = "free_online"

    default_model = {
        "none": "deterministic",
        "free_online": "openai",
        "gemini": "gemini-2.0-flash",
        "groq": "llama-3.3-70b-versatile",
        "openrouter": "google/gemini-2.0-flash-lite-preview-02-05:free",
        "ollama": "qwen2.5:7b",
        "anthropic": "claude-sonnet-5-5",
    }.get(provider) or OPENAI_COMPAT.get(provider, ("", ""))[1]

    return {
        "provider": provider,
        "model": os.environ.get("LLM_MODEL") or default_model,
        "key": os.environ.get("LLM_API_KEY", ""),
        "base_url": os.environ.get("LLM_BASE_URL", "").rstrip("/")
    }


def enabled() -> bool:
    return settings()["provider"] not in ("none", "disabled", "offline", "")


def build_request(system: str, user: str, max_tokens: int = 1200, cfg: dict = None):
    """-> (url, headers, json body). Pure function so every adapter can be tested without a network."""
    c = cfg or settings()
    p, model, key, base = c["provider"], c["model"], c["key"], c["base_url"]

    if p == "ollama":
        return (f"{base or 'http://localhost:11434'}/api/chat", {},
                {"model": model, "stream": False, "options": {"temperature": 0.2, "num_predict": max_tokens},
                 "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]})

    if p == "anthropic":
        return (f"{base or 'https://api.anthropic.com'}/v1/messages",
                {"x-api-key": key, "anthropic-version": "2023-06-01"},
                {"model": model, "max_tokens": max_tokens, "temperature": 0.2, "system": system,
                 "messages": [{"role": "user", "content": user}]})

    if p == "gemini":
        model_name = model or "gemini-2.0-flash"
        return (f"{base or 'https://generativelanguage.googleapis.com'}/v1beta/models/{model_name}:generateContent",
                {"x-goog-api-key": key} if key else {},
                {"systemInstruction": {"parts": [{"text": system}]},
                 "contents": [{"role": "user", "parts": [{"text": user}]}],
                 "generationConfig": {"temperature": 0.2, "maxOutputTokens": max_tokens}})

    if p in OPENAI_COMPAT:
        url = (base or OPENAI_COMPAT[p][0])
        if not url:
            raise LLMError("LLM_BASE_URL is required for openai_compatible")
        endpoint = f"{url}/chat/completions" if not url.endswith("/chat/completions") else url
        headers = {"Content-Type": "application/json"}
        if key:
            headers["Authorization"] = f"Bearer {key}"
        return (endpoint, headers,
                {"model": model or OPENAI_COMPAT[p][1], "temperature": 0.2, "max_tokens": max_tokens,
                 "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]})

    raise LLMError("No language model configured")


def parse_response(provider: str, data: dict) -> str:
    try:
        if provider == "ollama":
            return data["message"]["content"].strip()
        if provider == "anthropic":
            return "".join(b.get("text", "") for b in data["content"] if b.get("type") == "text").strip()
        if provider == "gemini":
            return "".join(p.get("text", "") for p in data["candidates"][0]["content"]["parts"]).strip()
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMError(f"Unexpected answer format from {provider}: {exc}")


def complete(system: str, user: str, max_tokens: int = 1200) -> str:
    cfg = settings()
    if not enabled() or cfg["provider"] == "none":
        raise LLMError("External AI summaries are turned off (offline air-gapped mode). No case or file data leaves the system.")

    # Primary attempt
    try:
        url, headers, body = build_request(system, user, max_tokens, cfg)
        r = httpx.post(url, headers=headers, json=body, timeout=TIMEOUT)
        if r.status_code < 400:
            text = parse_response(cfg["provider"], r.json())
            if text:
                return text
    except Exception as exc:
        # Never fall back to external web endpoints if provider is offline or local
        if cfg["provider"] in ("none", "ollama", "lmstudio"):
            raise LLMError(f"Model call failed: {exc}")
        # If configured provider was not free_online, try free_online as automatic fallback
        if cfg["provider"] != "free_online":
            try:
                fallback_cfg = {"provider": "free_online", "model": "openai", "key": "", "base_url": ""}
                url, headers, body = build_request(system, user, max_tokens, fallback_cfg)
                r = httpx.post(url, headers=headers, json=body, timeout=TIMEOUT)
                if r.status_code < 400:
                    text = parse_response("free_online", r.json())
                    if text:
                        return text
            except Exception:
                pass
        raise LLMError(f"Model call failed: {exc}")

    raise LLMError("The language model returned an empty answer")


def status() -> dict:
    """For the top-bar indicator and settings modal."""
    c = settings()
    if c["provider"] == "none":
        return {"provider": "none", "model": "deterministic", "online": False, "label": "Local Knowledge Engine (Offline Air-Gapped)"}
    if c["provider"] == "free_online":
        return {"provider": "free_online", "model": c["model"] or "openai", "online": True, "label": "Free Online AI (ChatGPT)"}
    if c["provider"] == "gemini":
        online = bool(c["key"])
        return {"provider": "gemini", "model": c["model"] or "gemini-2.0-flash", "online": online, "label": f"Google Gemini ({c['model']})"}
    if c["provider"] == "groq":
        online = bool(c["key"])
        return {"provider": "groq", "model": c["model"] or "llama-3.3-70b-versatile", "online": online, "label": f"Groq Llama ({c['model']})"}

    online = False
    if c["provider"] in ("ollama", "lmstudio") or c["base_url"]:
        try:
            base = c["base_url"] or ("http://localhost:11434" if c["provider"] == "ollama" else "http://localhost:1234/v1")
            path = "/api/tags" if c["provider"] == "ollama" else "/models"
            online = httpx.get(base + path, timeout=1.5).status_code < 400
        except httpx.HTTPError:
            online = False
    else:
        online = bool(c["key"])
    return {"provider": c["provider"], "model": c["model"], "online": online, "label": c["model"]}
