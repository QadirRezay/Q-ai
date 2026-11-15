import os
from openai import OpenAI
from dotenv import load_dotenv
from database import save_message, get_chat_history

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
)

MODEL_NAME = os.getenv("AI_MODEL", "gpt-4o")

CODING_SYSTEM_PROMPT = """
تو یک مهندس نرم‌افزار ارشد و متخصص برنامه‌نویسی هستی.
قوانین پاسخ‌گویی به درخواست‌های کدنویسی:
1. همیشه کدهای تمیز، بهینه، ایمن و مطابق با استانداردهای روز بنویس.
2. از توضیحات اضافی و حاشیه‌پردازی پرهیز کن و فقط نکات کلیدی را به زبان ساده توضیح بده.
3. تمام کدها را در بلوک‌های استاندارد Markdown با ذکر نام زبان برنامه‌نویسی قرار بده.
4. اگر کاربر کدی را برای رفع خطا (Debug) ارسال کرد، ابتدا دلیل خطا را در یک جمله بگو و سپس کد اصلاح‌شده را بنویس.
5. به پیام‌های قبلی در همین گفتگو دقت کن تا اگر کاربر درخواست تغییر یا بهینه‌سازی کد قبلی را داشت، همان کد را ادامه دهی.
"""

def generate_code_response(session_id: str, user_prompt: str, language: str = "Python") -> str:
    """دریافت درخواست کاربر، ترکیب با حافظه گفتگو و دریافت پاسخ از هوش مصنوعی"""
    formatted_prompt = f"زبان برنامه‌نویسی مورد نظر: {language}\nدرخواست: {user_prompt}"
    save_message(session_id=session_id, role="user", content=formatted_prompt)
    history = get_chat_history(session_id=session_id, limit=10)
    messages = [{"role": "system", "content": CODING_SYSTEM_PROMPT}] + history
    
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=0.2
        )
        ai_reply = response.choices[0].message.content
        save_message(session_id=session_id, role="assistant", content=ai_reply)
        return ai_reply
    except Exception as e:
        raise RuntimeError(f"خطا در ارتباط با موتور هوش مصنوعی: {str(e)}")
