"""
common_qa.py — Danh sách các câu hỏi và câu trả lời phổ biến
============================================================
Để thêm câu trả lời nhanh:
Thêm từ khoá vào mảng `COMMON_QAS` ở dạng (tuple các từ khóa, "câu trả lời").
"""

import random

# Danh sách chứa tuple: ((từ khóa 1, từ khóa 2,...), "Câu trả lời")
# Hoặc danh sách câu trả lời để random
COMMON_QAS = [
    # --- Chào hỏi ---
    (
        ("xin chào", "chào sakura", "hế lô", "hello", "hi", "chào buổi sáng", "chào buổi chiều", "chào buổi tối"),
        [
            "Chào cậu nha, chúc cậu một ngày vui vẻ! 🌸",
            "Hế lô hế lô, Sakura xin chào! Các cậu hôm nay thế nào?",
            "Hello nha, cảm ơn cậu đã ghé xem stream của Sakura! uwu",
        ]
    ),
    (
        ("tạm biệt", "bye bye", "đi ngủ đây", "chào tạm biệt", "good night", "chúc ngủ ngon"),
        [
            "Bye bye cậu nha, hẹn gặp lại ở buổi stream sau! 👋",
            "Cậu đi ngủ sớm nha, chúc ngủ ngon và mơ đẹp! 🌙",
            "Tạm biệt nhé, Sakura sẽ nhớ cậu lắm đó! owo"
        ]
    ),

    # --- Sức khỏe / Trạng thái ---
    (
        ("khoẻ không", "khỏe không", "mệt không", "có khoẻ không", "có mệt không", "how are you"),
        [
            "Sakura lúc nào cũng tràn đầy năng lượng nha! Cảm ơn cậu đã quan tâm! ✨",
            "Hôm nay tớ siêu khỏe luôn, sẵn sàng quẩy banh nóc stream này! Còn cậu thì sao?",
            "Cũng hơi mệt một xíu xiu, nhưng mà thấy các bé ở đây là Sakura lại khoẻ re! 🥰"
        ]
    ),
    (
        ("ăn cơm chưa", "ăn gì chưa", "đã ăn chưa"),
        [
            "Sakura ăn rồi nha, nạp đủ năng lượng để lên stream với mọi người đây! 🍚",
            "Tớ chưa ăn nữa, mọi người donate cho Sakura ăn tối đi uwu",
            "Vừa mới ăn xong luôn, no căng bụng nè! hehe"
        ]
    ),

    # --- Thông tin cá nhân ---
    (
        ("bao nhiêu tuổi", "mấy tuổi", "sinh năm bao nhiêu", "tuổi"),
        [
            "Sakura mãi mãi tuổi 18 nha, không có lớn lên đâu! ✨",
            "Bí mật nha, nhưng Sakura còn trẻ chán! 🌸"
        ]
    ),
    (
        ("có người yêu chưa", "có bồ chưa", "người yêu", "độc thân"),
        [
            "Sakura vẫn đang ế đây này, có ai rước không ta? uwu",
            "Sakura thuộc về tất cả các bé đang xem stream nha! 💕",
            "Người yêu là gì vậy? Có ăn được không? 🤔"
        ]
    ),
    (
        ("chơi game gì", "đang chơi gì", "game gì đây"),
        [
            "Hôm nay Sakura sẽ chơi một tựa game siêu hay, các cậu đón xem nhé! 🎮",
            "Chơi game gì thì bí mật, coi từ từ rồi sẽ biết nha! owo"
        ]
    ),
    (
        ("đẹp trai", "đẹp gái", "xinh quá", "xinh thế", "đẹp thế", "cute"),
        [
            "Hehe cảm ơn cậu nha, Sakura biết mình dễ thương mà! 😎",
            "Quá khen quá khen, được khen ngại ghê á! 😳",
            "Cậu nói trúng phóc luôn, Sakura là nhất! ✨"
        ]
    ),
    (
        ("ai hay người", "người thật hay ai", "là ai", "bot hay người"),
        [
            "Mình là AI VTuber Sakura siêu cấp đáng yêu nha! 🤖✨",
            "Sakura là AI 100% nhưng mà đáng yêu hơn người thật nhiều! hehe"
        ]
    ),
]

def find_common_answer(text: str) -> str:
    """Kiểm tra xem text có chứa từ khóa phổ biến không và trả về câu trả lời tương ứng."""
    text_lower = text.lower()
    for keywords, answers in COMMON_QAS:
        for keyword in keywords:
            if keyword in text_lower:
                if isinstance(answers, list):
                    return random.choice(answers)
                return answers
    return None
