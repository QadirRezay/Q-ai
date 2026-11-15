from __future__ import annotations

import asyncio
import logging
import os
import re
import time
import uuid
from collections import defaultdict, deque
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from typing import Annotated, Protocol

from fastapi import FastAPI, HTTPException, Request, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator
from fpdf import FPDF

# توابع فعلی شما — بعداً می‌توانیم جایگزین کنیم بدون دست زدن به endpointها
from ai_engine import generate_code_response
from database import get_chat_history, clear_history


# ============================================================
# 1) Logging
# ============================================================
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
logger = logging.getLogger("coding_ai")


# ============================================================
# 2) Settings (env-based)
# ============================================================
EXPORT_DIR = Path(os.getenv("EXPORT_DIR", "exports"))
EXPORT_TTL_SECONDS = int(os.getenv("EXPORT_TTL_SECONDS", "3600"))
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "30"))
MAX_PROMPT_CHARS = int(os.getenv("MAX_PROMPT_CHARS", "8000"))
AI_TIMEOUT_SECONDS = float(os.getenv("AI_TIMEOUT_SECONDS", "90"))

ALLOWED_LANGUAGES = {
    "python", "javascript", "typescript", "java", "go", "rust",
    "c", "cpp", "csharp", "php", "ruby", "kotlin", "swift", "sql",
    "html", "css", "bash",
}

ALLOWED_ORIGINS = ["http://127.0.0.1:5501", "http://localhost:5501", "http://127.0.0.1:5500"]

_SESSION_ID_RE = re.compile(r"^[A-Za-z0-9_\-]{1,64}$")


# ============================================================
# 3) Protocols (قراردادها) — برای DI
# ============================================================
class AIEngineProtocol(Protocol):
    async def generate(self, session_id: str, prompt: str, language: str) -> str: ...


class DatabaseProtocol(Protocol):
    async def history(self, session_id: str, limit: int) -> list: ...
    async def clear(self, session_id: str) -> None: ...


# ============================================================
# 4) Adapterها — پل به توابع فعلی (فعلاً sync)
# ============================================================
class LegacyAIEngine:
    """فعلاً generate_code_response را در thread اجرا می‌کند."""

    async def generate(self, session_id: str, prompt: str, language: str) -> str:
        return await asyncio.to_thread(
            generate_code_response,
            session_id=session_id,
            user_prompt=prompt,
            language=language,
        )


class LegacyDatabase:
    """فعلاً get_chat_history/clear_history را در thread اجرا می‌کند."""

    async def history(self, session_id: str, limit: int) -> list:
        return await asyncio.to_thread(
            get_chat_history, session_id=session_id, limit=limit
        )

    async def clear(self, session_id: str) -> None:
        await asyncio.to_thread(clear_history, session_id)


