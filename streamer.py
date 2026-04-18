"""
streamer.py — Main Orchestrator (Entry Point)
=============================================
Vòng lặp chính điều phối toàn bộ hệ thống AI VTuber Streamer.

Luồng xử lý:
1. Khởi động tất cả module (STT, TTS, FB Reader, AI Brain)
2. Main loop: lấy task từ priority queue
3. Gọi AI brain để xử lý → nhận response
4. Phát response qua TTS
5. Xử lý Ctrl+C để shutdown graceful

Priority Queue format:
  (-priority, timestamp, source, text, author)
  - priority âm vì PriorityQueue ưu tiên giá trị nhỏ nhất
  - Mic (priority=10) → -10 → ưu tiên cao hơn Comment (priority=1) → -1
"""

import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

import queue
import signal
import sys
import time
import logging
import threading
from datetime import datetime
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich import print as rprint
from rich.live import Live
from rich.table import Table
from rich.align import Align
from colorama import Fore, Style, init as colorama_init

import config
from brain import AIBrain
from stt import SpeechToText
from tts import TextToSpeech
from facebook_reader import create_facebook_reader

# ==============================================================
# SETUP LOGGING
# ==============================================================

def setup_logging():
    """Cấu hình logging với màu sắc đẹp."""
    colorama_init(autoreset=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s │ %(levelname)-8s │ %(name)-20s │ %(message)s",
        datefmt="%H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("vtuber_stream.log", encoding="utf-8"),
        ],
    )

    # Tắt bớt log ồn ào từ thư viện
    logging.getLogger("selenium").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

setup_logging()
logger = logging.getLogger(__name__)
console = Console(width=config.CONSOLE_WIDTH)


# ==============================================================
# DISPLAY HELPERS
# ==============================================================

def print_banner():
    """In banner khởi động đẹp."""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║    🌸  SAKURA AI — VTuber Streamer System  🌸                ║
