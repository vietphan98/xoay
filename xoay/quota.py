"""Theo dõi số request/token của từng model, lưu cục bộ dạng JSON."""
from __future__ import annotations
import json, time
from pathlib import Path
from .config import ModelSpec

class QuotaTracker:
    def __init__(self, path: Path | None, clock=time.time):
        self.path, self.clock = path, clock
        self.data: dict = {}
        if path and Path(path).exists():
            try: self.data = json.loads(Path(path).read_text())
            except Exception: self.data = {}

    def _entry(self, name: str) -> dict:
        day = time.strftime("%Y-%m-%d", time.localtime(self.clock()))
        e = self.data.setdefault(name, {"day": day, "req": 0, "tok": 0, "minute": [], "blocked_until": 0})
        if e["day"] != day:
            e.update(day=day, req=0, tok=0, blocked_until=0)
        now = self.clock()
        e["minute"] = [t for t in e["minute"] if now - t < 60]
        return e

    def record(self, name: str, tokens: int) -> None:
        e = self._entry(name)
        e["req"] += 1; e["tok"] += tokens; e["minute"].append(self.clock())
        self.save()

    def block(self, name: str, seconds: float = 60) -> None:
        self._entry(name)["blocked_until"] = self.clock() + seconds
        self.save()

    def available(self, m: ModelSpec) -> bool:
        e = self._entry(m.name)
        if e["blocked_until"] > self.clock(): return False
        if m.rpm and len(e["minute"]) >= m.rpm: return False
        if m.rpd and e["req"] >= m.rpd: return False
        if m.tpd and e["tok"] >= m.tpd: return False
        return True

    def remaining(self, m: ModelSpec) -> str:
        e = self._entry(m.name); parts = []
        if m.rpd: parts.append(f"{max(m.rpd - e['req'], 0)}/{m.rpd} req/ngày")
        if m.rpm: parts.append(f"{max(m.rpm - len(e['minute']), 0)}/{m.rpm} req/phút")
        if m.tpd: parts.append(f"{max(m.tpd - e['tok'], 0)}/{m.tpd} token/ngày")
        return ", ".join(parts) or "không giới hạn"

    def save(self) -> None:
        if not self.path: return
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        Path(self.path).write_text(json.dumps(self.data, indent=1))
