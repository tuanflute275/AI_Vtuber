"""
facebook_reader.py — Facebook Live Comment Reader
===================================================
Module đọc comment từ Facebook Live stream.

Hỗ trợ 2 chế độ:
1. MOCK MODE (mặc định, an toàn): Sinh comment giả để test
2. SELENIUM MODE: Scrape comment thật từ FB Live (cần đăng nhập FB)

Lưu ý quan trọng về Selenium mode:
- Dùng undetected-chromedriver để giảm nguy cơ bị detect
- Vẫn có rủi ro bị ban tài khoản — dùng tài khoản phụ!
- Facebook thay đổi DOM thường xuyên — selectors có thể cần update
"""

import queue
import random
import threading
import time
import logging
from typing import Optional, Set

import config

logger = logging.getLogger(__name__)


# ==============================================================
# MOCK MODE — Comment Giả (An Toàn)
# ==============================================================

class MockFacebookReader:
    """
    Sinh comment giả ngẫu nhiên để test hệ thống mà không cần FB thật.
    """

    def __init__(self, output_queue: queue.PriorityQueue):
        self.output_queue = output_queue
        self.is_running = False
        self._thread: Optional[threading.Thread] = None

    def _generate_loop(self) -> None:
        """Vòng lặp sinh comment giả."""
        logger.info(f"🎭 Mock FB Reader: Sinh comment mỗi {config.FB_MOCK_INTERVAL_SECONDS}s")

        # Shuffle để không lặp theo thứ tự
        comments = list(config.FB_MOCK_COMMENTS)

        while self.is_running:
            # Chờ khoảng thời gian ngẫu nhiên (± 30% để tự nhiên hơn)
            base_interval = config.FB_MOCK_INTERVAL_SECONDS
            wait_time = base_interval * random.uniform(0.7, 1.3)
            time.sleep(wait_time)

            if not self.is_running:
                break

            # Chọn comment ngẫu nhiên
            author, text = random.choice(comments)
            logger.info(f"📝 Mock comment: [{author}]: {text}")

            try:
                self.output_queue.put_nowait((
                    -config.PRIORITY_COMMENT,
                    time.time(),
                    "comment",
                    text,
                    author,
                ))
            except queue.Full:
                logger.warning("⚠️ Queue đầy, bỏ qua mock comment")

    def start(self) -> None:
        self.is_running = True
        self._thread = threading.Thread(
            target=self._generate_loop,
            name="MockFB-Reader",
            daemon=True,
        )
        self._thread.start()
        logger.info("✅ Mock Facebook Reader đã khởi động")

    def stop(self) -> None:
        self.is_running = False
        logger.info("🛑 Mock Facebook Reader đã dừng")


# ==============================================================
# SELENIUM MODE — Scrape Comment Thật
# ==============================================================

