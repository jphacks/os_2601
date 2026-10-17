import logging
import secrets
import time
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Annotated, Literal, NoReturn

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.state import (
    Accepted,
    Advance,
    ChangeSettings,
    Check,
    CheckDone,
    CheckRequested,
    End,
    Event,
    Hint,
    HintIssued,
    HintRequested,
    LeakCheck,
    Problem,
    Rejected,
    Session,
    SessionSettings,
    Signal,
    Thresholds,
    Tick,
    cooldown_remaining,
    step,
    still_seconds,
)
from app.check import CORRECT_TEXT, Judgement, judge
from app.gemini import Gemini
from app.hints import compose_hint, fixed_hint
from app.store import SessionStore
from app.worksheets import PRINT_LAYOUT, Worksheet

logger = logging.getLogger(__name__)

MAX_FRAME_BYTES = 600 * 1024
MODE_DEFAULT = "live"


@dataclass
class AppContext:
    thresholds: Thresholds
    default_settings: SessionSettings
    worksheets: dict[str, Worksheet]
    store: SessionStore
    operator_key: str
    demo_mode: bool
    ai: Gemini | None
    hint_model: str
    check_model: str
    frames: dict[str, tuple[str, bytes]] = field(default_factory=dict)


StuckSeconds = Annotated[int, Field(ge=5, le=1200)]
CooldownSeconds = Annotated[int, Field(ge=0, le=300)]
MaxLevel = Annotated[int, Field(ge=1, le=2)]


class SettingsInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    stuck_seconds: StuckSeconds | None = None
    cooldown_seconds: CooldownSeconds | None = None
    max_level: MaxLevel | None = None


class SessionCreateRequest(BaseModel):
    worksheet_id: str
    learner_label: str = "学習者"
    mode: Literal["live", "scripted"]
    settings: SettingsInput = SettingsInput()


class SettingsPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    stuck_seconds: StuckSeconds | None = None
    cooldown_seconds: CooldownSeconds | None = None

    @model_validator(mode="after")
    def require_one(self) -> "SettingsPatch":
        if self.stuck_seconds is None and self.cooldown_seconds is None:
            raise ValueError("stuck_seconds か cooldown_seconds のどちらかが要る")
        return self


class SignalRequest(BaseModel):
    ts: datetime
    motion: float | None = Field(default=None, ge=0, le=1)
    camera_ok: bool | None = None
    force_stuck: bool = False

    @model_validator(mode="after")
    def require_camera_ok(self) -> "SignalRequest":
        if not self.force_stuck and self.camera_ok is None:
            raise ValueError("force_stuck でなければ camera_ok が要る")
        return self


class HintRequest(BaseModel):
    trigger: Literal["auto", "manual", "voice"]
    frame_id: str


class CheckRequest(BaseModel):
    frame_id: str


class AdvanceRequest(BaseModel):
    reason: Literal["skip"] = "skip"


router = APIRouter()


def get_context(request: Request) -> AppContext:
    return request.app.state.context


def _fail(status: int, message: str) -> NoReturn:
    raise HTTPException(status_code=status, detail=message)


def _now() -> datetime:
    return datetime.now(UTC)


def _iso(value: datetime | None) -> str | None:
    return value.isoformat(timespec="seconds").replace("+00:00", "Z") if value else None


def _new_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_urlsafe(12)}"


def _matches(given: str | None, expected: str) -> bool:
    return bool(given) and bool(expected) and secrets.compare_digest(given.encode(), expected.encode())


def _operator_ok(request: Request, context: AppContext) -> bool:
    return _matches(request.headers.get("X-Operator-Key"), context.operator_key)


def _device_ok(request: Request, session: Session) -> bool:
    scheme, _, token = request.headers.get("Authorization", "").partition(" ")
    return scheme.lower() == "bearer" and _matches(token, session.session_token)


def _require_operator(request: Request, context: AppContext) -> None:
    if not _operator_ok(request, context):
        _fail(401, "X-Operator-Key が無いか一致しない")


def _require_device(request: Request, context: AppContext, session: Session) -> None:
    if _device_ok(request, session):
        return
    if _operator_ok(request, context):
        _fail(403, "この操作はセッションのトークンでだけできる")
    _fail(401, "セッションのトークンが無いか一致しない")


def _require_device_or_operator(request: Request, context: AppContext, session: Session) -> None:
    if not (_device_ok(request, session) or _operator_ok(request, context)):
        _fail(401, "セッションのトークンかオペレータの鍵が要る")


