# دستیار هوش مصنوعی کدنویسی (Coding AI Project)

این پروژه یک دستیار برنامه‌نویسی متصل به سرور است که دارای سیستم **ذخیره حافظه گفتگوها (SQLite)** و قابلیت دانلود کدها در قالب **نوت‌پد (.txt)** و **PDF** می‌باشد.

## نحوه راه‌اندازی سریع
1. وارد پوشه `backend` شوید و کتابخانه‌ها را نصب کنید:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```
2. کلید API خود را در فایل `backend/.env` قرار دهید.
3. سرور را اجرا کنید:
   ```bash
   uvicorn app.main:app --reload
   ```
4. فایل `frontend/index.html` را در مرورگر باز کنید.
