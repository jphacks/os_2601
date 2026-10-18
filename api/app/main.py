import logging
import os
from pathlib import Path

import yaml
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.gemini import Gemini
from app.routes import AppContext, router
from app.state import SessionSettings, Thresholds
from app.store import SessionStore
from app.voicevox import Voicevox
from app.worksheets import FREE_WORKSHEET

SETTINGS_PATH = Path(__file__).resolve().parents[1] / "settings.yaml"
DEFAULT_DATA_PATH = "./data/tonari.json"
DEFAULT_MODEL = "gemini-3.5-flash-lite"
DEFAULT_CORS_ORIGIN_REGEX = r"https://.*\.vercel\.app|https://.*\.trycloudflare\.com"
ERROR_CODES = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    409: "STATE_CONFLICT",
    413: "FRAME_TOO_LARGE",
    422: "VALIDATION_ERROR",
    503: "HINT_UNAVAILABLE",
}


def _error(status: int, message: str) -> JSONResponse:
    code = ERROR_CODES.get(status, "BAD_REQUEST")
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}})


def _build_context() -> AppContext:
    settings = yaml.safe_load(SETTINGS_PATH.read_text(encoding="utf-8"))
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
        worksheets={FREE_WORKSHEET.worksheet_id: FREE_WORKSHEET},
        store=SessionStore(Path(os.environ.get("DATA_PATH", DEFAULT_DATA_PATH))),
        operator_key=os.environ.get("OPERATOR_KEY", ""),
        demo_mode=os.environ.get("DEMO_MODE") == "1",
        ai=Gemini(api_key) if (api_key := os.environ.get("GEMINI_API_KEY")) else None,
        hint_model=os.environ.get("HINT_MODEL", DEFAULT_MODEL),
        check_model=os.environ.get("CHECK_MODEL", DEFAULT_MODEL),
        voice=Voicevox(voicevox_url) if (voicevox_url := os.environ.get("VOICEVOX_URL")) else None,
    )
    context.store.load()
    return context


def create_app() -> FastAPI:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    app = FastAPI(title="となり API")
    app.state.context = _build_context()
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
