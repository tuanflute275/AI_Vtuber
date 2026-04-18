# 🌸 AI VTuber Streamer — Sakura AI

Ứng dụng AI VTuber Streamer hoàn chỉnh bằng Python, tích hợp Google Gemini, Faster-Whisper STT, Edge-TTS, và định tuyến âm thanh tới VTube Studio để lip-sync.

## 📐 Kiến Trúc Hệ Thống

```
Microphone ──→ STT (Faster-Whisper) ──┐
                                       ├──→ Priority Queue ──→ AI Brain (Gemini) ──→ TTS (Edge-TTS)
FB Live Comments ──→ FB Reader ────────┘                                                    │
                                                                                            ▼
                                                                          Virtual Audio Cable (CABLE Input)
                                                                                            │
                                                                               OBS ←── VTube Studio (Lip-sync)
```

## 📁 Cấu Trúc File

```
vtuberAI/
├── .env                 # API Keys (BẢO MẬT - không commit)
├── .env.example         # Mẫu file .env
├── .gitignore
├── requirements.txt     # Danh sách thư viện
├── config.py            # ⚙️  Toàn bộ cấu hình
├── brain.py             # 🧠 AI Brain (Gemini 1.5 Flash)
├── stt.py               # 🎤 Speech-to-Text (Faster-Whisper)
├── tts.py               # 🔊 Text-to-Speech (Edge-TTS)
├── facebook_reader.py   # 📺 FB Comment Reader
├── streamer.py          # 🚀 Main Orchestrator (Entry Point)
├── setup_check.py       # 🔍 Kiểm tra môi trường
└── README.md
```

## 🛠️ Cài Đặt

### Bước 1: Phần Mềm Cần Thiết

Cài các phần mềm này trước:

| Phần mềm | Link | Ghi chú |
|----------|------|---------|
| Python 3.9+ | https://python.org | Tick "Add to PATH" khi cài |
| VB-Audio Virtual Cable | https://vb-audio.com/Cable/ | Miễn phí — bắt buộc cho lip-sync |
| FFmpeg | https://ffmpeg.org/download.html | Thêm vào PATH sau khi cài |
| VTube Studio (Steam) | https://store.steampowered.com/app/1325860/ | Cho nhân vật 2D/3D |
| OBS Studio | https://obsproject.com/ | Để stream |

### Bước 2: Cài Thư Viện Python

```bash
# Tạo virtual environment (khuyên dùng)
python -m venv venv
venv\Scripts\activate      # Windows

# Cài thư viện cơ bản
pip install -r requirements.txt

# PyAudio trên Windows (nếu lỗi):
pip install pipwin
pipwin install pyaudio
```

### Bước 3: Cấu Hình

```bash
# Copy file env mẫu
copy .env.example .env

# Mở .env và điền thông tin
# GEMINI_API_KEY đã được điền sẵn
```

File `.env` đã có sẵn API key. Nếu cần đổi giọng nói hoặc cấu hình khác, chỉnh trong `config.py`.

## 🔐 Các Biến Môi Trường (.env)

Hệ thống sử dụng file `.env` để lưu trữ các thông tin nhạy cảm và cấu hình nhanh. Dưới đây là ý nghĩa của các biến:

| Biến | Ý nghĩa | Giá trị gợi ý |
|------|---------|---------------|
| `GEMINI_API_KEY` | Key để gọi AI từ Google Gemini. | (Đã có sẵn trong file) |
| `FACEBOOK_LIVE_URL` | Đường dẫn livestream Facebook để đọc comment thật. | Để trống nếu dùng Mock Mode. |
| `FB_ENABLE_READER` | **Bật/Tắt hoàn toàn** việc đọc comment (cả thật và giả). | `True` (Bật), `False` (Tắt). |
| `USE_FAKE_REPLY_FOR_COMMENTS` | Dùng câu trả lời mẫu cho comment để **tiết kiệm token API**. | `True` (Dùng câu mẫu), `False` (Dùng AI thật). |
| `VIRTUAL_CABLE_DEVICE_NAME` | Tên thiết bị cáp ảo để truyền âm thanh tới VTube Studio. | Mặc định là `CABLE Input`. |

### Bước 4: Kiểm Tra Môi Trường

```bash
python setup_check.py
```

Script này sẽ kiểm tra tất cả dependencies, API key, và audio devices.

## 🎮 Cách Sử Dụng

