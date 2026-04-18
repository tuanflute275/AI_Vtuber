"""
brain.py — AI Brain sử dụng Google Gemini API
===============================================
Module này xử lý toàn bộ logic ngôn ngữ AI:
- Kết nối và cấu hình Gemini 1.5 Flash
- Quản lý lịch sử hội thoại (ChatSession)
- Phân biệt nguồn input (mic vs comment)
- Xử lý lỗi và retry
"""

import os
import time
import logging
from typing import Optional

import google.generativeai as genai
from google.generativeai.types import GenerationConfig

import config

logger = logging.getLogger(__name__)


class AIBrain:
    """
    Bộ não AI của VTuber.
    Dùng Gemini 1.5 Flash với ChatSession để nhớ lịch sử hội thoại.
    """

    def __init__(self):
        self._configure_api()
        self.model = self._init_model()
        self.chat_session = self._start_chat()
        self.total_requests = 0
        logger.info(f"✅ AIBrain khởi tạo thành công | Model: {config.GEMINI_MODEL}")

    def _configure_api(self) -> None:
        """Cấu hình API key cho Gemini."""
        api_key = config.GEMINI_API_KEY
        if not api_key:
            raise ValueError(
                "❌ GEMINI_API_KEY chưa được đặt!\n"
                "Hãy thêm vào file .env: GEMINI_API_KEY=your_key_here"
            )
        genai.configure(api_key=api_key)
        logger.info("🔑 Gemini API key đã được cấu hình")

    def _init_model(self) -> genai.GenerativeModel:
        """Khởi tạo Gemini model với system instruction."""
        generation_config = GenerationConfig(
            temperature=0.9,        # Độ sáng tạo cao — phù hợp cho streamer hài hước
            top_p=0.95,
            top_k=40,
            max_output_tokens=256,  # Giới hạn độ dài response (phù hợp livestream)
        )

        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_ONLY_HIGH"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_ONLY_HIGH"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_ONLY_HIGH"},
        ]

        model = genai.GenerativeModel(
            model_name=config.GEMINI_MODEL,
            generation_config=generation_config,
            safety_settings=safety_settings,
            system_instruction=config.SYSTEM_INSTRUCTION,
        )
        return model

    def _start_chat(self) -> genai.ChatSession:
        """Bắt đầu một chat session mới."""
        return self.model.start_chat(history=[])

    def think(self, source: str, message: str, author: str = "") -> Optional[str]:
        """
        Xử lý input và trả về response từ AI.

        Args:
            source: "mic" (giọng nói) hoặc "comment" (comment FB)
            message: Nội dung cần xử lý
            author: Tên người comment (chỉ dùng khi source="comment")

        Returns:
            Chuỗi response, hoặc None nếu lỗi
        """
        # Định dạng prompt theo nguồn
        if source == "mic":
            prompt = f"[Người dùng nói qua mic]: {message}"
        elif source == "comment":
            author_str = author if author else "Khán giả"
            prompt = f"[Comment từ {author_str}]: {message}"
        else:
            prompt = message

        logger.info(f"🧠 Thinking... | Source: {source} | Input: '{message[:50]}...' " if len(message) > 50 else f"🧠 Thinking... | Source: {source} | Input: '{message}'")

        if source == "comment" and config.USE_FAKE_REPLY_FOR_COMMENTS:
            fake_resp = f"@ {author}: Sakura đã thấy comment của bạn nha! (Phản hồi giả để tiết kiệm token)"
            logger.info(f"💬 Response: '{fake_resp}'")
            return fake_resp

        # Retry logic
        for attempt in range(3):
            try:
                response = self.chat_session.send_message(prompt)
                self.total_requests += 1

                if response.text:
                    result = response.text.strip()
                    logger.info(f"💬 Response: '{result[:80]}...' " if len(result) > 80 else f"💬 Response: '{result}'")
                    return result
                else:
                    logger.warning("⚠️ Gemini trả về response rỗng")
                    return None

            except Exception as e:
                error_msg = str(e)
                logger.error(f"❌ Lỗi Gemini (attempt {attempt + 1}/3): {error_msg}")

                # Nếu bị block bởi safety filter
                if "SAFETY" in error_msg.upper():
                    return "Ồ câu này khó quá, để Sakura né nhé~ hehe 😅"

                # Nếu quota hết
                if "QUOTA" in error_msg.upper() or "429" in error_msg:
                    return "Sakura đang quá tải rồi các bé ơi, chờ xíu nhé~ 🥺"

                if attempt < 2:
                    time.sleep(2 ** attempt)  # Exponential backoff

        return "Sakura bị lag rồi, thử lại sau nha mọi người~ 😵"

    def reset_conversation(self) -> None:
        """Reset lịch sử hội thoại (bắt đầu fresh)."""
        self.chat_session = self._start_chat()
        logger.info("🔄 Lịch sử hội thoại đã được reset")

    def get_stats(self) -> dict:
        """Trả về thống kê sử dụng."""
        return {
            "total_requests": self.total_requests,
            "history_turns": len(self.chat_session.history),
            "model": config.GEMINI_MODEL,
        }
