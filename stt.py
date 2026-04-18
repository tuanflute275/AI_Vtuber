"""
stt.py — Speech-to-Text Module (Faster-Whisper)
================================================
Thu âm từ microphone theo thời gian thực và chuyển thành văn bản.
Dùng Voice Activity Detection (VAD) để chỉ transcribe khi có giọng nói.

Kiến trúc:
- Thread 1 (recorder): Liên tục thu âm, đẩy chunk vào audio_buffer
- Thread 2 (transcriber): Xử lý buffer, transcribe và đẩy text vào output_queue
"""

import queue
import threading
import logging
import time
import numpy as np
from typing import Optional

import sounddevice as sd
from faster_whisper import WhisperModel

import config

logger = logging.getLogger(__name__)


class SpeechToText:
    """
    STT Engine dùng Faster-Whisper với thu âm real-time.
    """

    def __init__(self, output_queue: queue.PriorityQueue):
        """
        Args:
            output_queue: Queue chia sẻ để đẩy kết quả transcription vào
                          Format: (priority, timestamp, source, text, author)
        """
        self.output_queue = output_queue
        self.audio_buffer = []          # Buffer chứa các chunk audio
        self.buffer_lock = threading.Lock()
        self.is_running = False
        self.is_speaking = False        # Track trạng thái đang nói hay không
        self.silence_chunks = 0         # Đếm số chunk im lặng liên tiếp

        # Tính số chunk tương ứng với thời gian
        self.chunks_per_second = int(1.0 / config.AUDIO_CHUNK_DURATION)
        self.min_speech_chunks = int(
            config.AUDIO_MIN_SPEECH_DURATION / config.AUDIO_CHUNK_DURATION
        )
        self.max_buffer_chunks = int(
            config.AUDIO_MAX_BUFFER_SECONDS / config.AUDIO_CHUNK_DURATION
        )
        # Sau bao nhiêu chunk im lặng thì coi như đã nói xong
        self.silence_end_chunks = int(1.5 / config.AUDIO_CHUNK_DURATION)

        # Load Whisper model
        logger.info(f"⏳ Đang load Whisper model '{config.WHISPER_MODEL_SIZE}'... (lần đầu có thể mất vài phút)")
        try:
            self.model = WhisperModel(
                config.WHISPER_MODEL_SIZE,
                device=config.WHISPER_DEVICE,
                compute_type=config.WHISPER_COMPUTE_TYPE,
            )
            logger.info(f"✅ Whisper model '{config.WHISPER_MODEL_SIZE}' đã sẵn sàng")
        except Exception as e:
            logger.error(f"❌ Không thể load Whisper model: {e}")
            raise

        # Threads
        self._record_thread: Optional[threading.Thread] = None
        self._transcribe_thread: Optional[threading.Thread] = None

    def _get_rms(self, audio_chunk: np.ndarray) -> float:
        """Tính Root Mean Square để đo độ lớn âm thanh."""
        return float(np.sqrt(np.mean(audio_chunk.astype(np.float32) ** 2)))

    def _is_speech(self, audio_chunk: np.ndarray) -> bool:
        """Kiểm tra chunk có chứa giọng nói không (VAD đơn giản)."""
        # Normalize về [-1, 1] nếu cần
        if audio_chunk.dtype == np.int16:
            normalized = audio_chunk.astype(np.float32) / 32768.0
        else:
            normalized = audio_chunk.astype(np.float32)

        rms = float(np.sqrt(np.mean(normalized ** 2)))
        return rms > config.AUDIO_SILENCE_THRESHOLD

    def _record_loop(self) -> None:
        """Thread thu âm: liên tục capture audio từ microphone."""
        chunk_samples = int(config.AUDIO_SAMPLE_RATE * config.AUDIO_CHUNK_DURATION)

        logger.info(f"🎤 Bắt đầu thu âm | Sample rate: {config.AUDIO_SAMPLE_RATE}Hz | Chunk: {config.AUDIO_CHUNK_DURATION}s")

        try:
            with sd.InputStream(
                samplerate=config.AUDIO_SAMPLE_RATE,
                channels=config.AUDIO_CHANNELS,
                dtype="int16",
                blocksize=chunk_samples,
            ) as stream:
                while self.is_running:
                    chunk, overflowed = stream.read(chunk_samples)
                    if overflowed:
                        logger.debug("⚠️ Audio buffer overflow")

                    chunk_flat = chunk.flatten()
                    has_speech = self._is_speech(chunk_flat)

                    with self.buffer_lock:
                        if has_speech:
                            self.audio_buffer.append(chunk_flat)
                            self.silence_chunks = 0
                            if not self.is_speaking:
                                self.is_speaking = True
                                logger.debug("🗣️ Phát hiện giọng nói...")
                        elif self.is_speaking:
                            # Vẫn thêm vào buffer một ít silence để tránh cắt chữ
                            self.audio_buffer.append(chunk_flat)
                            self.silence_chunks += 1

                            # Nếu im lặng đủ lâu = đã nói xong
                            if self.silence_chunks >= self.silence_end_chunks:
                                self.is_speaking = False
                                self.silence_chunks = 0
                                logger.debug("🔇 Phát hiện im lặng — sẵn sàng transcribe")

                        # Buộc transcribe nếu buffer quá đầy
                        if len(self.audio_buffer) >= self.max_buffer_chunks:
                            self.is_speaking = False
                            self.silence_chunks = 0

        except Exception as e:
            if self.is_running:
                logger.error(f"❌ Lỗi thu âm: {e}")

    def _transcribe_loop(self) -> None:
        """Thread transcribe: xử lý buffer và đẩy text vào queue."""
        logger.info("📝 Transcription thread đã sẵn sàng")

        while self.is_running:
            # Chỉ transcribe khi đã nói xong (is_speaking = False) và có data
            should_transcribe = False
            audio_data = None

            with self.buffer_lock:
                if (
                    not self.is_speaking
                    and len(self.audio_buffer) >= self.min_speech_chunks
                ):
                    # Lấy toàn bộ buffer để transcribe
                    audio_data = np.concatenate(self.audio_buffer)
                    self.audio_buffer = []
                    should_transcribe = True

            if should_transcribe and audio_data is not None:
                try:
                    self._do_transcribe(audio_data)
                except Exception as e:
                    logger.error(f"❌ Lỗi transcription: {e}")
            else:
                time.sleep(0.1)  # Tránh busy-wait

    def _do_transcribe(self, audio_data: np.ndarray) -> None:
        """Thực hiện transcription và đẩy kết quả vào queue."""
        # Convert sang float32 [-1, 1] như Whisper yêu cầu
        audio_float = audio_data.astype(np.float32) / 32768.0

        logger.debug(f"🔄 Đang transcribe {len(audio_float)/config.AUDIO_SAMPLE_RATE:.1f}s audio...")

        language = None if config.WHISPER_LANGUAGE == "auto" else config.WHISPER_LANGUAGE

        segments, info = self.model.transcribe(
            audio_float,
            language=language,
            beam_size=5,
            vad_filter=True,                # Dùng Silero VAD tích hợp sẵn
            vad_parameters={
                "min_silence_duration_ms": 500,
                "speech_pad_ms": 200,
            },
        )

        # Ghép các segment lại
        text_parts = []
        for segment in segments:
            text_parts.append(segment.text.strip())

        full_text = " ".join(text_parts).strip()

        if full_text and len(full_text) > 2:  # Lọc các text quá ngắn (noise)
            logger.info(f"🎤 STT: '{full_text}'")
            # Đẩy vào priority queue: (priority, timestamp, source, text, author)
            try:
                self.output_queue.put_nowait((
                    -config.PRIORITY_MIC,  # Âm để PriorityQueue ưu tiên số nhỏ hơn
                    time.time(),
                    "mic",
                    full_text,
                    ""  # author rỗng với mic
                ))
            except queue.Full:
                logger.warning("⚠️ Queue đầy, bỏ qua audio input này")
        else:
            logger.debug("🔇 Transcription rỗng hoặc quá ngắn, bỏ qua")

    def start(self) -> None:
        """Khởi động STT threads."""
        self.is_running = True

        self._record_thread = threading.Thread(
            target=self._record_loop,
            name="STT-Recorder",
            daemon=True,
        )
        self._transcribe_thread = threading.Thread(
            target=self._transcribe_loop,
            name="STT-Transcriber",
            daemon=True,
        )

        self._record_thread.start()
        self._transcribe_thread.start()
        logger.info("✅ STT module đã khởi động")

    def stop(self) -> None:
        """Dừng STT threads."""
        self.is_running = False
        logger.info("🛑 STT module đã dừng")