def _latest_frame(context: AppContext, session_id: str) -> bytes | None:
    latest = context.frames.get(session_id)
    return latest[1] if latest else None


def _find_session(context: AppContext, session_id: str) -> Session:
    session = context.store.get(session_id)
    if session is None:
        _fail(404, f"セッション {session_id} が無い")
    return session


def _apply(context: AppContext, session: Session, event: Event, now: datetime) -> tuple[Session, Accepted]:
    next_session, result = step(session, event, now, context.thresholds)
    context.store.put(next_session)
    if next_session.state == "ended":
        context.frames.pop(next_session.session_id, None)
    if isinstance(result, Rejected):
        _fail(409, f"今の状態（{next_session.state}）では受理できない")
    return next_session, result


def _seconds_spent(problem: Problem, session: Session, now: datetime) -> int:
    if problem.started_at is None:
        return 0
    finished = problem.finished_at or session.ended_at or now
    return int((finished - problem.started_at).total_seconds())


def _hint_record(hint: Hint) -> dict:
    return {
        "hint_id": hint.hint_id,
        "level": hint.level,
        "trigger": hint.trigger,
        "display": hint.display,
        "stuck_point": hint.stuck_point,
        "source": hint.source,
        "leak_check": asdict(hint.leak_check),
        "latency_ms": hint.latency_ms,
        "created_at": _iso(hint.created_at),
    }


def _problem_record(problem: Problem, session: Session, now: datetime) -> dict:
    check = problem.check
    return {
        "problem_no": problem.problem_no,
        "status": problem.status,
        "stuck_count": problem.stuck_count,
        "max_level": max((hint.level for hint in problem.hints), default=0),
        "seconds_spent": _seconds_spent(problem, session, now),
        "hints": [_hint_record(hint) for hint in problem.hints],
        "check": {"verdict": check.verdict, "display": check.display, "created_at": _iso(check.created_at)} if check else None,
    }


def _stuck_points(session: Session) -> list[dict]:
    counts: dict[str, int] = {}
    for problem in session.problems:
        for hint in problem.hints:
            counts[hint.stuck_point] = counts.get(hint.stuck_point, 0) + 1
    return [{"label": label, "count": count} for label, count in sorted(counts.items(), key=lambda item: -item[1])]


@router.post("/sessions", status_code=201)
async def create_session(
    body: SessionCreateRequest, request: Request, context: AppContext = Depends(get_context)
) -> dict:
    _require_operator(request, context)
    worksheet = context.worksheets.get(body.worksheet_id)
    if worksheet is None:
        _fail(422, f"ワークシート {body.worksheet_id} が無い")
    now = _now()
    settings = SessionSettings(**{**asdict(context.default_settings), **body.settings.model_dump(exclude_none=True)})
    problems = [Problem(problem_no=problem_no) for problem_no in range(1, worksheet.problem_count + 1)]
    problems[0].status = "working"
    problems[0].started_at = now
    session = Session(
        session_id=_new_id("ses"),
        session_token=_new_id("tok"),
        worksheet_id=worksheet.worksheet_id,
        learner_label=body.learner_label,
        mode=body.mode,
        settings=settings,
        problems=problems,
        created_at=now,
    )
    context.store.put(session)
    context.store.save()
    return {
        "session_id": session.session_id,
        "session_token": session.session_token,
        "mode": session.mode,
        "state": session.state,
        "worksheet": {"worksheet_id": worksheet.worksheet_id, "title": worksheet.title, "problem_count": len(problems)},
        "settings": asdict(session.settings),
        "created_at": _iso(session.created_at),
    }


@router.get("/sessions")
async def list_sessions(request: Request, context: AppContext = Depends(get_context)) -> dict:
    _require_operator(request, context)
    now = _now()
    sessions = [_apply(context, session, Tick(), now)[0] for session in context.store.all()]
    sessions.sort(key=lambda session: session.created_at, reverse=True)
    return {
        "sessions": [
            {
                "session_id": session.session_id,
                "worksheet_id": session.worksheet_id,
                "learner_label": session.learner_label,
                "mode": session.mode,
                "state": session.state,
                "problem_done": sum(problem.status == "done" for problem in session.problems),
                "problem_count": len(session.problems),
                "stuck_total": sum(problem.stuck_count for problem in session.problems),
                "created_at": _iso(session.created_at),
                "ended_at": _iso(session.ended_at),
            }
            for session in sessions
        ]
    }