### Khởi Động

```bash
python streamer.py
```

### Cài Đặt VTube Studio Cho Lip-Sync

1. Mở **VTube Studio**
2. Vào **Settings → Microphone**
3. Chọn microphone = **"CABLE Output (VB-Audio Virtual Cable)"**
4. Bật **"Use Microphone"**
5. Chọn **Lip Sync Type = "Advanced Lip Sync"**
6. Calibrate các âm A, I, U, E, O

### Cài Đặt OBS

1. Thêm source **"Audio Input Capture"**
2. Chọn device = **"CABLE Output (VB-Audio Virtual Cable)"**
3. Right-click source → **"Advanced Audio Properties"**
4. Set **Monitor** = **"Monitor and Output"** để nghe được âm thanh

## ⚙️ Tùy Chỉnh

### Đổi Giọng TTS

Trong `config.py`:
```python
TTS_VOICE = "vi-VN-HoaiMyNeural"   # Nữ tiếng Việt (mặc định)
TTS_VOICE = "vi-VN-NamMinhNeural"  # Nam tiếng Việt
TTS_VOICE = "en-US-AnaNeural"      # Nữ tiếng Anh dễ thương
```

Xem danh sách đầy đủ: `edge-tts --list-voices`

### Đổi Tính Cách AI

Trong `config.py`, sửa biến `SYSTEM_INSTRUCTION` để đổi:
- Tên nhân vật
- Tính cách
- Ngôn ngữ phản hồi
- Độ dài câu trả lời

### Bật Comment Facebook Thật

1. Trong `config.py`:
```python
FB_MODE = "selenium"  # Đổi từ "mock" sang "selenium"
```

2. Trong `.env`:
```
FACEBOOK_LIVE_URL=https://www.facebook.com/your_live_url
```

> ⚠️ **Cảnh báo**: Dùng tài khoản phụ! Facebook có thể ban tài khoản nếu phát hiện automation.

### Whisper Model Size

| Model | RAM | Tốc độ | Độ chính xác |
|-------|-----|--------|--------------|
| tiny  | 1GB | ⚡⚡⚡⚡  | ⭐⭐ |
| base  | 1GB | ⚡⚡⚡   | ⭐⭐⭐ (khuyên dùng) |
| small | 2GB | ⚡⚡    | ⭐⭐⭐⭐ |
| medium| 5GB | ⚡     | ⭐⭐⭐⭐⭐ |

Thay đổi trong `config.py`: `WHISPER_MODEL_SIZE = "small"`

## 🔧 Xử Lý Lỗi Thường Gặp

### "No module named 'pyaudio'"
```bash
pip install pipwin
pipwin install pyaudio
```

### "VIRTUAL_CABLE không tìm thấy"
- Cài VB-Audio Virtual Cable và restart máy
- Kiểm tra tên device: chạy `python setup_check.py`

### Whisper không nghe thấy giọng
- Kiểm tra microphone đang hoạt động
- Giảm `AUDIO_SILENCE_THRESHOLD` trong `config.py` (thử `0.005`)

### Edge-TTS lỗi kết nối
- Kiểm tra internet (Edge-TTS cần kết nối Microsoft servers)
- Thử đổi sang giọng khác

### Gemini trả về lỗi 429
- Vượt quá rate limit miễn phí
- Đợi vài giây rồi retry (tự động)
- Hoặc nâng cấp API quota tại https://makersuite.google.com

## 📊 Cấu Trúc Queue

```
Priority Queue (min-heap):
  (-10, timestamp, "mic", text, "")        ← Mic input (ưu tiên cao nhất)
  (-1,  timestamp, "comment", text, name)  ← FB Comment (ưu tiên thấp hơn)
```

Mic luôn được xử lý trước comment khi có cả hai trong queue.

## 🔗 Tài Nguyên Tham Khảo

- [Google Gemini API Docs](https://ai.google.dev/api/python/google/generativeai)
- [Faster-Whisper GitHub](https://github.com/SYSTRAN/faster-whisper)
- [Edge-TTS GitHub](https://github.com/rany2/edge-tts)
- [VB-Audio Virtual Cable](https://vb-audio.com/Cable/)
- [VTube Studio Wiki](https://github.com/DenchiSoft/VTubeStudio)

## 📝 License

Dự án cá nhân, sử dụng tự do. Không dùng cho mục đích thương mại.
