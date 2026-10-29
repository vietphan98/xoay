import json
import pytest
from xoay.config import ModelSpec, load_config
from xoay.quota import QuotaTracker
from xoay.router import Router, AllModelsExhausted
from xoay.providers import QuotaError, ProviderError, is_quota_message
from xoay.cli import apply_edits

def models():
    return [ModelSpec("a", "mock", "a", rpd=5), ModelSpec("b", "mock", "b"), ModelSpec("c", "mock", "c")]

class Fake:
    def __init__(self, fail=()):
        self.fail, self.seen = set(fail), []
    def __call__(self, spec, msgs):
        self.seen.append((spec.name, msgs))
        if spec.name in self.fail: raise QuotaError("429")
        return f"ok-{spec.name}", 10

def test_primary_used_when_ok():
    r = Router(models(), QuotaTracker(None), chat_fn=Fake())
    assert r.send([{"role": "user", "content": "hi"}]) == "ok-a"

def test_switch_on_429_keeps_context():
    f = Fake(fail={"a"}); switches = []
    r = Router(models(), QuotaTracker(None), chat_fn=f, on_switch=lambda *x: switches.append(x))
    msgs = [{"role": "user", "content": "1"}, {"role": "assistant", "content": "x"}, {"role": "user", "content": "2"}]
    assert r.send(msgs) == "ok-b"
    assert r.current.name == "b" and switches[0][:2] == ("a", "b")
    assert f.seen[-1][1] == msgs  # toàn bộ ngữ cảnh được chuyển sang

def test_skips_blocked_model_without_calling():
    f = Fake(fail={"a"}); r = Router(models(), QuotaTracker(None), chat_fn=f)
    r.send([{"role": "user", "content": "1"}]); f.seen.clear()
    r.send([{"role": "user", "content": "2"}])
    assert [s for s, _ in f.seen] == ["b"]

def test_local_limit_triggers_switch():
    t = QuotaTracker(None); ms = models()
    r = Router(ms, t, chat_fn=Fake())
    for _ in range(5): assert r.send([{"role": "user", "content": "x"}]) == "ok-a"
    assert r.send([{"role": "user", "content": "x"}]) == "ok-b"
    assert t.remaining(ms[0]).startswith("0/5")

def test_all_exhausted():
    r = Router(models(), QuotaTracker(None), chat_fn=Fake(fail={"a", "b", "c"}))
    with pytest.raises(AllModelsExhausted): r.send([{"role": "user", "content": "x"}])

def test_provider_error_falls_through():
    def fn(spec, m):
        if spec.name == "a": raise ProviderError("down")
        return "ok", 1
    assert Router(models(), QuotaTracker(None), chat_fn=fn).send([{"role": "user", "content": "x"}]) == "ok"

def test_returns_to_primary_after_block_expires():
    now = [1000.0]; t = QuotaTracker(None, clock=lambda: now[0])
    f = Fake(fail={"a"}); r = Router(models(), t, chat_fn=f, block_seconds=30)
    r.send([{"role": "user", "content": "x"}]); assert r.current.name == "b"
    f.fail.clear(); now[0] += 31
    assert r.send([{"role": "user", "content": "x"}]) == "ok-a"

def test_quota_persisted(tmp_path):
    p = tmp_path / "u.json"; t = QuotaTracker(p); t.record("a", 42)
    assert QuotaTracker(p).data["a"]["tok"] == 42

def test_rpm_limit():
    now = [0.0]; t = QuotaTracker(None, clock=lambda: now[0]); m = ModelSpec("a", "mock", "a", rpm=2)
    t.record("a", 1); t.record("a", 1); assert not t.available(m)
    now[0] += 61; assert t.available(m)

def test_quota_message_detection():
    assert is_quota_message("RESOURCE_EXHAUSTED: quota exceeded")
    assert not is_quota_message("invalid model")

def test_config_rejects_inline_key(tmp_path):
    p = tmp_path / "x.toml"
    p.write_text('[[models]]\nname="a"\nprovider="gemini"\nmodel="m"\napi_key="secret"\n')
    with pytest.raises(ValueError): load_config(p)

def test_example_config_loads():
    from pathlib import Path
    cfg = load_config(Path(__file__).parent.parent / "xoay.example.toml")
    assert [m.provider for m in cfg.models][-1] == "ollama"

def test_apply_edits(tmp_path):
    f = tmp_path / "a.py"
    assert apply_edits(f"```edit:{f}\nprint(1)\n```", ask=lambda _: "y") == 1
    assert f.read_text() == "print(1)\n"
    assert apply_edits(f"```edit:{f}\nX\n```", ask=lambda _: "n") == 0