║                                                              ║
║    AI Brain   : Google Gemini 1.5 Flash                     ║
║    STT Engine : Faster-Whisper                               ║
║    TTS Engine : Edge-TTS (Microsoft Neural)                  ║
║    Audio Route: VB-Audio Virtual Cable → OBS → VTube Studio ║
║    FB Comments: {mode:<10} Mode                              ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """.format(mode=config.FB_MODE.upper())
    print(Fore.MAGENTA + banner + Style.RESET_ALL)


def log_interaction(source: str, author: str, text: str, response: str):
    """In log tương tác đẹp ra console."""
    timestamp = datetime.now().strftime("%H:%M:%S")

    if source == "mic":
        icon = "🎤"
        color = Fore.CYAN
        source_label = "MIC"
    else:
        icon = "💬"
        color = Fore.YELLOW
        source_label = f"FB: {author}" if author else "FB"

    print("\n" + "─" * config.CONSOLE_WIDTH)
    print(f"{Fore.WHITE}[{timestamp}]{Style.RESET_ALL} {icon} {color}{source_label}{Style.RESET_ALL}")
    print(f"  📥 Input  : {Fore.WHITE}{text}{Style.RESET_ALL}")
    print(f"  📤 Output : {Fore.GREEN}{response}{Style.RESET_ALL}")
    print("─" * config.CONSOLE_WIDTH)


# ==============================================================
# MAIN STREAMER CLASS
# ==============================================================

class VTuberStreamer:
    """
    Orchestrator chính: kết nối tất cả module lại với nhau.
    """

    def __init__(self):
        self.is_running = False
        self.task_queue = queue.PriorityQueue(maxsize=config.MAX_QUEUE_SIZE)
        self.stats = {
            "total_interactions": 0,
            "mic_interactions": 0,
            "comment_interactions": 0,
            "start_time": None,
        }

        # Modules sẽ được init trong start()
        self.brain: Optional[AIBrain] = None
        self.stt: Optional[SpeechToText] = None
        self.tts: Optional[TextToSpeech] = None
        self.fb_reader = None

    def _init_modules(self) -> bool:
        """Khởi tạo tất cả module. Trả về True nếu thành công."""
        try:
            # 1. AI Brain
            logger.info("🧠 Đang khởi tạo AI Brain...")
            self.brain = AIBrain()

            # 2. TTS (trước STT vì cần kiểm tra audio devices)
            logger.info("🔊 Đang khởi tạo TTS Engine...")
            self.tts = TextToSpeech()

            # 3. STT
            logger.info("🎤 Đang khởi tạo STT Engine...")
            self.stt = SpeechToText(self.task_queue)

            # 4. FB Reader
            logger.info("📺 Đang khởi tạo Facebook Reader...")
            self.fb_reader = create_facebook_reader(self.task_queue)

            return True

        except Exception as e:
            logger.error(f"❌ Lỗi khởi tạo module: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _startup_greeting(self) -> None:
        """Phát lời chào mở đầu stream."""
        greetings = [
            "Ôi ôi ôi! Sakura đã online rồi đây các bé ơi! Stream hôm nay vui lắm nha, hype lên nào! 🌸",
            "Xin chào xin chào! Sakura AI đã sẵn sàng chiến đấu rồi đây! Các bé đang xem có khoẻ không? 💕",
            "Hế lô mọi người! Sakura AI đây, hôm nay chúng ta sẽ có một buổi stream siêu vui! 🎉",
        ]
        import random
        greeting = random.choice(greetings)
        logger.info(f"👋 Startup greeting: {greeting}")
        self.tts.speak(greeting)

    def _process_task(self, priority_neg: int, timestamp: float, source: str, text: str, author: str) -> None:
        """Xử lý một task từ queue."""
        try:
            # Kiểm tra task quá cũ (hơn 30 giây) thì bỏ qua
            age = time.time() - timestamp
            if age > 30.0 and source == "comment":
                logger.debug(f"⏭️ Bỏ qua comment cũ ({age:.0f}s): {text[:30]}...")
                return

            # Gọi AI brain
            response = self.brain.think(source, text, author)

            if response:
                # Update stats
                self.stats["total_interactions"] += 1
                if source == "mic":
                    self.stats["mic_interactions"] += 1
                else:
                    self.stats["comment_interactions"] += 1

                # Log ra console
                log_interaction(source, author, text, response)

                # Phát âm thanh
                self.tts.speak(response)

                # Cooldown tự nhiên giữa các response
                time.sleep(config.RESPONSE_COOLDOWN_SECONDS)

        except Exception as e:
            logger.error(f"❌ Lỗi xử lý task: {e}")

    def _main_loop(self) -> None:
        """Vòng lặp chính xử lý tasks từ queue."""
        logger.info("🚀 Main loop đã bắt đầu — Đang lắng nghe...")
        print(f"\n{Fore.GREEN}✅ Hệ thống đã sẵn sàng! Hãy nói gì đó vào mic...{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}   (Nhấn Ctrl+C để dừng){Style.RESET_ALL}\n")

        while self.is_running:
            try:
                # Lấy task từ queue (timeout 1s để check is_running)
                try:
                    task = self.task_queue.get(timeout=1.0)
                except queue.Empty:
                    continue

                priority_neg, timestamp, source, text, author = task
                self._process_task(priority_neg, timestamp, source, text, author)
                self.task_queue.task_done()

            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"❌ Lỗi main loop: {e}")
                time.sleep(0.5)

    def _print_stats(self) -> None:
        """In thống kê cuối session."""
        if self.stats["start_time"]:
            duration = time.time() - self.stats["start_time"]
            brain_stats = self.brain.get_stats() if self.brain else {}

            print(f"\n{Fore.CYAN}{'='*50}")
            print(f"📊 THỐNG KÊ SESSION")
            print(f"{'='*50}")
            print(f"  ⏱️  Thời gian stream : {duration/60:.1f} phút")
            print(f"  🎤  Mic interactions : {self.stats['mic_interactions']}")
            print(f"  💬  Comment replies  : {self.stats['comment_interactions']}")
            print(f"  🤖  Tổng AI requests : {brain_stats.get('total_requests', 0)}")
            print(f"{'='*50}{Style.RESET_ALL}\n")

    def start(self) -> None:
        """Khởi động toàn bộ hệ thống."""
        print_banner()

        # Init tất cả module
        if not self._init_modules():
            logger.error("❌ Không thể khởi tạo hệ thống. Đang thoát...")
            sys.exit(1)

        # Setup signal handler cho Ctrl+C
        def signal_handler(sig, frame):
            logger.info("🛑 Nhận tín hiệu dừng (Ctrl+C)...")
            self.stop()

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        self.is_running = True
        self.stats["start_time"] = time.time()

        # Khởi động các background threads
        self.stt.start()
        
        if config.FB_ENABLE_READER:
            self.fb_reader.start()

        # Phát lời chào mở đầu (trong background thread)
        greeting_thread = threading.Thread(
            target=self._startup_greeting,
            daemon=True,
        )
        greeting_thread.start()

        # Chạy main loop (blocking)
        try:
            self._main_loop()
        finally:
            self.stop()

    def stop(self) -> None:
        """Dừng hệ thống gracefully."""
        if not self.is_running:
            return

        self.is_running = False
        logger.info("🛑 Đang dừng hệ thống...")

        if self.stt:
            self.stt.stop()
        if self.fb_reader:
            self.fb_reader.stop()
        if self.tts:
            self.tts.stop_speaking()
            self.tts.cleanup()

        self._print_stats()
        logger.info("👋 Sakura AI đã offline. Hẹn gặp lại mọi người! 🌸")


# ==============================================================
# ENTRY POINT
# ==============================================================

def main():
    """Entry point chính."""
    # Kiểm tra môi trường
    if not config.GEMINI_API_KEY:
        print(f"\n{Fore.RED}❌ LỖI: GEMINI_API_KEY chưa được cấu hình!")
        print(f"   1. Copy file .env.example thành .env")
        print(f"   2. Điền GEMINI_API_KEY của bạn vào")
        print(f"   3. Chạy lại: python streamer.py{Style.RESET_ALL}\n")
        sys.exit(1)

    # Khởi động
    streamer = VTuberStreamer()
    streamer.start()


if __name__ == "__main__":
    main()
