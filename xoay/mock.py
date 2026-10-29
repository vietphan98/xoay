"""Chế độ demo: giả lập model với quota rất nhỏ để thấy việc tự đổi model."""
from __future__ import annotations
import time
from .config import Config, ModelSpec
from .providers import QuotaError, estimate_tokens

def demo_config(state_file) -> Config:
    return Config(state_file=state_file, models=[
        ModelSpec("chinh-pro", "mock", "mock/pro", rpd=2),
        ModelSpec("openrouter-free", "mock", "mock/or-free", rpd=50),
        ModelSpec("gemini-flash", "mock", "mock/gemini", rpd=1500),
        ModelSpec("ollama-local", "mock", "mock/ollama"),
    ])

class MockBackend:
    """Mỗi model trả 429 sau `fail_after` lần gọi (giả lập phía server)."""
    def __init__(self, fail_after: int = 2, delay: float = 0.6):
        self.calls: dict[str, int] = {}; self.fail_after, self.delay = fail_after, delay
    def __call__(self, spec: ModelSpec, messages):
        time.sleep(self.delay)
        n = self.calls.get(spec.name, 0)
        if spec.name != "ollama-local" and n >= self.fail_after:
            raise QuotaError("HTTP 429: Too Many Requests (giả lập)")
        self.calls[spec.name] = n + 1
        last = messages[-1]["content"]
        turns = sum(1 for m in messages if m["role"] == "user")
        return (f"[{spec.name}] Đã nhận câu hỏi #{turns} (ngữ cảnh {len(messages)} tin nhắn): "
                f"\"{last[:50]}\""), estimate_tokens(messages)

DEMO_PROMPTS = [
    "Viết hàm fibonacci bằng Python",
    "Thêm memo hoá cho hàm đó",
    "Viết test cho hàm fibonacci",
    "Giải thích độ phức tạp",
    "Đổi sang dạng vòng lặp",
    "Thêm type hint",
    "Tóm tắt những gì ta đã làm",
]
