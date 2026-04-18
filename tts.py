"""
tts.py — Text-to-Speech Module (Edge-TTS + PyAudio Routing)
=============================================================
Chuyển text thành giọng nói và định tuyến tới Virtual Audio Cable.

Luồng xử lý:
1. Edge-TTS tạo audio MP3/audio stream
2. Decode sang PCM 16-bit
3. PyAudio phát ra Virtual Cable Input (→ OBS → VTube Studio)
4. Tuỳ chọn: phát song song ra loa thường để monitor
"""

import io
import time
import asyncio
import logging
import tempfile
import threading
from typing import Optional

import pyaudio
import edge_tts
import numpy as np

import config

logger = logging.getLogger(__name__)


class TextToSpeech:
    """
    TTS Engine dùng Edge-TTS với routing tới Virtual Audio Cable.
    """

    def __init__(self):
        self.pa = pyaudio.PyAudio()
        self.virtual_cable_index: Optional[int] = None
        self.monitor_device_index: Optional[int] = None
        self.is_speaking = False
        self._lock = threading.Lock()

        self._find_audio_devices()
        logger.info(f"✅ TTS module khởi tạo | Voice: {config.TTS_VOICE}")

    def _find_audio_devices(self) -> None:
        """Tìm Virtual Cable và monitor device."""
        device_count = self.pa.get_device_count()
        logger.info(f"🔍 Đang tìm audio devices... (tổng: {device_count} devices)")

        cable_name = config.VIRTUAL_CABLE_DEVICE_NAME.lower()
        monitor_name = config.MONITOR_DEVICE_NAME.lower()

        for i in range(device_count):
            try:
                info = self.pa.get_device_info_by_index(i)
                name = info.get("name", "").lower()
                max_output = info.get("maxOutputChannels", 0)

                if max_output > 0:  # Chỉ xét output devices
                    logger.debug(f"  [{i}] {info.get('name', 'Unknown')} (out channels: {max_output})")

                    if cable_name in name and self.virtual_cable_index is None:
                        self.virtual_cable_index = i
                        logger.info(f"🎵 Virtual Cable tìm thấy: [{i}] {info.get('name', 'Unknown')}")

                    if monitor_name and monitor_name in name and self.monitor_device_index is None:
                        self.monitor_device_index = i
                        logger.info(f"🔊 Monitor device tìm thấy: [{i}] {info.get('name', 'Unknown')}")

            except Exception as e:
                logger.debug(f"  [{i}] Lỗi đọc device info: {e}")

        if self.virtual_cable_index is None:
            logger.warning(
                f"⚠️ Không tìm thấy Virtual Cable '{config.VIRTUAL_CABLE_DEVICE_NAME}'!\n"
                "   → Âm thanh sẽ phát ra loa mặc định thay thế.\n"
                "   → Cài VB-Audio Virtual Cable tại: https://vb-audio.com/Cable/"
            )
        
        if config.ENABLE_MONITOR_PLAYBACK and not monitor_name:
            # Dùng default output device để monitor
            self.monitor_device_index = None  # None = default device

    def list_all_devices(self) -> None:
        """In danh sách tất cả audio devices (để debug)."""
        print("\n" + "="*50)
        print("📋 DANH SÁCH AUDIO DEVICES:")
        print("="*50)
        for i in range(self.pa.get_device_count()):
            try:
                info = self.pa.get_device_info_by_index(i)
                in_ch = info.get("maxInputChannels", 0)
                out_ch = info.get("maxOutputChannels", 0)
                name = info.get("name", "Unknown")
                print(f"  [{i:2d}] {name}")
                print(f"       Input channels: {in_ch} | Output channels: {out_ch}")
            except Exception:
                pass
        print("="*50 + "\n")

    def _generate_audio(self, text: str) -> bytes:
        """Tạo audio từ text dùng Edge-TTS. Trả về raw audio bytes (MP3)."""
        async def _async_generate():
            communicate = edge_tts.Communicate(
                text=text,
                voice=config.TTS_VOICE,
                rate=config.TTS_RATE,
                volume=config.TTS_VOLUME,
                pitch=config.TTS_PITCH,
            )
            audio_chunks = []
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_chunks.append(chunk["data"])
            return b"".join(audio_chunks)

        # Chạy async trong event loop mới
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(_async_generate())
        finally:
            loop.close()

    def _mp3_to_pcm(self, mp3_bytes: bytes) -> tuple[np.ndarray, int]:
        """Convert MP3 bytes sang PCM numpy array và sample rate."""
        try:
            from pydub import AudioSegment
            audio = AudioSegment.from_mp3(io.BytesIO(mp3_bytes))
            # Convert sang mono, 16-bit
            audio = audio.set_channels(1).set_sample_width(2)
            sample_rate = audio.frame_rate
            pcm_data = np.frombuffer(audio.raw_data, dtype=np.int16)
            return pcm_data, sample_rate
        except Exception as e:
            logger.error(f"❌ Lỗi convert MP3 sang PCM: {e}")
            raise

    def _play_on_device(self, pcm_data: np.ndarray, sample_rate: int, device_index: Optional[int]) -> None:
        """Phát audio PCM trên một device cụ thể."""
        try:
            stream = self.pa.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=sample_rate,
                output=True,
                output_device_index=device_index,
                frames_per_buffer=1024,
            )

            # Chuyển sang bytes và phát
            audio_bytes = pcm_data.tobytes()
            chunk_size = 1024 * 2  # 1024 samples * 2 bytes/sample

            for i in range(0, len(audio_bytes), chunk_size):
                if not self.is_speaking:
                    break  # Cho phép interrupt
                stream.write(audio_bytes[i:i + chunk_size])

            stream.stop_stream()
            stream.close()
        except Exception as e:
            logger.error(f"❌ Lỗi phát audio trên device {device_index}: {e}")

    def speak(self, text: str) -> None:
        """
        Phát text thành giọng nói.
        BLOCKING: Đợi cho đến khi phát xong.

        Args:
            text: Văn bản cần đọc
        """
        with self._lock:  # Đảm bảo chỉ 1 lần speak tại một thời điểm
            self.is_speaking = True
            logger.info(f"🔊 TTS: '{text[:60]}...' " if len(text) > 60 else f"🔊 TTS: '{text}'")

            try:
                # Bước 1: Generate audio từ Edge-TTS
                start_time = time.time()
                mp3_bytes = self._generate_audio(text)
                gen_time = time.time() - start_time
                logger.debug(f"⚡ Edge-TTS generate time: {gen_time:.2f}s | Size: {len(mp3_bytes)} bytes")

                if not mp3_bytes:
                    logger.warning("⚠️ Edge-TTS trả về audio rỗng")
                    return

                # Bước 2: Convert MP3 sang PCM
                pcm_data, sample_rate = self._mp3_to_pcm(mp3_bytes)
                logger.debug(f"🎵 PCM: {len(pcm_data)} samples | {sample_rate}Hz | {len(pcm_data)/sample_rate:.2f}s")

                # Bước 3: Phát ra Virtual Cable (cho OBS/VTube Studio)
                if self.virtual_cable_index is not None:
                    # Phát ra Virtual Cable
                    cable_thread = threading.Thread(
                        target=self._play_on_device,
                        args=(pcm_data, sample_rate, self.virtual_cable_index),
                        daemon=True,
                    )
                    cable_thread.start()

                    # Monitor: phát song song ra loa thường nếu bật
                    if config.ENABLE_MONITOR_PLAYBACK:
                        monitor_thread = threading.Thread(
                            target=self._play_on_device,
                            args=(pcm_data, sample_rate, self.monitor_device_index),
                            daemon=True,
                        )
                        monitor_thread.start()
                        monitor_thread.join()  # Đợi monitor xong (dài hơn hoặc bằng cable)

                    cable_thread.join()
                else:
                    # Fallback: phát ra loa mặc định
                    logger.debug("📢 Phát ra loa mặc định (không có Virtual Cable)")
                    self._play_on_device(pcm_data, sample_rate, None)

            except Exception as e:
                logger.error(f"❌ Lỗi TTS speak: {e}")
            finally:
                self.is_speaking = False

    def stop_speaking(self) -> None:
        """Ngắt phát âm thanh hiện tại."""
        self.is_speaking = False

    def cleanup(self) -> None:
        """Giải phóng tài nguyên PyAudio."""
        self.pa.terminate()
        logger.info("🛑 TTS module đã dừng")
