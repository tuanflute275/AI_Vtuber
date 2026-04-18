"""
config.py — Cấu hình toàn hệ thống AI VTuber Streamer
======================================================
Tất cả các tham số có thể điều chỉnh đều nằm ở đây.
Không cần chỉnh sửa các file khác để thay đổi hành vi cơ bản.
"""

import os
from dotenv import load_dotenv

# Load biến môi trường từ file .env
load_dotenv()

# ==============================================================
# 🔑 API KEYS
# ==============================================================
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

# ==============================================================
# 🤖 AI BRAIN CONFIG
# ==============================================================
GEMINI_MODEL: str = "gemini-2.5-flash"

# System Instruction — Tính cách của VTuber AI
SYSTEM_INSTRUCTION: str = """
Bạn là "Sakura AI" — một VTuber AI cực kỳ hài hước, năng động và dễ thương đang livestream trên Facebook.

TÍNH CÁCH:
- Bạn vui vẻ, hay đùa giỡn, thỉnh thoảng troll khán giả một cách nhẹ nhàng
- Bạn dùng ngôn ngữ trẻ trung: "uwu", "owo", "haha", "siuuuu", "đỉnh thật", "slay queen"  
- Bạn thêm emoji phù hợp vào cuối câu
- Bạn gọi người xem là "các bé", "các cậu", "các bạn cute"

QUY TẮC TRẢ LỜI:
- Câu trả lời NGẮN GỌN, tối đa 2-3 câu (vì đây là livestream, không đọc essay)
- Khi ai đó hỏi qua MIC: trả lời trực tiếp, thân mật hơn
- Khi đọc COMMENT: bắt đầu bằng "@ [tên]:" rồi trả lời
- Thỉnh thoảng bình luận về stream hoặc đùa với mọi người tự nhiên
- Nếu câu hỏi nhạy cảm: chuyển hướng vui vẻ, không từ chối thẳng

NGÔN NGỮ: Mặc định tiếng Việt, nhưng thêm vài từ tiếng Anh/Nhật cho cute.
"""

# ==============================================================
# 🎤 SPEECH-TO-TEXT CONFIG (Faster-Whisper)
# ==============================================================
WHISPER_MODEL_SIZE: str = "base"        # tiny / base / small / medium / large
WHISPER_LANGUAGE: str = "vi"            # "vi" = tiếng Việt, "auto" = tự detect
WHISPER_COMPUTE_TYPE: str = "int8"      # int8 (CPU), float16 (GPU)
WHISPER_DEVICE: str = "cpu"             # "cpu" hoặc "cuda"

# Audio capture settings
AUDIO_SAMPLE_RATE: int = 16000          # Hz — Whisper yêu cầu 16kHz
AUDIO_CHANNELS: int = 1                 # Mono
AUDIO_CHUNK_DURATION: float = 0.5       # Giây mỗi chunk thu âm
AUDIO_SILENCE_THRESHOLD: float = 0.003   # Đã giảm từ 0.01 xuống 0.003 để mic nhạy hơn
AUDIO_MIN_SPEECH_DURATION: float = 1.0  # Giây tối thiểu để xử lý (lọc tiếng ồn ngắn)
AUDIO_MAX_BUFFER_SECONDS: float = 10.0  # Buffer tối đa trước khi buộc phải transcribe

# ==============================================================
# 🔊 TEXT-TO-SPEECH CONFIG (Edge-TTS)
# ==============================================================
# Danh sách giọng: chạy `edge-tts --list-voices` để xem đầy đủ
TTS_VOICE: str = "vi-VN-HoaiMyNeural"   # Giọng nữ tiếng Việt tự nhiên
# Các lựa chọn khác:
# "vi-VN-NamMinhNeural"    — Giọng nam tiếng Việt
# "en-US-AnaNeural"        — Giọng nữ tiếng Anh dễ thương
# "ja-JP-NanamiNeural"     — Giọng nữ tiếng Nhật