class SeleniumFacebookReader:
    """
    Đọc comment thật từ Facebook Live bằng Selenium.
    
    ⚠️ CẢNH BÁO:
    - Vi phạm ToS của Facebook
    - Rủi ro ban tài khoản
    - DOM selectors có thể thay đổi bất kỳ lúc nào
    - Chỉ dùng với tài khoản phụ và mục đích cá nhân!
    """

    # CSS selectors để tìm comment — có thể cần update nếu FB thay đổi DOM
    COMMENT_SELECTORS = [
        "[data-testid='UFI2Comment/body']",
        "div[class*='_7a9a']",
        "div[role='article'] span[lang]",
    ]

    AUTHOR_SELECTORS = [
        "[data-testid='UFI2Comment/author']",
        "a[class*='actor-link']",
        "h3 a",
    ]

    def __init__(self, output_queue: queue.PriorityQueue, live_url: str):
        self.output_queue = output_queue
        self.live_url = live_url
        self.is_running = False
        self.seen_comment_ids: Set[str] = set()
        self.driver = None
        self._thread: Optional[threading.Thread] = None

    def _init_driver(self):
        """Khởi tạo Chrome WebDriver với undetected-chromedriver."""
        try:
            import undetected_chromedriver as uc
            from selenium.webdriver.chrome.options import Options

            options = uc.ChromeOptions()

            if config.FB_HEADLESS:
                options.add_argument("--headless=new")

            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--window-size=1280,900")
            options.add_argument("--lang=vi-VN")
            options.add_argument("--disable-blink-features=AutomationControlled")

            # User agent tự nhiên hơn
            options.add_argument(
                "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )

            self.driver = uc.Chrome(options=options)
            logger.info("✅ Chrome WebDriver đã khởi động (undetected)")
            return True

        except ImportError:
            logger.error("❌ undetected_chromedriver chưa được cài. Chạy: pip install undetected-chromedriver")
            return False
        except Exception as e:
            logger.error(f"❌ Lỗi khởi tạo WebDriver: {e}")
            return False

    def _navigate_to_live(self) -> bool:
        """Điều hướng tới FB Live URL."""
        try:
            logger.info(f"🌐 Đang mở FB Live: {self.live_url}")
            self.driver.get(self.live_url)
            time.sleep(5)  # Đợi trang load

            # Kiểm tra có bị redirect về login không
            current_url = self.driver.current_url
            if "login" in current_url or "checkpoint" in current_url:
                logger.error(
                    "❌ Facebook yêu cầu đăng nhập!\n"
                    "   Giải pháp: Thêm cookies đăng nhập vào driver\n"
                    "   Hoặc đặt FB_HEADLESS=False để đăng nhập thủ công"
                )
                return False

            logger.info("✅ Đã mở FB Live thành công")
            return True

        except Exception as e:
            logger.error(f"❌ Lỗi navigate: {e}")
            return False

    def _extract_comments(self) -> list:
        """Trích xuất comment mới từ DOM."""
        from selenium.webdriver.common.by import By

        new_comments = []

        for selector in self.COMMENT_SELECTORS:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    for elem in elements[-config.FB_MAX_COMMENTS_PER_BATCH:]:
                        try:
                            text = elem.text.strip()
                            if not text:
                                continue

                            # Tạo ID duy nhất cho comment (dựa trên nội dung)
                            comment_id = hash(text)

                            if comment_id not in self.seen_comment_ids:
                                self.seen_comment_ids.add(comment_id)

                                # Cố gắng lấy tên tác giả
                                author = self._get_author_near(elem)
                                new_comments.append((author, text))

                        except Exception:
                            continue
                    break  # Dùng selector đầu tiên hoạt động
            except Exception:
                continue

        return new_comments

    def _get_author_near(self, comment_element) -> str:
        """Cố gắng lấy tên tác giả gần với comment element."""
        from selenium.webdriver.common.by import By

        try:
            # Tìm tên trong parent containers
            parent = comment_element.find_element(By.XPATH, "..")
            for _ in range(3):  # Lên tối đa 3 cấp
                for selector in self.AUTHOR_SELECTORS:
                    try:
                        author_elem = parent.find_element(By.CSS_SELECTOR, selector)
                        name = author_elem.text.strip()
                        if name:
                            return name
                    except Exception:
                        pass
                parent = parent.find_element(By.XPATH, "..")
        except Exception:
            pass

        return "Khán giả"

    def _poll_loop(self) -> None:
        """Vòng lặp poll comment từ FB."""
        if not self._init_driver():
            logger.error("❌ Không thể khởi tạo driver, chuyển sang mock mode...")
            return

        if not self._navigate_to_live():
            logger.error("❌ Không thể mở FB Live")
            if self.driver:
                self.driver.quit()
            return

        logger.info(f"📺 Đang poll comment mỗi {config.FB_POLL_INTERVAL_SECONDS}s...")

        while self.is_running:
            try:
                comments = self._extract_comments()

                for author, text in comments:
                    logger.info(f"📝 FB Comment: [{author}]: {text}")
                    try:
                        self.output_queue.put_nowait((
                            -config.PRIORITY_COMMENT,
                            time.time(),
                            "comment",
                            text,
                            author,
                        ))
                    except queue.Full:
                        logger.warning("⚠️ Queue đầy, bỏ qua comment")

            except Exception as e:
                logger.error(f"❌ Lỗi poll: {e}")

            time.sleep(config.FB_POLL_INTERVAL_SECONDS)

        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass

    def start(self) -> None:
        self.is_running = True
        self._thread = threading.Thread(
            target=self._poll_loop,
            name="Selenium-FB-Reader",
            daemon=True,
        )
        self._thread.start()
        logger.info("✅ Selenium Facebook Reader đã khởi động")

    def stop(self) -> None:
        self.is_running = False
        logger.info("🛑 Selenium Facebook Reader đã dừng")


# ==============================================================
# FACTORY — Tự động chọn chế độ
# ==============================================================

def create_facebook_reader(output_queue: queue.PriorityQueue):
    """
    Factory function: Tạo reader phù hợp dựa trên config.
    
    Returns:
        MockFacebookReader hoặc SeleniumFacebookReader
    """
    if config.FB_MODE == "selenium" and config.FACEBOOK_LIVE_URL:
        logger.info(f"🌐 Chế độ: SELENIUM | URL: {config.FACEBOOK_LIVE_URL}")
        return SeleniumFacebookReader(output_queue, config.FACEBOOK_LIVE_URL)
    else:
        if config.FB_MODE == "selenium" and not config.FACEBOOK_LIVE_URL:
            logger.warning("⚠️ FB_MODE=selenium nhưng FACEBOOK_LIVE_URL trống → dùng Mock mode")
        logger.info("🎭 Chế độ: MOCK (comment giả)")
        return MockFacebookReader(output_queue)
