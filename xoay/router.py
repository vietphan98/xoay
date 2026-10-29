"""Bộ định tuyến: thử model theo thứ tự, gặp quota thì chuyển model kế tiếp, giữ nguyên hội thoại."""
from __future__ import annotations
from typing import Callable
from .config import ModelSpec
from .quota import QuotaTracker
from .providers import QuotaError, ProviderError, chat as default_chat

class AllModelsExhausted(Exception):
    pass

class Router:
    def __init__(self, models: list[ModelSpec], tracker: QuotaTracker,
                 chat_fn: Callable = default_chat, on_switch: Callable[[str, str, str], None] | None = None,
                 block_seconds: float = 60):
        self.models, self.tracker, self.chat_fn = models, tracker, chat_fn
        self.on_switch = on_switch or (lambda a, b, why: None)
        self.block_seconds = block_seconds
        self.index = 0

    @property
    def current(self) -> ModelSpec:
        return self.models[self.index]

    def _switch(self, new: int, why: str) -> None:
        old = self.current.name; self.index = new
        self.on_switch(old, self.current.name, why)

    def send(self, messages: list[dict]) -> str:
        """Gửi toàn bộ `messages` (đủ ngữ cảnh) tới model khả dụng đầu tiên."""
        errors = []
        # Ưu tiên quay về model chính nếu nó khả dụng trở lại
        order = list(range(len(self.models)))
        for i in order:
            spec = self.models[i]
            if not self.tracker.available(spec):
                errors.append(f"{spec.name}: hết quota cục bộ"); continue
            if i != self.index:
                self._switch(i, errors[-1] if errors else "model ưu tiên khả dụng lại")
            try:
                text, tokens = self.chat_fn(spec, list(messages))
            except QuotaError as e:
                self.tracker.block(spec.name, self.block_seconds)
                errors.append(f"{spec.name}: {e}"); continue
            except ProviderError as e:
                errors.append(f"{spec.name}: {e}"); continue
            self.tracker.record(spec.name, tokens or 0)
            return text
        raise AllModelsExhausted("; ".join(errors))
