"""Gọi model qua HTTP (stdlib). Lỗi quota được chuẩn hoá thành QuotaError."""
from __future__ import annotations
import json, urllib.request, urllib.error
from .config import ModelSpec

class QuotaError(Exception):
    """429 / hết quota / rate limit."""
class ProviderError(Exception):
    """Lỗi khác (mạng, thiếu key...)."""

QUOTA_HINTS = ("rate limit", "rate_limit", "quota", "resource_exhausted", "too many requests")

def is_quota_message(text: str) -> bool:
    t = text.lower(); return any(h in t for h in QUOTA_HINTS)

def _post(url: str, body: dict, headers: dict, timeout=120) -> dict:
    req = urllib.request.Request(url, json.dumps(body).encode(), {"Content-Type": "application/json", **headers})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        msg = e.read().decode(errors="replace")
        if e.code == 429 or is_quota_message(msg):
            raise QuotaError(f"HTTP {e.code}: {msg[:200]}") from None
        raise ProviderError(f"HTTP {e.code}: {msg[:200]}") from None
    except urllib.error.URLError as e:
        raise ProviderError(str(e.reason)) from None

def chat(spec: ModelSpec, messages: list[dict]) -> tuple[str, int]:
    """Trả về (nội dung, số token ước lượng)."""
    if spec.provider == "openrouter":
        key = spec.api_key()
        if not key: raise ProviderError(f"Thiếu biến môi trường {spec.api_key_env}")
        d = _post((spec.base_url or "https://openrouter.ai/api/v1") + "/chat/completions",
                  {"model": spec.model, "messages": messages}, {"Authorization": f"Bearer {key}"})
        if "error" in d:
            m = json.dumps(d["error"])
            raise (QuotaError if is_quota_message(m) or d["error"].get("code") == 429 else ProviderError)(m)
        return d["choices"][0]["message"]["content"], d.get("usage", {}).get("total_tokens", 0)
    if spec.provider == "gemini":
        key = spec.api_key()
        if not key: raise ProviderError(f"Thiếu biến môi trường {spec.api_key_env}")
        sys_txt = "\n".join(m["content"] for m in messages if m["role"] == "system")
        contents = [{"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]}
                    for m in messages if m["role"] != "system"]
        body = {"contents": contents}
        if sys_txt: body["systemInstruction"] = {"parts": [{"text": sys_txt}]}
        base = spec.base_url or "https://generativelanguage.googleapis.com/v1beta"
        d = _post(f"{base}/models/{spec.model}:generateContent", body, {"x-goog-api-key": key})
        text = "".join(p.get("text", "") for p in d["candidates"][0]["content"]["parts"])
        return text, d.get("usageMetadata", {}).get("totalTokenCount", 0)
    if spec.provider == "ollama":
        d = _post((spec.base_url or "http://localhost:11434") + "/api/chat",
                  {"model": spec.model, "messages": messages, "stream": False}, {})
        return d["message"]["content"], d.get("prompt_eval_count", 0) + d.get("eval_count", 0)
    raise ProviderError(f"Provider không hỗ trợ: {spec.provider}")

def estimate_tokens(messages: list[dict]) -> int:
    return sum(len(m["content"]) for m in messages) // 4 + 1
