# xoay 🔄

**xoay** là trợ lý lập trình chạy trên terminal, viết bằng Python thuần (không phụ thuộc thư viện ngoài). Khi model đang dùng bị **hết quota / rate limit (HTTP 429)**, xoay tự động **xoay** sang model miễn phí kế tiếp trong danh sách — và **giữ nguyên toàn bộ ngữ cảnh hội thoại**, bạn cứ thế code tiếp.

## Tính năng

- Một model chính + danh sách model dự phòng theo thứ tự: OpenRouter (model `:free`), Gemini (Google AI Studio, gói miễn phí), Ollama chạy cục bộ.
- Bắt lỗi 429 / `quota` / `RESOURCE_EXHAUSTED` / rate limit và chuyển model ngay, không mất lịch sử chat.
- Thanh trạng thái hiển thị model hiện tại và **quota ước tính còn lại** (request/phút, request/ngày, token/ngày), lưu cục bộ tại `~/.xoay/usage.json`.
- Tự quay lại model chính khi nó hết bị chặn.
- Một file cấu hình TOML duy nhất; API key **chỉ đọc từ biến môi trường** (file cấu hình chứa key sẽ bị từ chối).
- Công cụ code: REPL chat, `/read` đọc file vào ngữ cảnh, `/apply` ghi các thay đổi file mà model đề xuất (luôn hỏi xác nhận).
- Chế độ `--demo` giả lập hết quota, không cần API key.

## Cài đặt

Yêu cầu Python ≥ 3.11.

```bash
git clone https://github.com/vietphan98/xoay.git
cd xoay
pip install -e .        # hoặc chạy trực tiếp: python3 -m xoay
```

## Cấu hình

```bash
cp xoay.example.toml xoay.toml
```

xoay tìm `./xoay.toml`, sau đó `~/.config/xoay/xoay.toml` (hoặc chỉ định bằng `-c`). Mỗi khối `[[models]]` là một model; thứ tự trong file chính là thứ tự ưu tiên:

```toml
[[models]]
name = "gemini-flash"
provider = "gemini"            # openrouter | gemini | ollama
model = "gemini-2.0-flash"
api_key_env = "GEMINI_API_KEY" # tên biến môi trường, KHÔNG phải key
rpm = 15                       # giới hạn request/phút (tuỳ chọn)
rpd = 1500                     # giới hạn request/ngày (tuỳ chọn)
tpd = 1000000                  # giới hạn token/ngày (tuỳ chọn)
```

Khi số liệu cục bộ chạm giới hạn, xoay bỏ qua model đó trước cả khi gọi API.

## Biến môi trường

| Biến | Dùng cho |
|---|---|
| `OPENROUTER_API_KEY` | Các model OpenRouter (lấy tại openrouter.ai/keys) |
| `GEMINI_API_KEY` | Gemini qua Google AI Studio (aistudio.google.com) |
| *(không cần)* | Ollama cục bộ — chỉ cần `ollama serve` và đã `ollama pull` model |

```bash
export OPENROUTER_API_KEY=sk-or-...
export GEMINI_API_KEY=AIza...
```

## Sử dụng

```bash
xoay                 # mở REPL
xoay -c duong/dan/xoay.toml
```

Các lệnh trong REPL:

| Lệnh | Ý nghĩa |
|---|---|
| `/read <file>` | Đọc file vào ngữ cảnh |
| `/apply` | Áp dụng các khối ```` ```edit:<file> ```` trong câu trả lời gần nhất, hỏi `y/N` cho từng file |
| `/models` | Xem danh sách model và quota còn lại |
| `/clear` | Xoá ngữ cảnh |
| `/exit` | Thoát |

## Demo (20–30 giây, không cần key)

```bash
python3 -m xoay --demo
```

Kịch bản: 4 model giả lập, 7 câu hỏi liên tiếp.

1. `chinh-pro` trả lời 2 câu → hết quota cục bộ → **⟳ đổi sang `openrouter-free`**.
2. `openrouter-free` trả lời 2 câu → server giả lập trả **HTTP 429** → **⟳ đổi sang `gemini-flash`**.
3. `gemini-flash` cũng dính 429 → **⟳ đổi sang `ollama-local`**.
4. Kết thúc: hội thoại 15 tin nhắn được giữ nguyên qua mọi lần đổi model.

Thêm `--fast` để chạy không có độ trễ.

## Kiểm thử

```bash
pip install pytest
python3 -m pytest -q
```

## Gợi ý hook cho Reel

> „Hết quota giữa lúc đang code? Tool này tự đổi sang model miễn phí khác — không mất một dòng ngữ cảnh nào." 🔄

## Tác giả

**Việt Phan**

## Giấy phép

MIT — xem file [LICENSE](LICENSE).
