import re
import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fpdf import FPDF

from app.ai_engine import generate_code_response
from app.database import clear_history, get_chat_history

app = FastAPI(title="Coding AI Server with Export")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
EXPORT_DIR = os.path.join(BASE_DIR, "exports")
os.makedirs(EXPORT_DIR, exist_ok=True)

class CodeRequest(BaseModel):
    session_id: str = "default_user"
    prompt: str
    language: str = "Python"

def extract_pure_code(markdown_text: str) -> str:
    """استخراج کد خالص از داخل بلوک‌های Markdown"""
    code_blocks = re.findall(r"```(?:\w+)?\n(.*?)```", markdown_text, re.DOTALL)
    if code_blocks:
        return "\n\n# -----------------------------------\n\n".join(code_blocks).strip()
    return markdown_text.strip()

@app.post("/chat")
async def chat_with_ai(request: CodeRequest):
    """مسیر اصلی گفتگو و دریافت کد همراه با توضیحات"""
    try:
        ai_reply = generate_code_response(
            session_id=request.session_id,
            user_prompt=request.prompt,
            language=request.language
        )
        pure_code = extract_pure_code(ai_reply)
        
        return {
            "status": "success",
            "full_response": ai_reply,
            "pure_code": pure_code
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/history/{session_id}")
async def fetch_history(session_id: str):
    """دریافت تاریخچه گفتگوها برای نمایش در رابط کاربری"""
    history = get_chat_history(session_id=session_id, limit=50)
    return {"status": "success", "history": history}

@app.post("/export/notepad")
async def export_as_notepad(request: CodeRequest):
    """تولید کد و تحویل به‌صورت فایل متنی آماده برای نوت‌پد (.txt)"""
    try:
        ai_reply = generate_code_response(request.session_id, request.prompt, request.language)
        pure_code = extract_pure_code(ai_reply)
        
        file_path = os.path.join(EXPORT_DIR, f"code_{request.session_id}.txt")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(pure_code)
            
        return FileResponse(
            path=file_path,
            filename="generated_code.txt",
            media_type="text/plain"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/export/pdf")
async def export_as_pdf(request: CodeRequest):
    """تولید کد و تحویل به‌صورت فایل PDF استاندارد"""
    try:
        ai_reply = generate_code_response(request.session_id, request.prompt, request.language)
        pure_code = extract_pure_code(ai_reply)
        
        file_path = os.path.join(EXPORT_DIR, f"code_{request.session_id}.pdf")
        
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Courier", size=10)
        
        for line in pure_code.splitlines():
            safe_line = line.encode("latin-1", "replace").decode("latin-1")
            pdf.cell(0, 6, txt=safe_line, ln=True)
            
        pdf.output(file_path)
        
        return FileResponse(
            path=file_path,
            filename="generated_code.pdf",
            media_type="application/pdf"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/clear/{session_id}")
async def reset_memory(session_id: str):
    """پاک کردن حافظه گفتگو"""
    clear_history(session_id)
    return {"status": "cleared", "message": "حافظه گفتگو پاک شد."}
