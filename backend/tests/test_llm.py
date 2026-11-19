import httpx
import pytest

from app import llm


def cfg(provider, **kw):
    return {"provider": provider, "model": kw.get("model", "m"), "key": kw.get("key", "K"),
            "base_url": kw.get("base_url", "")}


def test_ollama_request_and_parse():
    url, h, body = llm.build_request("SYS", "USER", 300, cfg("ollama", model="qwen2.5:7b", key=""))
    assert url == "http://localhost:11434/api/chat" and body["stream"] is False and body["model"] == "qwen2.5:7b"
    assert body["messages"][0] == {"role": "system", "content": "SYS"}
    assert llm.parse_response("ollama", {"message": {"content": " hi "}}) == "hi"


@pytest.mark.parametrize("p,host", [("openai", "api.openai.com"), ("groq", "api.groq.com"),
                                    ("openrouter", "openrouter.ai"), ("deepseek", "api.deepseek.com"),
                                    ("mistral", "api.mistral.ai"), ("together", "api.together.xyz"),
                                    ("lmstudio", "localhost:1234")])
def test_openai_compatible(p, host):
    url, h, body = llm.build_request("S", "U", 100, cfg(p))
    assert host in url and url.endswith("/chat/completions") and h["Authorization"] == "Bearer K"
    assert body["messages"][1]["content"] == "U"
    assert llm.parse_response(p, {"choices": [{"message": {"content": "ok"}}]}) == "ok"


def test_custom_base_url_and_missing():
    url, _, _ = llm.build_request("S", "U", 10, cfg("openai_compatible", base_url="http://my.host/v1"))
    assert url == "http://my.host/v1/chat/completions"
    with pytest.raises(llm.LLMError):
        llm.build_request("S", "U", 10, cfg("openai_compatible"))


def test_anthropic_and_gemini():
    url, h, body = llm.build_request("S", "U", 50, cfg("anthropic", model="claude-x"))
    assert url == "https://api.anthropic.com/v1/messages" and h["x-api-key"] == "K"
    assert h["anthropic-version"] == "2023-06-01" and body["system"] == "S" and body["max_tokens"] == 50
    assert llm.parse_response("anthropic", {"content": [{"type": "text", "text": "a"}, {"type": "text", "text": "b"}]}) == "ab"
    url, h, body = llm.build_request("S", "U", 50, cfg("gemini", model="gemini-x"))
    assert "models/gemini-x:generateContent" in url and h["x-goog-api-key"] == "K"
    assert body["systemInstruction"]["parts"][0]["text"] == "S"
    assert llm.parse_response("gemini", {"candidates": [{"content": {"parts": [{"text": "yo"}]}}]}) == "yo"


def test_bad_format_raises():
    for p in ("ollama", "anthropic", "gemini", "openai"):
        with pytest.raises(llm.LLMError):
            llm.parse_response(p, {"weird": 1})


def test_complete_paths(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("LLM_API_KEY", "K")

    def ok(url, headers=None, json=None, timeout=None):
        return httpx.Response(200, json={"choices": [{"message": {"content": "fine"}}]})

    monkeypatch.setattr(httpx, "post", ok)
    assert llm.complete("s", "u") == "fine"
    monkeypatch.setattr(httpx, "post", lambda *a, **k: httpx.Response(401, text="nope"))
    with pytest.raises(llm.LLMError, match="401"):
        llm.complete("s", "u")

    def boom(*a, **k):
        raise httpx.ConnectError("down")

    monkeypatch.setattr(httpx, "post", boom)
    with pytest.raises(llm.LLMError, match="Could not reach"):
        llm.complete("s", "u")
    monkeypatch.setattr(httpx, "post", lambda *a, **k: httpx.Response(200, json={"choices": [{"message": {"content": ""}}]}))
    with pytest.raises(llm.LLMError):
        llm.complete("s", "u")
    monkeypatch.setenv("LLM_PROVIDER", "none")
    with pytest.raises(llm.LLMError):
        llm.complete("s", "u")


def test_status(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "none")
    assert llm.status()["label"] == "template" and not llm.status()["online"]
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("LLM_API_KEY", "")
    assert not llm.status()["online"]
    monkeypatch.setenv("LLM_API_KEY", "x")
    assert llm.status()["online"]
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setattr(httpx, "get", lambda *a, **k: httpx.Response(200, json={}))
    s = llm.status()
    assert s["online"] and s["model"] == "qwen2.5:7b"
    monkeypatch.setattr(httpx, "get", lambda *a, **k: (_ for _ in ()).throw(httpx.ConnectError("x")))
    assert not llm.status()["online"]
