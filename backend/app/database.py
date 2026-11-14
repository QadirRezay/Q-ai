import os
import sqlite3

# ذخیره پایگاه داده در پوشه data
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
os.makedirs(DATA_DIR, exist_ok=True)
DB_NAME = os.path.join(DATA_DIR, "chat_history.db")

def init_db():
    """ساخت جدول پایگاه داده در اولین اجرای برنامه"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()

def save_message(session_id: str, role: str, content: str):
    """ذخیره یک پیام جدید (از طرف user یا assistant) در حافظه"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute(
        "INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
        (session_id, role, content)
    )
    
    conn.commit()
    conn.close()

def get_chat_history(session_id: str, limit: int = 10):
    """دریافت آخرین پیام‌های ردوبدل شده برای ارسال به هوش مصنوعی"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT role, content FROM (
            SELECT id, role, content FROM messages 
            WHERE session_id = ? 
            ORDER BY id DESC LIMIT ?
        ) ORDER BY id ASC
    """, (session_id, limit))
    
    rows = cursor.fetchall()
    conn.close()
    
    history = [{"role": row[0], "content": row[1]} for row in rows]
    return history

def clear_history(session_id: str):
    """پاک کردن حافظه یک گفتگوی خاص"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
    
    conn.commit()
    conn.close()

init_db()
