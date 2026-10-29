"""Đọc cấu hình TOML. API key chỉ lấy từ biến môi trường."""
from __future__ import annotations
import os, tomllib
from dataclasses import dataclass, field
from pathlib import Path

@dataclass
class ModelSpec:
    name: str
    provider: str            # openrouter | gemini | ollama | mock
    model: str
    api_key_env: str | None = None
    base_url: str | None = None
    rpm: int | None = None   # requests / minute
    rpd: int | None = None   # requests / day
    tpd: int | None = None   # tokens / day

    def api_key(self) -> str | None:
        return os.environ.get(self.api_key_env) if self.api_key_env else None

@dataclass
class Config:
    models: list[ModelSpec] = field(default_factory=list)
    state_file: Path = Path.home() / ".xoay" / "usage.json"
    system_prompt: str = "Bạn là trợ lý lập trình. Khi sửa file, trả lời bằng khối ```edit:<đường dẫn>\n<nội dung đầy đủ>\n```."

DEFAULT_PATHS = [Path("xoay.toml"), Path.home() / ".config" / "xoay" / "xoay.toml"]

def load_config(path: str | os.PathLike | None = None) -> Config:
    p = Path(path) if path else next((c for c in DEFAULT_PATHS if c.exists()), None)
    if p is None:
        raise FileNotFoundError("Không tìm thấy xoay.toml (xem xoay.example.toml)")
    data = tomllib.loads(Path(p).read_text(encoding="utf-8"))
    for m in data.get("models", []):
        for k in m:
            if k in ("api_key", "key", "token"):
                raise ValueError("Không được ghi API key vào file cấu hình; dùng api_key_env")
    cfg = Config(models=[ModelSpec(**m) for m in data.get("models", [])])
    g = data.get("general", {})
    if "state_file" in g:
        cfg.state_file = Path(os.path.expanduser(g["state_file"]))
    if "system_prompt" in g:
        cfg.system_prompt = g["system_prompt"]
    if not cfg.models:
        raise ValueError("Cấu hình cần ít nhất một [[models]]")
    return cfg
