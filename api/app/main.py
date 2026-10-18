import logging
import os
from pathlib import Path

import yaml
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.context import AppContext
from app.gemini import Gemini
from app.hints import FALLBACK_HINTS
from app.routes import MAX_FRAME_BYTES, router
from app.state import SessionSettings, Thresholds
from app.store import SessionStore
from app.voicevox import Voicevox

SETTINGS_PATH = Path(__file__).resolve().parents[1] / "settings.yaml"
DEFAULT_DATA_PATH = "./data/tonari.json"
DEFAULT_MODEL = "gemini-3.5-flash-lite"
MULTIPART_OVERHEAD_BYTES = 16 * 1024
DEFAULT_CORS_ORIGIN_REGEX = r"https://.*\.vercel\.app|https://.*\.trycloudflare\.com"
ERROR_CODES = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    409: "STATE_CONFLICT",
    413: "FRAME_TOO_LARGE",
    422: "VALIDATION_ERROR",
    429: "RATE_LIMITED",
    503: "HINT_UNAVAILABLE",
}


def _error(status: int, message: str) -> JSONResponse:
    code = ERROR_CODES.get(status, "BAD_REQUEST")
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}})


def _build_context() -> AppContext:
    settings = yaml.safe_load(SETTINGS_PATH.read_text(encoding="utf-8"))
    if settings["max_level"] not in FALLBACK_HINTS:
        raise ValueError(f"max_level は {sorted(FALLBACK_HINTS)} のどれか")
    context = AppContext(
        thresholds=Thresholds(
            motion_threshold=settings["motion_threshold"],
            motion_exit_threshold=settings["motion_exit_threshold"],
            signal_timeout_seconds=settings["signal_timeout_seconds"],
            prefetch_lead_seconds=settings["prefetch_lead_seconds"],
            speech_seconds_per_char=settings["speech_seconds_per_char"],
            speech_seconds_base=settings["speech_seconds_base"],
        ),
        default_settings=SessionSettings(
            stuck_seconds=settings["stuck_seconds"],
            cooldown_seconds=settings["cooldown_seconds"],
            max_level=settings["max_level"],
        ),
        store=SessionStore(Path(os.environ.get("DATA_PATH", DEFAULT_DATA_PATH))),
        operator_key=os.environ.get("OPERATOR_KEY", ""),
        demo_mode=os.environ.get("DEMO_MODE") == "1",
        open_sessions=os.environ.get("OPEN_SESSIONS", "1") == "1",
        ai=Gemini(api_key) if (api_key := os.environ.get("GEMINI_API_KEY")) else None,
        hint_model=os.environ.get("HINT_MODEL", DEFAULT_MODEL),
        check_model=os.environ.get("CHECK_MODEL", DEFAULT_MODEL),
        voice=Voicevox(voicevox_url) if (voicevox_url := os.environ.get("VOICEVOX_URL")) else None,
    )
    context.store.load()
    return context


def create_app() -> FastAPI:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    app = FastAPI(title="となり API")
    app.state.context = _build_context()
    @app.middleware("http")
    async def refuse_large_frames(request: Request, call_next):
        if request.method == "POST" and request.url.path.endswith("/frames"):
            length = request.headers.get("content-length")
            if length is not None and length.isdigit() and int(length) > MAX_FRAME_BYTES + MULTIPART_OVERHEAD_BYTES:
                return _error(413, f"フレームは {MAX_FRAME_BYTES // 1024} KB まで")
        return await call_next(request)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[origin.strip() for origin in os.environ.get("CORS_ORIGINS", "").split(",") if origin.strip()],
        allow_origin_regex=os.environ.get("CORS_ORIGIN_REGEX", DEFAULT_CORS_ORIGIN_REGEX),
        allow_methods=["*"],
        allow_headers=["Authorization", "X-Operator-Key", "Content-Type"],
    )
    app.include_router(router)


    @app.exception_handler(HTTPException)
    async def http_error(_: Request, error: HTTPException) -> JSONResponse:
        return _error(error.status_code, str(error.detail))

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, error: RequestValidationError) -> JSONResponse:
        problems = error.errors()
        status = 400 if any(problem.get("type") == "json_invalid" for problem in problems) else 422
        message = "; ".join(f"{'.'.join(map(str, problem['loc']))}: {problem['msg']}" for problem in problems)
        return _error(status, message)

    return app


app = create_app()
