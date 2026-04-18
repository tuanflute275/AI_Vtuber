"""
setup_check.py — Kiểm tra môi trường cài đặt
=============================================
Chạy script này trước khi chạy streamer.py để kiểm tra
tất cả dependencies và cấu hình đã đúng chưa.

Sử dụng: python setup_check.py
"""

import sys
import os
import subprocess

# Màu console
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"


def check(name: str, test_fn, fix_hint: str = "") -> bool:
    """Chạy một bài kiểm tra và in kết quả."""
    try:
        result = test_fn()
        if result is True or result is None:
            print(f"  {GREEN}✅ {name}{RESET}")
            return True
        elif isinstance(result, str):
            print(f"  {GREEN}✅ {name}: {result}{RESET}")
            return True
    except Exception as e:
        print(f"  {RED}❌ {name}{RESET}")
        print(f"     Lỗi: {e}")
        if fix_hint:
            print(f"     {YELLOW}💡 Sửa: {fix_hint}{RESET}")
        return False


def main():
    print(f"\n{BOLD}{CYAN}{'='*60}")
    print(f"  🔍 AI VTuber Streamer — Kiểm Tra Môi Trường")
    print(f"{'='*60}{RESET}\n")

    all_ok = True

    # ─── Python Version ───────────────────────────────────────
    print(f"{BOLD}[1] Python Version{RESET}")
    ok = check(
        f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        lambda: sys.version_info >= (3, 9),
        "Cài Python 3.9+ từ https://python.org"
    )
    all_ok = all_ok and ok

    # ─── Core Libraries ───────────────────────────────────────
    print(f"\n{BOLD}[2] Core Libraries{RESET}")

    libs = [
        ("google-generativeai", "google.generativeai", "pip install google-generativeai"),
        ("faster-whisper", "faster_whisper", "pip install faster-whisper"),
        ("sounddevice", "sounddevice", "pip install sounddevice"),
        ("numpy", "numpy", "pip install numpy"),
        ("edge-tts", "edge_tts", "pip install edge-tts"),
        ("pyaudio", "pyaudio", "pip install pyaudio  (Windows: pip install pipwin && pipwin install pyaudio)"),
        ("pydub", "pydub", "pip install pydub"),
        ("python-dotenv", "dotenv", "pip install python-dotenv"),
        ("colorama", "colorama", "pip install colorama"),
        ("rich", "rich", "pip install rich"),
    ]

    for name, module, hint in libs:
        def test_import(m=module):
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                __import__(m)
            return True
        
        ok = check(name, test_import, hint)
        all_ok = all_ok and ok

    # ─── Optional Libraries ────────────────────────────────────
    print(f"\n{BOLD}[3] Optional Libraries (chỉ cần cho Selenium mode){RESET}")

    optional_libs = [
        ("selenium", "selenium", "pip install selenium"),
        ("undetected-chromedriver", "undetected_chromedriver", "pip install undetected-chromedriver"),
    ]

    for name, module, hint in optional_libs:
        try:
            __import__(module)
            print(f"  {GREEN}✅ {name}{RESET}")
        except ImportError:
            print(f"  {YELLOW}⚠️  {name} — Chưa cài (chỉ cần nếu dùng Selenium mode){RESET}")
            print(f"     {YELLOW}💡 Cài bằng: {hint}{RESET}")

    # ─── API Key ──────────────────────────────────────────────
    print(f"\n{BOLD}[4] API Key & Config{RESET}")

    def check_env():
        from dotenv import load_dotenv
        load_dotenv()
        key = os.getenv("GEMINI_API_KEY", "")
        if not key:
            raise ValueError("GEMINI_API_KEY chưa được đặt trong .env")
        if len(key) < 20:
            raise ValueError("GEMINI_API_KEY có vẻ không hợp lệ (quá ngắn)")
        return f"Key hợp lệ (***{key[-4:]})"

    ok = check("GEMINI_API_KEY", check_env, "Tạo file .env với GEMINI_API_KEY=your_key")
    all_ok = all_ok and ok

    # ─── Audio Devices ────────────────────────────────────────
    print(f"\n{BOLD}[5] Audio Devices{RESET}")

    def check_microphone():
        import sounddevice as sd
        devices = sd.query_devices()
        input_devices = [d for d in devices if d["max_input_channels"] > 0]
        if not input_devices:
            raise ValueError("Không tìm thấy microphone!")
        return f"Tìm thấy {len(input_devices)} input device(s)"

    def check_virtual_cable():
        import pyaudio
        from dotenv import load_dotenv
        load_dotenv()
        cable_name = os.getenv("VIRTUAL_CABLE_DEVICE_NAME", "CABLE Input").lower()
        pa = pyaudio.PyAudio()
        found = False
        for i in range(pa.get_device_count()):
            info = pa.get_device_info_by_index(i)
            if cable_name in info["name"].lower() and info["maxOutputChannels"] > 0:
                found = True
                break
        pa.terminate()
        if not found:
            raise ValueError(
                f"Không tìm thấy '{cable_name}'! "
                "Cài VB-Audio Virtual Cable: https://vb-audio.com/Cable/"
            )
        return "VB-Audio Virtual Cable OK"

    def list_audio_devices():
        import pyaudio
        pa = pyaudio.PyAudio()
        print(f"\n  {CYAN}Danh sách Output Devices:{RESET}")
        for i in range(pa.get_device_count()):
            info = pa.get_device_info_by_index(i)
            if info["maxOutputChannels"] > 0:
                print(f"    [{i:2d}] {info['name']}")
        pa.terminate()

    ok = check("Microphone", check_microphone, "Kết nối microphone và kiểm tra driver")
    all_ok = all_ok and ok

    ok = check("Virtual Audio Cable", check_virtual_cable,
               "Tải tại: https://vb-audio.com/Cable/ (miễn phí)")
    # Virtual Cable là optional — không fail all_ok
    if not ok:
        print(f"  {YELLOW}   → Âm thanh sẽ phát ra loa thường thay thế{RESET}")

    list_audio_devices()

    # ─── Whisper Model Download ─────────────────────────────────
    print(f"\n{BOLD}[6] Whisper Model{RESET}")

    def check_whisper():
        from faster_whisper import WhisperModel
        # Chỉ kiểm tra import, không load model (mất thời gian)
        return "faster-whisper import OK (model sẽ tải lần đầu chạy)"

    check("faster-whisper import", check_whisper)

    # ─── FFmpeg (cho pydub) ─────────────────────────────────────
    print(f"\n{BOLD}[7] FFmpeg (pydub cần){RESET}")

    def check_ffmpeg():
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            raise ValueError("FFmpeg không tìm thấy trong PATH")
        version_line = result.stdout.split("\n")[0]
        return version_line[:50]

    ok = check(
        "FFmpeg",
        check_ffmpeg,
        "Tải tại: https://ffmpeg.org/download.html và thêm vào PATH"
    )
    if not ok:
        print(f"  {YELLOW}   → Thêm cách khác: pip install audioop-lts{RESET}")

    # ─── Kết Quả ───────────────────────────────────────────────
    print(f"\n{BOLD}{'='*60}{RESET}")
    if all_ok:
        print(f"{GREEN}{BOLD}🎉 Tất cả kiểm tra đã qua! Hệ thống sẵn sàng.{RESET}")
        print(f"\n{CYAN}Chạy: python streamer.py{RESET}")
    else:
        print(f"{RED}{BOLD}⚠️  Có lỗi cần sửa trước khi chạy.{RESET}")
        print(f"{YELLOW}Sửa các lỗi ở trên rồi chạy lại: python setup_check.py{RESET}")
    print(f"{BOLD}{'='*60}{RESET}\n")


if __name__ == "__main__":
    main()