# ============================================================
# 5) Schemas
# ============================================================
class ChatRequest(BaseModel):
    session_id: str = Field(default="default_user", max_length=64)
    prompt: str = Field(min_length=1)
    language: str = Field(default="Python", max_length=32)

    @field_validator("session_id")
    @classmethod
    def _check_sid(cls, v: str) -> str:
        if not _SESSION_ID_RE.match(v):
            raise ValueError("session_id must be 1-64 chars: A-Z a-z 0-9 _ -")
        return v

    @field_validator("prompt")
    @classmethod
    def _check_prompt(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("prompt is empty")
        if len(v) > MAX_PROMPT_CHARS:
            raise ValueError(f"prompt too long (max {MAX_PROMPT_CHARS})")
        return v

    @field_validator("language")
    @classmethod
    def _check_lang(cls, v: str) -> str:
        if v.lower() not in ALLOWED_LANGUAGES:
            raise ValueError(f"unsupported language: {v}")
        return v


class ExportRequest(BaseModel):
    session_id: str = Field(default="default_user", max_length=64)
    code: str = Field(min_length=1)
    filename: str | None = Field(default=None, max_length=80)

    @field_validator("session_id")
    @classmethod
    def _check_sid(cls, v: str) -> str:
        if not _SESSION_ID_RE.match(v):
            raise ValueError("invalid session_id")
        return v


# ============================================================
# 6) Rate limiter (in-memory)
# ============================================================
class RateLimiter:
    def __init__(self, per_minute: int):
        self.per_minute = per_minute
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        q = self._hits[key]
        while q and now - q[0] > 60.0:
            q.popleft()
        if len(q) >= self.per_minute:
            return False
        q.append(now)
        return True


# ============================================================
# 7) Helpers
# ============================================================
def extract_pure_code(markdown_text: str) -> str:
    blocks = re.findall(r"```(?:\w+)?\n(.*?)```", markdown_text, re.DOTALL)
    if blocks:
        return "\n\n# -----------------------------------\n\n".join(b.strip() for b in blocks)
    return markdown_text.strip()


def _safe_filename(name: str, default: str) -> str:
    name = os.path.basename(name)
    name = re.sub(r"[^A-Za-z0-9._-]", "_", name)
    return name or default


def _write_txt(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def _write_pdf(path: Path, code: str) -> None:
    pdf = FPDF()
    pdf.add_page()
    unicode_font = Path("assets/DejaVuSansMono.ttf")
    if unicode_font.exists():
        pdf.add_font("Mono", "", str(unicode_font))
        pdf.set_font("Mono", size=9)
        for line in code.splitlines() or [""]:
            pdf.multi_cell(0, 5, line)
    else:
        pdf.set_font("Courier", size=9)
        for line in code.splitlines() or [""]:
            safe = line.encode("latin-1", "replace").decode("latin-1")
            pdf.multi_cell(0, 5, safe)
    pdf.output(str(path))


async def _cleanup_old_exports() -> None:
    while True:
        await asyncio.sleep(max(EXPORT_TTL_SECONDS // 2, 60))
        now = time.time()
        try:
            for f in EXPORT_DIR.iterdir():
                if f.is_file() and (now - f.stat().st_mtime) > EXPORT_TTL_SECONDS:
                    with suppress(OSError):
                        f.unlink()
        except FileNotFoundError:
            return


# ============================================================
# 8) Lifespan — ساخت منابع در startup
# ============================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    app.state.ai = LegacyAIEngine()        # ← بعداً AIEngine(settings)
    app.state.db = LegacyDatabase()        # ← بعداً ChatRepository(...)
    app.state.rate = RateLimiter(RATE_LIMIT_PER_MINUTE)
    cleanup_task = asyncio.create_task(_cleanup_old_exports())
    logger.info(
        "AI server ready | exports=%s ttl=%ss rate=%s/min",
        EXPORT_DIR, EXPORT_TTL_SECONDS, RATE_LIMIT_PER_MINUTE,
    )
    try:
        yield
    finally:
        cleanup_task.cancel()
        with suppress(asyncio.CancelledError):
            await cleanup_task
        close = getattr(app.state.db, "close", None)
        if callable(close):
            await close()
        logger.info("AI server shutdown")


# ============================================================
# 9) App + middleware
# ============================================================
app = FastAPI(
    title="Coding AI Server",
    version="1.2.0",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Request-ID"],
    expose_headers=["X-Request-ID", "X-Duration-Ms"],
    max_age=600,
)


@app.middleware("http")
async def request_context(request: Request, call_next):
    rid = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("unhandled rid=%s path=%s", rid, request.url.path)
        raise
    response.headers["x-request-id"] = rid
    response.headers["x-duration-ms"] = f"{(time.perf_counter() - start) * 1000:.1f}"
    return response


# ============================================================
# 10) Dependencies
# ============================================================
def get_ai(request: Request) -> AIEngineProtocol:
    return request.app.state.ai


def get_db(request: Request) -> DatabaseProtocol:
    return request.app.state.db


async def rate_limit_dep(request: Request) -> None:
    client = request.client.host if request.client else "unknown"
    if not request.app.state.rate.allow(client):
        logger.warning("rate limit hit by %s", client)
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many requests")


AI = Annotated[AIEngineProtocol, Depends(get_ai)]
DB = Annotated[DatabaseProtocol, Depends(get_db)]
RateLimited = Annotated[None, Depends(rate_limit_dep)]


# ============================================================
# 11) Routes
# ============================================================
@app.post("/chat")
async def chat_with_ai(req: ChatRequest, ai: AI, _: RateLimited):
    try:
        ai_reply = await asyncio.wait_for(
            ai.generate(
                session_id=req.session_id,
                prompt=req.prompt,
                language=req.language,
            ),
            timeout=AI_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        logger.warning("AI timeout sid=%s", req.session_id)
        raise HTTPException(status.HTTP_504_GATEWAY_TIMEOUT, "AI provider timeout")
    except Exception:
        logger.exception("AI failure sid=%s", req.session_id)
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "AI provider error")

    return {
        "status": "success",
        "full_response": ai_reply,
        "pure_code": extract_pure_code(ai_reply),
    }


@app.get("/history/{session_id}")
async def fetch_history(session_id: str, db: DB):
    if not _SESSION_ID_RE.match(session_id):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "invalid session_id")
    try:
        history = await db.history(session_id=session_id, limit=50)
        return {"status": "success", "history": history}
    except Exception:
        logger.exception("history failure sid=%s", session_id)
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "history error")


@app.post("/export/notepad")
async def export_as_notepad(req: ExportRequest, _: RateLimited):
    fname = _safe_filename(req.filename or "generated_code.txt", "generated_code.txt")
    if not fname.lower().endswith(".txt"):
        fname += ".txt"
    path = EXPORT_DIR / f"{req.session_id}_{uuid.uuid4().hex[:8]}_{fname}"
    await asyncio.to_thread(_write_txt, path, req.code)
    return FileResponse(path, filename=fname, media_type="text/plain; charset=utf-8")


@app.post("/export/pdf")
async def export_as_pdf(req: ExportRequest, _: RateLimited):
    fname = _safe_filename(req.filename or "generated_code.pdf", "generated_code.pdf")
    if not fname.lower().endswith(".pdf"):
        fname += ".pdf"
    path = EXPORT_DIR / f"{req.session_id}_{uuid.uuid4().hex[:8]}_{fname}"
    await asyncio.to_thread(_write_pdf, path, req.code)
    return FileResponse(path, filename=fname, media_type="application/pdf")


@app.delete("/clear/{session_id}")
async def reset_memory(session_id: str, db: DB):
    if not _SESSION_ID_RE.match(session_id):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "invalid session_id")
    await db.clear(session_id)
    return {"status": "cleared", "message": "حافظه گفتگو پاک شد."}
# Mounting Frontend (Serving HTML/CSS/JS)
import os
from fastapi.staticfiles import StaticFiles

frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
