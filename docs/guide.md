# راهنمای جامع نصب، اجرا و استقرار هوش مصنوعی کدنویسی

این مستند راهنمای کامل راه‌اندازی پروژه در محیط **VS Code** و اتصال آن به **GitHub** است.

---

## ۱. ساختار نهایی ۶ پوشه‌ای پروژه

```text
coding-ai-project/
├── backend/              # ۱. پوشه سرور و پایتون
│   ├── app/              # ۲. هسته منطقی و API
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── ai_engine.py
│   │   └── database.py
│   ├── exports/          # ۳. فایل‌های موقت خروجی (نوت‌پد و PDF)
│   ├── data/             # ۴. محل ذخیره پایگاه داده (chat_history.db)
│   ├── .env              # تنظیمات مخفی و کلید API
│   └── requirements.txt  # کتابخانه‌های مورد نیاز
│
├── frontend/             # ۵. رابط کاربری وب (HTML, CSS, JS)
│   ├── index.html
│   ├── style.css
│   └── script.js
│
├── docs/                 # ۶. مستندات و راهنمای پروژه
│   └── guide.md
│
├── .gitignore            # محافظت از فایل‌های حساس در گیت‌هاب
└── README.md             # معرفی پروژه
```

---

## ۲. راه‌اندازی بخش سرور (Backend) در VS Code

1. ترمینال VS Code را باز کنید (`Ctrl + ~`).
2. وارد پوشه `backend` شوید:
   ```bash
   cd backend
   ```
3. کتابخانه‌های مورد نیاز را نصب کنید:
   ```bash
   pip install -r requirements.txt
   ```
4. فایل `.env` را باز کنید و کلید واقعی خود را در بخش `OPENAI_API_KEY` قرار دهید.
5. سرور را اجرا کنید:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

---

## ۳. اجرای رابط کاربری (Frontend)

1. وارد پوشه `frontend` شوید.
2. فایل `index.html` را در مرورگر باز کنید (یا از افزونه **Live Server** در VS Code استفاده نمایید).
3. زبان برنامه‌نویسی را انتخاب کرده و دستور کدنویسی خود را ارسال کنید.

---

## ۴. مسیرهای ارتباطی سرور (API Endpoints)

* `POST /chat` : ارسال پیام و دریافت کد همراه با توضیحات و ذخیره در حافظه.
* `POST /export/notepad` : دریافت کد خالص به‌صورت فایل متنی (`.txt`).
* `POST /export/pdf` : دریافت کد به‌صورت فایل استاندارد `.pdf`.
* `GET /history/{session_id}` : بازیابی تاریخچه گفتگوهای یک پروژه.
* `DELETE /clear/{session_id}` : پاک‌سازی حافظه یک گفتگو.

---

## ۵. اتصال ایمن به GitHub

پیش از ارسال کدها به گیت‌هاب، مطمئن شوید فایل `.gitignore` در پوشه ریشه پروژه شامل موارد زیر است:

```text
.env
backend/.env
backend/data/*.db
backend/exports/*
!backend/data/.gitkeep
!backend/exports/.gitkeep
venv/
__pycache__/
```
