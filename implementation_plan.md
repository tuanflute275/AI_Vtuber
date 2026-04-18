# AI VTuber Streamer — Kế Hoạch Triển Khai

Xây dựng ứng dụng AI VTuber Streamer hoàn chỉnh bằng Python, có khả năng tương tác thời gian thực qua microphone, đọc comment Facebook Live, và định tuyến âm thanh tới VTube Studio qua Virtual Audio Cable để lip-sync.

---

## ⚠️ Lưu Ý Quan Trọng Trước Khi Bắt Đầu

> [!IMPORTANT]
> **Facebook Comment Scraping**: Facebook chặt chẽ chống scraping. Selenium có thể bị ban tài khoản. Giải pháp được chọn: dùng **Selenium ẩn danh** (undetected-chromedriver) với cơ chế **giả lập comment** (mock mode) khi không có stream thật — an toàn hơn và dễ test.

> [!WARNING]
> **API Key trong `.env`**: API Key `AIzaSyCv0FaPuMUprcCs99FTrxsXOfUdFKBqRTQ` sẽ được lưu trong file `.env` (không commit lên git). File `.gitignore` sẽ được tạo sẵn.

> [!CAUTION]
> **Virtual Audio Cable**: Cần cài **VB-Audio Virtual Cable** (miễn phí) trước khi chạy ứng dụng. Không có VAC thì âm thanh sẽ phát ra loa thường thay vì route tới OBS.

---

## Kiến Trúc Hệ Thống

```
┌─────────────────────────────────────────────────────────┐
│                    MAIN LOOP (streamer.py)               │
│                                                         │
│  ┌──────────┐   ┌──────────────┐   ┌─────────────────┐  │
│  │   STT    │   │  FB Comment  │   │   Mock Comment  │  │
│  │ (Whisper)│   │   Scraper    │   │   Generator     │  │
│  └────┬─────┘   └──────┬───────┘   └────────┬────────┘  │
│       │                │                    │            │
│       └────────────────┴────────────────────┘            │
│                        │                                 │
│              ┌──────────▼──────────┐                     │
│              │   Priority Queue    │                     │
│              │  (Mic > Comments)   │                     │
│              └──────────┬──────────┘                     │
│                         │                                │
│              ┌──────────▼──────────┐                     │
│              │    brain.py         │                     │
│              │  (Gemini 1.5 Flash) │                     │
│              │  + System Prompt    │                     │
│              └──────────┬──────────┘                     │
│                         │                                │
│              ┌──────────▼──────────┐                     │
│              │    tts.py           │                     │
│              │   (Edge-TTS)        │                     │
│              └──────────┬──────────┘                     │
│                         │                                │
│       ┌─────────────────┴─────────────────┐             │
│       │                                   │             │
│  ┌────▼──────┐                  ┌──────────▼────────┐   │
│  │  Loa thường│                │  Virtual Cable Input│   │
│  │  (Monitor) │                │  → OBS → VTube Std │   │
│  └───────────┘                  └───────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

---

## Cấu Trúc File

```
vtuberAI/
├── .env                    # API Keys (không commit git)
├── .gitignore
├── requirements.txt        # Tất cả thư viện cần cài
├── config.py               # Cấu hình toàn hệ thống
├── brain.py                # Gemini AI processor
├── stt.py                  # Speech-to-Text (Faster-Whisper)
├── tts.py                  # Text-to-Speech (Edge-TTS + PyAudio routing)
├── facebook_reader.py      # FB Live comment scraper (Selenium + Mock)
├── streamer.py             # Main orchestrator loop
└── README.md               # Hướng dẫn cài đặt và sử dụng
```

---

## Chi Tiết Từng File

### `requirements.txt` [NEW]
Toàn bộ dependencies:
- `google-generativeai` — Gemini API
- `faster-whisper` — STT nhanh, chính xác
- `sounddevice` — Thu âm microphone
- `numpy` — Xử lý audio buffer
- `edge-tts` — TTS giọng tự nhiên (Microsoft)
- `pyaudio` — Stream audio tới Virtual Cable
- `python-dotenv` — Load .env
- `selenium` — Scrape FB comments
- `undetected-chromedriver` — Bypass bot detection
- `pydub` — Xử lý audio (convert format)
- `asyncio`, `threading`, `queue` — Built-in

---

### `config.py` [NEW]
Chứa toàn bộ cấu hình có thể chỉnh:
- Model AI, voice Edge-TTS, ngưỡng VAD
- Tên thiết bị Virtual Audio Cable
- FB Live URL, chế độ mock/real
- System prompt cho AI streamer

---

### `brain.py` [NEW]
- Khởi tạo Gemini `ChatSession` với system instruction hài hước
- Hàm `think(source, message)` trả về response text
- Phân biệt nguồn: `"mic"` (người dùng nói) vs `"comment"` (fan comment)
- Quản lý lịch sử hội thoại tự động

---

### `stt.py` [NEW]
- Load model `faster-whisper` (`base` hoặc `small`)
- Thread liên tục thu âm từ microphone qua `sounddevice`
- Voice Activity Detection (VAD) để không transcribe im lặng
- Khi phát hiện giọng nói, đẩy text vào `queue.Queue`

---

### `tts.py` [NEW]
- Dùng `edge-tts` với giọng Vietnamese (`vi-VN-HoaiMyNeural`) hoặc giọng EN
- Stream audio output tới **Virtual Audio Cable** qua `pyaudio`
- Nếu không có VAC, fallback về loa mặc định
- Hàm `speak(text)` đồng bộ (block cho đến khi phát xong)

---

### `facebook_reader.py` [NEW]
Có **2 chế độ**:
1. **Mock Mode** (mặc định): Tự sinh comment giả ngẫu nhiên để test — an toàn
2. **Selenium Mode**: Dùng `undetected-chromedriver` để scrape comment thật từ FB Live URL
   - Poll DOM mỗi 5 giây, lọc comment mới
   - Đẩy comment vào `queue.Queue`

---

### `streamer.py` [NEW]
Main loop điều phối:
- Khởi động tất cả thread (STT, FB reader)
- Lấy task từ queue theo priority (mic > comment)
- Gọi `brain.think()` → nhận response
- Gọi `tts.speak()` → phát âm
- Hiển thị console log đẹp với màu sắc
- Xử lý Ctrl+C graceful shutdown

---

## Thư Viện Cần Cài Đặt

```
pip install google-generativeai faster-whisper sounddevice numpy edge-tts pyaudio python-dotenv selenium undetected-chromedriver pydub
```

> [!NOTE]
> `pyaudio` trên Windows cần cài từ wheel file. Script sẽ hướng dẫn cụ thể trong README.

---

## Kế Hoạch Xác Minh

### Tự động
- Import test tất cả module không có lỗi
- Mock mode FB reader sinh comment thành công
- STT thread khởi động không lỗi

### Thủ công (User)
1. Cài Virtual Audio Cable từ VB-Audio
2. Cài VTube Studio và set microphone = CABLE Output
3. Chạy `python streamer.py` và thử nói vào mic
4. Kiểm tra VTube Studio có lip-sync không