@router.get("/sessions/{session_id}")
async def get_session(session_id: str, request: Request, context: AppContext = Depends(get_context)) -> dict:
    session = _find_session(context, session_id)
    _require_device_or_operator(request, context, session)
    now = _now()
    session, _ = _apply(context, session, Tick(), now)
    worksheet = context.worksheets[session.worksheet_id]
    return {
        "session_id": session.session_id,
        "worksheet_id": session.worksheet_id,
        "worksheet_title": worksheet.title,
        "problem_count": len(session.problems),
        "learner_label": session.learner_label,
        "mode": session.mode,
        "state": session.state,
        "current_problem_no": session.current_problem_no,
        "still_seconds": still_seconds(session, now),
        "settings": asdict(session.settings),
        "problems": [_problem_record(problem, session, now) for problem in session.problems],
        "stuck_points": _stuck_points(session),
        "leak_blocked_count": session.leak_blocked_count,
        "created_at": _iso(session.created_at),
        "ended_at": _iso(session.ended_at),
    }


@router.patch("/sessions/{session_id}/settings")
async def patch_settings(
    session_id: str, body: SettingsPatch, request: Request, context: AppContext = Depends(get_context)
) -> dict:
    session = _find_session(context, session_id)
    _require_device(request, context, session)
    session, _ = _apply(context, session, ChangeSettings(body.stuck_seconds, body.cooldown_seconds), _now())
    context.store.save()
    return {"settings": asdict(session.settings), "state": session.state}


@router.post("/sessions/{session_id}/signals")
async def post_signal(
    session_id: str, body: SignalRequest, request: Request, context: AppContext = Depends(get_context)
) -> dict:
    session = _find_session(context, session_id)
    if body.force_stuck:
        _require_device_or_operator(request, context, session)
    else:
        _require_device(request, context, session)
    now = _now()
    event = Signal(motion=body.motion, camera_ok=bool(body.camera_ok), force_stuck=body.force_stuck)
    session, result = _apply(context, session, event, now)
    logger.info(
        "signal session=%s motion=%s camera_ok=%s force_stuck=%s state=%s",
        session.session_id,
        body.motion,
        body.camera_ok,
        body.force_stuck,
        session.state,
    )
    return {
        "state": session.state,
        "still_seconds": still_seconds(session, now),
        "current_problem_no": session.current_problem_no,
        "next_action": result.next_action,
        "cooldown_remaining": cooldown_remaining(session, now),
    }


@router.post("/sessions/{session_id}/frames")
async def post_frame(
    session_id: str, request: Request, frame: UploadFile = File(...), context: AppContext = Depends(get_context)
) -> dict:
    session = _find_session(context, session_id)
    _require_device(request, context, session)
    if session.state == "ended":
        _fail(409, "終了したセッションにはフレームを送れない")
    data = await frame.read(MAX_FRAME_BYTES + 1)
    if len(data) > MAX_FRAME_BYTES:
        _fail(413, f"フレームは {MAX_FRAME_BYTES // 1024} KB まで")
    frame_id = _new_id("frm")
    context.frames[session.session_id] = (frame_id, data)
    return {"frame_id": frame_id, "received_at": _iso(_now()), "bytes": len(data)}


@router.post("/sessions/{session_id}/hints")
async def request_hint(
    session_id: str, body: HintRequest, request: Request, context: AppContext = Depends(get_context)
) -> dict:
    session = _find_session(context, session_id)
    _require_device(request, context, session)
    started = time.monotonic()
    now = _now()
    session, accepted = _apply(context, session, HintRequested(body.trigger), now)
    problem_no = session.current_problem_no
    problem = session.current_problem
    if session.mode == "scripted":
        composed = fixed_hint(accepted.level, "scripted", LeakCheck(ok=True, fallback=False), problem.leak_strings)
    else:
        composed = await compose_hint(
            context.ai,
            context.hint_model,
            _latest_frame(context, session_id),
            accepted.level,
            [hint.display for hint in problem.hints],
            problem.problem_text,
            problem.leak_strings,
        )
    session, _ = _apply(context, _find_session(context, session_id), HintIssued(len(composed.speech)), _now())
    hint = Hint(
        hint_id=_new_id("hnt"),
        level=accepted.level,
        trigger=body.trigger,
        speech=composed.speech,
        display=composed.display,
        stuck_point=composed.stuck_point,
        source=composed.source,
        leak_check=composed.leak_check,
        model=composed.model,
        latency_ms=int((time.monotonic() - started) * 1000),
        created_at=now,
    )
    recorded = session.problems[problem_no - 1]
    recorded.hints.append(hint)
    recorded.problem_text = composed.problem_text or recorded.problem_text
    recorded.answer = composed.final_answer or recorded.answer
    recorded.leak_strings = composed.leak_strings
    if not composed.leak_check.ok:
        session.leak_blocked_count += 1
    context.store.put(session)
    context.store.save()
    return {
        "hint_id": hint.hint_id,
        "problem_no": problem_no,
        "level": hint.level,
        "trigger": hint.trigger,
        "speech": hint.speech,
        "display": hint.display,
        "stuck_point": hint.stuck_point,
        "leak_check": asdict(hint.leak_check),
        "source": hint.source,
        **({"model": hint.model} if hint.model else {}),
        "latency_ms": hint.latency_ms,
        "state": session.state,
    }