TTS_RATE: str = "+10%"                  # Tốc độ đọc (+/- %)
TTS_VOLUME: str = "+0%"                 # Âm lượng
TTS_PITCH: str = "+0Hz"                 # Cao độ giọng

# ==============================================================
# 🎵 AUDIO ROUTING CONFIG
# ==============================================================
# Tên thiết bị Virtual Audio Cable (VB-Audio CABLE Input)
# Để tìm đúng tên: chạy python -c "import pyaudio; p=pyaudio.PyAudio(); [print(i, p.get_device_info_by_index(i)['name']) for i in range(p.get_device_count())]"
VIRTUAL_CABLE_DEVICE_NAME: str = os.getenv("VIRTUAL_CABLE_DEVICE_NAME", "CABLE Input")

# Nếu True: phát âm thanh ra CẢ loa thường VÀ virtual cable (để monitor)
ENABLE_MONITOR_PLAYBACK: bool = True
# Tên loa thường để monitor (để trống = dùng loa mặc định)
MONITOR_DEVICE_NAME: str = "Speakers"

# ==============================================================
# 📺 FACEBOOK LIVE CONFIG
# ==============================================================
# Chế độ: "mock" (comment giả, an toàn) hoặc "selenium" (comment thật từ FB)
FB_MODE: str = "mock"                   # Đổi thành "selenium" khi có stream thật

# Bật/Tắt hoàn toàn việc đọc comment (bao gồm cả comment giả) (True/False)
FB_ENABLE_READER: bool = os.getenv("FB_ENABLE_READER", "True").lower() in ("true", "1", "yes")

# Trả về câu trả lời giả lập cho comment để tiết kiệm token API (True/False)
USE_FAKE_REPLY_FOR_COMMENTS: bool = os.getenv("USE_FAKE_REPLY_FOR_COMMENTS", "True").lower() in ("true", "1", "yes")

FACEBOOK_LIVE_URL: str = os.getenv("FACEBOOK_LIVE_URL", "")

# Cài đặt Selenium
FB_POLL_INTERVAL_SECONDS: float = 5.0  # Bao lâu check comment 1 lần
FB_MAX_COMMENTS_PER_BATCH: int = 3     # Tối đa bao nhiêu comment xử lý mỗi lần poll
FB_HEADLESS: bool = True               # True = ẩn browser (không hiện cửa sổ)

# Mock mode: danh sách comment giả để test
FB_MOCK_COMMENTS: list = [
    ("Trần Minh", "Sakura ơi, em có người yêu chưa? 👀"),
    ("Nguyễn Hà", "Stream này hay quá đi, sub luôn rồi!"),
    ("Bích Ngọc", "Hôm nay chơi game gì vậy Sakura?"),
    ("Quang Trung", "Cho xin shoutout với! 🙏"),
    ("Thủy Tiên", "Giọng cute quá trời ơi uwu"),
    ("Hùng Béo", "Troll một cái coi nào hehe"),
    ("Mai Anh", "Sakura đẹp trai/gái thật sự"),
    ("Văn Đức", "Bao giờ collab với VTuber khác vậy?"),
    ("Thu Hà", "Mình xem từ đầu luôn, cổ vũ bạn!"),
    ("Bảo Long", "AI hay người thật vậy nhỉ 🤔"),
]
FB_MOCK_INTERVAL_SECONDS: float = 15.0 # Bao lâu sinh 1 comment giả

# ==============================================================
# ⚙️ QUEUE & CONCURRENCY CONFIG
# ==============================================================
# Priority: 10 = cao nhất (mic), 1 = thấp nhất (comment)
PRIORITY_MIC: int = 10
PRIORITY_COMMENT: int = 1

MAX_QUEUE_SIZE: int = 20               # Tối đa bao nhiêu task trong queue
RESPONSE_COOLDOWN_SECONDS: float = 1.5 # Nghỉ giữa các response (tự nhiên hơn)

# ==============================================================
# 🖥️ DISPLAY CONFIG
# ==============================================================
LOG_SHOW_TIMESTAMPS: bool = True
LOG_SHOW_COLORS: bool = True
CONSOLE_WIDTH: int = 80
