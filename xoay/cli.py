"""Giao diện dòng lệnh: REPL chat, /read, /apply, thanh trạng thái."""
from __future__ import annotations
import argparse, re, sys, tempfile, time
from pathlib import Path
from .config import load_config
from .quota import QuotaTracker
from .router import Router, AllModelsExhausted

C = {"dim": "\033[2m", "cy": "\033[36m", "ye": "\033[33m", "gr": "\033[32m", "re": "\033[31m", "b": "\033[1m", "x": "\033[0m"}
if not sys.stdout.isatty():
    C = {k: "" for k in C}

EDIT_RE = re.compile(r"```edit:([^\n]+)\n(.*?)```", re.S)

def status_line(router: Router) -> str:
    m = router.current
    return f"{C['dim']}─ model: {C['x']}{C['cy']}{C['b']}{m.name}{C['x']}{C['dim']} ({m.provider}:{m.model}) │ còn lại: {router.tracker.remaining(m)}{C['x']}"

def on_switch(old, new, why):
    print(f"{C['ye']}⟳ Đổi model: {old} → {new}  ({why[:90]}){C['x']}")

HELP = """Lệnh:
  /read <file>   đọc file vào ngữ cảnh
  /apply         áp dụng các khối ```edit:<file>``` trong câu trả lời gần nhất (có hỏi xác nhận)
  /models        xem danh sách model và quota
  /clear         xoá ngữ cảnh
  /exit          thoát"""

def apply_edits(text: str, ask=input) -> int:
    n = 0
    for path, body in EDIT_RE.findall(text):
        path = path.strip()
        if ask(f"Ghi {len(body)} ký tự vào {path}? [y/N] ").strip().lower() == "y":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            Path(path).write_text(body, encoding="utf-8"); n += 1
            print(f"{C['gr']}✓ đã ghi {path}{C['x']}")
    return n

def repl(router: Router, system_prompt: str) -> None:
    messages = [{"role": "system", "content": system_prompt}]
    last = ""
    print(f"{C['b']}xoay{C['x']} – gõ /help để xem lệnh")
    while True:
        print(status_line(router))
        try: line = input(f"{C['gr']}› {C['x']}").strip()
        except (EOFError, KeyboardInterrupt): print(); return
        if not line: continue
        if line in ("/exit", "/quit"): return
        if line == "/help": print(HELP); continue
        if line == "/clear": messages = messages[:1]; print("Đã xoá ngữ cảnh."); continue
        if line == "/models":
            for i, m in enumerate(router.models):
                mark = "●" if i == router.index else " "
                print(f" {mark} {m.name:18} {router.tracker.remaining(m)}")
            continue
        if line.startswith("/read "):
            p = Path(line[6:].strip())
            try: content = p.read_text(encoding="utf-8")
            except OSError as e: print(f"{C['re']}{e}{C['x']}"); continue
            messages.append({"role": "user", "content": f"Nội dung file {p}:\n```\n{content}\n```"})
            print(f"Đã thêm {p} ({len(content)} ký tự) vào ngữ cảnh."); continue
        if line == "/apply":
            if not apply_edits(last): print("Không có thay đổi nào được áp dụng.")
            continue
        messages.append({"role": "user", "content": line})
        try:
            last = router.send(messages)
        except AllModelsExhausted as e:
            messages.pop(); print(f"{C['re']}Tất cả model đều hết quota/lỗi: {e}{C['x']}"); continue
        messages.append({"role": "assistant", "content": last})
        print(last)

def run_demo(fast: bool) -> int:
    from .mock import demo_config, MockBackend, DEMO_PROMPTS
    tmp = Path(tempfile.mkdtemp()) / "usage.json"
    cfg = demo_config(tmp)
    router = Router(cfg.models, QuotaTracker(tmp), chat_fn=MockBackend(delay=0 if fast else 1.0), on_switch=on_switch)
    print(f"{C['b']}xoay --demo{C['x']}: 4 model giả lập, model chính hết quota cục bộ sau 2 request, model free bị server trả 429\n")
    messages = [{"role": "system", "content": cfg.system_prompt}]
    for p in DEMO_PROMPTS:
        print(status_line(router))
        print(f"{C['gr']}› {C['x']}{p}")
        if not fast: time.sleep(2.2)
        messages.append({"role": "user", "content": p})
        reply = router.send(messages)
        messages.append({"role": "assistant", "content": reply})
        print(reply + "\n")
    print(status_line(router))
    print(f"{C['gr']}✓ Demo xong: hội thoại {len(messages)} tin nhắn được giữ nguyên qua mọi lần đổi model.{C['x']}")
    return 0

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="xoay", description="Trợ lý code trên terminal, tự đổi model khi hết quota")
    ap.add_argument("-c", "--config", help="đường dẫn xoay.toml")
    ap.add_argument("--demo", "--mock", action="store_true", help="chạy demo giả lập, không cần API key")
    ap.add_argument("--fast", action="store_true", help="demo không có độ trễ")
    a = ap.parse_args(argv)
    if a.demo: return run_demo(a.fast)
    try: cfg = load_config(a.config)
    except (FileNotFoundError, ValueError) as e: print(e, file=sys.stderr); return 2
    repl(Router(cfg.models, QuotaTracker(cfg.state_file), on_switch=on_switch), cfg.system_prompt)
    return 0