@router.post("/sessions/{session_id}/check")
async def post_check(
    session_id: str, body: CheckRequest, request: Request, context: AppContext = Depends(get_context)
) -> dict:
    session = _find_session(context, session_id)
    _require_device(request, context, session)
    now = _now()
    session, _ = _apply(context, session, CheckRequested(), now)
    checked_no = session.current_problem_no
    problem = session.current_problem
    if session.mode == "scripted":
        judgement = Judgement("correct", CORRECT_TEXT)
    else:
        judgement = await judge(
            context.ai, context.check_model, _latest_frame(context, session_id), problem.problem_text, problem.answer
        )
    session, _ = _apply(
        context, _find_session(context, session_id), CheckDone(judgement.verdict, len(judgement.speech)), _now()
    )
    check = Check(
        check_id=_new_id("chk"),
        verdict=judgement.verdict,
        speech=judgement.speech,
        display=judgement.speech,
        created_at=now,
    )
    session.problems[checked_no - 1].check = check
    context.store.put(session)
    context.store.save()
    return {
        "check_id": check.check_id,
        "problem_no": checked_no,
        "verdict": check.verdict,
        "speech": check.speech,
        "display": check.display,
        "next_problem_no": None if session.state == "ended" else session.current_problem_no,
        "state": session.state,
    }


@router.post("/sessions/{session_id}/advance")
async def post_advance(
    session_id: str, request: Request, body: AdvanceRequest | None = None, context: AppContext = Depends(get_context)
) -> dict:
    session = _find_session(context, session_id)
    _require_device(request, context, session)
    session, _ = _apply(context, session, Advance(), _now())
    context.store.save()
    return {"current_problem_no": session.current_problem_no, "state": session.state}


@router.post("/sessions/{session_id}/end")
async def post_end(session_id: str, request: Request, context: AppContext = Depends(get_context)) -> dict:
    session = _find_session(context, session_id)
    _require_device_or_operator(request, context, session)
    session, _ = _apply(context, session, End(), _now())
    context.store.save()
    return {"state": session.state, "ended_at": _iso(session.ended_at)}


@router.get("/worksheets")
async def list_worksheets(context: AppContext = Depends(get_context)) -> dict:
    return {
        "worksheets": [
            {
                "worksheet_id": worksheet.worksheet_id,
                "title": worksheet.title,
                "problem_count": worksheet.problem_count,
                "grade": worksheet.grade,
            }
            for worksheet in context.worksheets.values()
        ]
    }


@router.get("/worksheets/{worksheet_id}")
async def get_worksheet(worksheet_id: str, context: AppContext = Depends(get_context)) -> dict:
    worksheet = context.worksheets.get(worksheet_id)
    if worksheet is None:
        _fail(404, f"ワークシート {worksheet_id} が無い")
    return {
        "worksheet_id": worksheet.worksheet_id,
        "title": worksheet.title,
        "grade": worksheet.grade,
        "problems": [],
        "print": PRINT_LAYOUT,
    }


@router.post("/demo/reset")
async def demo_reset(request: Request, context: AppContext = Depends(get_context)) -> dict:
    _require_operator(request, context)
    if not context.demo_mode:
        _fail(404, "DEMO_MODE が 1 でない")
    removed = context.store.clear()
    context.frames.clear()
    context.store.save()
    return {"ok": True, "removed_sessions": removed}


@router.get("/healthz")
async def healthz(context: AppContext = Depends(get_context)) -> dict:
    return {
        "ok": True,
        "gpt": "ok" if context.ai else "missing",
        "worksheets": len(context.worksheets),
        "mode_default": MODE_DEFAULT,
    }
