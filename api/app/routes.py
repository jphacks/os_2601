import logging
import secrets
import time
from dataclasses import asdict, replace
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, File, Request, Response, UploadFile

from app.auth import require_device, require_device_or_operator, require_operator
from app.check import CORRECT_TEXT, Judgement, judge
from app.composer import answer, compose
from app.context import AppContext, get_context
from app.errors import fail
from app.gemini import AIUnavailable
from app.hints import (
    FALLBACK_HINTS,
    ComposedHint,
    answer_fallback,
    asks_for_help,
    asks_if_correct,
    check_reply,
    fixed_hint,
    read_problem,
)
from app.leak import same_problem
from app.limits import AI_CALLS_PER_MINUTE, MAX_FRAME_BYTES, SPEECHES_PER_MINUTE, allow_open, client_ip, count_call, one_at_a_time
from app.personas import persona_options
from app.prefetch import discard_prefetch, settle_prefetch, start_prefetch, take_prefetch
from app.schemas import CheckRequest, HintRequest, ProblemRequest, SessionCreateRequest, SettingsPatch, SignalRequest, SpeechRequest
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
    HintAbandoned,
    HintIssued,
    HintRequested,
    LeakCheck,
    Mode,
    Problem,
    Rejected,
    Session,
    SessionSettings,
    Signal,
    Tick,
    cooldown_remaining,
    step,
    still_seconds,
)
from app.views import iso, problem_record, stuck_points
from app.voicevox import VoiceUnavailable

logger = logging.getLogger(__name__)

OPEN_SESSION_LIFETIME = timedelta(minutes=30)
OPEN_SESSION_KEPT_FOR = timedelta(hours=2)
OPEN_SESSION_LABEL = "自分で始めた"
SPEECH_AFTER_END_SECONDS = 60
MODE_DEFAULT = "live"
WORKSHEET_ID = "FREE"
WORKSHEET_TITLE = "自由な問題"
PROBLEM_SLOTS = 20


router = APIRouter()


def _now() -> datetime:
    return datetime.now(UTC)


def _new_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_urlsafe(12)}"


def _latest_frame(context: AppContext, session_id: str) -> bytes | None:
    latest = context.frames.get(session_id)
    return latest[1] if latest else None


def _abandon_hint(context: AppContext, session_id: str, ticket: datetime) -> None:
    session = context.store.get(session_id)
    if session is not None:
        _apply(context, session, HintAbandoned(ticket), _now())
        context.store.save()


def _find_session(context: AppContext, session_id: str) -> Session:
    session = context.store.get(session_id)
    if session is None:
        fail(404, f"セッション {session_id} が無い")
    return session


def _count_ai_call(context: AppContext, session_id: str, frame: bytes | None, now: datetime) -> None:
    if context.ai is not None and frame is not None:
        count_call(context.ai_calls, session_id, AI_CALLS_PER_MINUTE, now)


def _forget_old_open_sessions(context: AppContext, now: datetime) -> None:
    for session in context.store.all():
        if session.auto_end_at is None:
            continue
        finished_at = session.ended_at or session.auto_end_at
        if now - finished_at > OPEN_SESSION_KEPT_FOR:
            context.store.remove(session.session_id)
        if session.ended_at is not None or now >= session.auto_end_at:
            context.frames.pop(session.session_id, None)
            discard_prefetch(context, session.session_id)
    alive = {session.session_id for session in context.store.all()}
    for calls in (context.frames, context.ai_calls, context.speeches):
        for session_id in [session_id for session_id in calls if session_id not in alive]:
            del calls[session_id]


def _apply(context: AppContext, session: Session, event: Event, now: datetime) -> tuple[Session, Accepted]:
    next_session, result = step(session, event, now, context.thresholds)
    if next_session is not session:
        context.store.put(next_session)
    settle_prefetch(context, next_session)
    if next_session.state == "ended":
        context.frames.pop(next_session.session_id, None)
    if isinstance(result, Rejected):
        fail(409, f"今の状態（{next_session.state}）では受理できない")
    return next_session, result


def _new_session(
    context: AppContext, learner_label: str, mode: Mode, settings: SessionSettings, auto_end_at: datetime | None
) -> dict:
    now = _now()
    problems = [Problem(problem_no=problem_no) for problem_no in range(1, PROBLEM_SLOTS + 1)]
    problems[0].status = "working"
    problems[0].started_at = now
    session = Session(
        session_id=_new_id("ses"),
        session_token=_new_id("tok"),
        worksheet_id=WORKSHEET_ID,
        learner_label=learner_label,
        mode=mode,
        settings=settings,
        problems=problems,
        created_at=now,
        auto_end_at=auto_end_at,
    )
    context.store.put(session)
    context.store.save()
    return {
        "session_id": session.session_id,
        "session_token": session.session_token,
        "mode": session.mode,
        "state": session.state,
        "worksheet": {"worksheet_id": WORKSHEET_ID, "title": WORKSHEET_TITLE, "problem_count": len(problems)},
        "settings": asdict(session.settings),
        "created_at": iso(session.created_at),
    }


@router.post("/sessions", status_code=201)
async def create_session(
    body: SessionCreateRequest, request: Request, context: AppContext = Depends(get_context)
) -> dict:
    require_operator(request, context)
    settings = SessionSettings(**{**asdict(context.default_settings), **body.settings.model_dump(exclude_none=True)})
    return _new_session(context, body.learner_label, body.mode, settings, None)


@router.post("/sessions/open", status_code=201)
async def open_session(request: Request, context: AppContext = Depends(get_context)) -> dict:
    if not context.open_sessions:
        fail(404, "OPEN_SESSIONS が 0")
    now = _now()
    if not allow_open(context, client_ip(request), now):
        fail(429, "少し待ってから、もう一度開いてね")
    _forget_old_open_sessions(context, now)
    settings = replace(context.default_settings)
    return _new_session(context, OPEN_SESSION_LABEL, "live", settings, now + OPEN_SESSION_LIFETIME)


@router.get("/sessions")
async def list_sessions(request: Request, context: AppContext = Depends(get_context)) -> dict:
    require_operator(request, context)
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
                "created_at": iso(session.created_at),
                "ended_at": iso(session.ended_at),
            }
            for session in sessions
        ]
    }


@router.get("/sessions/{session_id}")
async def get_session(session_id: str, request: Request, context: AppContext = Depends(get_context)) -> dict:
    session = _find_session(context, session_id)
    require_device_or_operator(request, context, session)
    now = _now()
    session, _ = _apply(context, session, Tick(), now)
    return {
        "session_id": session.session_id,
        "worksheet_id": session.worksheet_id,
        "worksheet_title": WORKSHEET_TITLE,
        "problem_count": len(session.problems),
        "learner_label": session.learner_label,
        "mode": session.mode,
        "state": session.state,
        "current_problem_no": session.current_problem_no,
        "still_seconds": still_seconds(session, now),
        "settings": asdict(session.settings),
        "problems": [problem_record(problem, session, now) for problem in session.problems],
        "persona_options": persona_options(),
        "stuck_points": stuck_points(session),
        "leak_blocked_count": session.leak_blocked_count,
        "created_at": iso(session.created_at),
        "ended_at": iso(session.ended_at),
    }


@router.patch("/sessions/{session_id}/settings")
async def patch_settings(
    session_id: str, body: SettingsPatch, request: Request, context: AppContext = Depends(get_context)
) -> dict:
    session = _find_session(context, session_id)
    require_device(request, context, session)
    session, _ = _apply(context, session, ChangeSettings(body.stuck_seconds, body.cooldown_seconds, body.persona), _now())
    context.store.save()
    return {"settings": asdict(session.settings), "state": session.state}


@router.post("/sessions/{session_id}/signals")
async def post_signal(
    session_id: str, body: SignalRequest, request: Request, context: AppContext = Depends(get_context)
) -> dict:
    session = _find_session(context, session_id)
    if body.force_stuck:
        require_operator(request, context)
    else:
        require_device(request, context, session)
    now = _now()
    before = session.state
    event = Signal(motion=body.motion, camera_ok=bool(body.camera_ok), force_stuck=body.force_stuck)
    session, result = _apply(context, session, event, now)
    logger.log(
        logging.INFO if session.state != before else logging.DEBUG,
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
    require_device(request, context, _find_session(context, session_id))
    data = await frame.read(MAX_FRAME_BYTES + 1)
    if len(data) > MAX_FRAME_BYTES:
        fail(413, f"フレームは {MAX_FRAME_BYTES // 1024} KB まで")
    now = _now()
    session, _ = _apply(context, _find_session(context, session_id), Tick(), now)
    if session.state == "ended":
        fail(409, "終了したセッションにはフレームを送れない")
    frame_id = _new_id("frm")
    context.frames[session.session_id] = (frame_id, data)
    start_prefetch(context, session, data, now)
    return {"frame_id": frame_id, "received_at": iso(now), "bytes": len(data)}


def _issue_hint(
    context: AppContext,
    session_id: str,
    *,
    problem_no: int,
    level: int,
    trigger: str,
    composed: ComposedHint,
    ticket: datetime,
    started: float,
    requested_at: datetime,
    prefetched: bool,
) -> dict:
    session, _ = _apply(context, _find_session(context, session_id), HintIssued(len(composed.speech), ticket), _now())
    hint = Hint(
        hint_id=_new_id("hnt"),
        level=level,
        trigger=trigger,
        speech=composed.speech,
        display=composed.display,
        stuck_point=composed.stuck_point,
        source=composed.source,
        leak_check=composed.leak_check,
        model=composed.model,
        latency_ms=int((time.monotonic() - started) * 1000),
        created_at=requested_at,
    )
    recorded = session.problems[problem_no - 1]
    recorded.hints.append(hint)
    recorded.problem_text = composed.problem_text or recorded.problem_text
    recorded.leak_strings = composed.leak_strings
    if not composed.leak_check.ok:
        session.leak_blocked_count += 1
    context.store.put(session)
    context.store.save()
    logger.info(
        "hint session=%s trigger=%s level=%s source=%s prefetched=%s latency_ms=%s",
        session.session_id,
        hint.trigger,
        hint.level,
        hint.source,
        prefetched,
        hint.latency_ms,
    )
    return {
        "hint_id": hint.hint_id,
        "problem_no": problem_no,
        "problem_text": recorded.problem_text,
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


async def _answer_utterance(context: AppContext, session: Session, utterance: str) -> dict | Response:
    started = time.monotonic()
    now = _now()
    _, acceptable = step(session, HintRequested("voice"), now, context.thresholds)
    if isinstance(acceptable, Rejected):
        fail(409, f"今の状態（{session.state}）では受理できない")
    if session.mode == "scripted":
        return Response(status_code=204)
    problem_no = session.current_problem_no
    problem = session.current_problem
    if asks_if_correct(utterance):
        _, requested = _apply(context, session, HintRequested("voice"), now)
        return _issue_hint(
            context,
            session.session_id,
            problem_no=problem_no,
            level=requested.level,
            trigger="voice",
            composed=check_reply(problem.leak_strings, session.settings.persona),
            ticket=requested.ticket,
            started=started,
            requested_at=now,
            prefetched=False,
        )
    frame = _latest_frame(context, session.session_id)
    _count_ai_call(context, session.session_id, frame, now)
    try:
        composed = await answer(context, problem, frame, utterance, session.settings.persona)
    except AIUnavailable:
        logger.warning("answer session=%s ai_unavailable=True", session.session_id)
        composed = answer_fallback(problem.leak_strings, session.settings.persona) if asks_for_help(utterance) else None
    latest = _find_session(context, session.session_id)
    if composed is None or latest.current_problem_no != problem_no or latest.settings.persona != session.settings.persona:
        logger.info("answer session=%s answered=False", session.session_id)
        return Response(status_code=204)
    latest, accepted = _apply(context, latest, HintRequested("voice"), _now())
    return _issue_hint(
        context,
        session.session_id,
        problem_no=problem_no,
        level=accepted.level,
        trigger="voice",
        composed=composed,
        ticket=accepted.ticket,
        started=started,
        requested_at=now,
        prefetched=False,
    )


@router.post("/sessions/{session_id}/hints", response_model=None)
async def request_hint(
    session_id: str, body: HintRequest, request: Request, context: AppContext = Depends(get_context)
) -> dict | Response:
    session = _find_session(context, session_id)
    require_device(request, context, session)
    if body.trigger == "voice" and body.utterance:
        with one_at_a_time(context, session_id, "voice"):
            return await _answer_utterance(context, session, body.utterance)
    started = time.monotonic()
    now = _now()
    session, accepted = _apply(context, session, HintRequested(body.trigger), now)
    problem = session.current_problem
    composing = take_prefetch(context, session) if body.trigger == "auto" else None
    try:
        if session.mode == "scripted":
            composed = fixed_hint(
                FALLBACK_HINTS[accepted.level], "scripted", LeakCheck(ok=True, fallback=False), problem.leak_strings,
                session.settings.persona,
            )
        elif composing:
            composed = await composing
        else:
            frame = _latest_frame(context, session_id)
            if body.trigger != "auto":
                _count_ai_call(context, session_id, frame, now)
            composed = await compose(context, problem, accepted.level, frame, session.settings.persona)
    except Exception:
        _abandon_hint(context, session_id, accepted.ticket)
        raise
    latest = _find_session(context, session_id)
    if latest.current_problem_no != session.current_problem_no or latest.settings.persona != session.settings.persona:
        _abandon_hint(context, session_id, accepted.ticket)
        fail(409, "ヒント生成中に問題か人格が変わったため、もう一度お試しください")
    return _issue_hint(
        context,
        session_id,
        problem_no=session.current_problem_no,
        level=accepted.level,
        trigger=body.trigger,
        composed=composed,
        ticket=accepted.ticket,
        started=started,
        requested_at=now,
        prefetched=composing is not None,
    )


@router.post("/sessions/{session_id}/check")
async def post_check(
    session_id: str, body: CheckRequest, request: Request, context: AppContext = Depends(get_context)
) -> dict:
    session = _find_session(context, session_id)
    require_device(request, context, session)
    now = _now()
    session, _ = _apply(context, session, CheckRequested(), now)
    checked_no = session.current_problem_no
    problem = session.current_problem
    if session.mode == "scripted":
        judgement = Judgement("correct", CORRECT_TEXT)
    else:
        judgement = await judge(context.ai, context.check_model, _latest_frame(context, session_id), problem.problem_text)
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


@router.post("/sessions/{session_id}/problem")
async def post_problem(
    session_id: str, body: ProblemRequest, request: Request, context: AppContext = Depends(get_context)
) -> dict:
    session = _find_session(context, session_id)
    require_device(request, context, session)
    now = _now()
    session, _ = _apply(context, session, Tick(), now)
    if session.state == "ended":
        fail(409, "終了したセッションでは読み取れない")
    problem_no = session.current_problem_no
    started = time.monotonic()
    with one_at_a_time(context, session_id, f"problem-{problem_no}"):
        frame = _latest_frame(context, session_id)
        _count_ai_call(context, session_id, frame, now)
        problem_text = await read_problem(context.ai, context.hint_model, frame, session.current_problem.problem_text)
    session = _find_session(context, session_id)
    problem = session.problems[problem_no - 1]
    if problem_text and session.current_problem_no == problem_no and problem_text != problem.problem_text:
        if not same_problem(problem_text, problem.problem_text):
            problem.leak_strings = []
        problem.problem_text = problem_text
        context.store.put(session)
        context.store.save()
    logger.info(
        "problem session=%s read=%s latency_ms=%s", session.session_id, problem_text is not None, int((time.monotonic() - started) * 1000)
    )
    return {"problem_no": problem_no, "problem_text": session.problems[problem_no - 1].problem_text, "state": session.state}


@router.post("/sessions/{session_id}/tts")
async def post_tts(session_id: str, body: SpeechRequest, request: Request, context: AppContext = Depends(get_context)) -> Response:
    session = _find_session(context, session_id)
    require_device(request, context, session)
    now = _now()
    session, _ = _apply(context, session, Tick(), now)
    if session.ended_at is not None and now - session.ended_at > timedelta(seconds=SPEECH_AFTER_END_SECONDS):
        fail(409, "終わったセッションの読み上げは受け付けない")
    count_call(context.speeches, session_id, SPEECHES_PER_MINUTE, now)
    if context.voice is None:
        fail(503, "読み上げの声が用意されていない")
    started = time.monotonic()
    try:
        audio = await context.voice.synthesize(body.text, body.character)
    except VoiceUnavailable as error:
        logger.warning("tts session=%s failed=%s", session.session_id, error)
        fail(503, "読み上げの声を作れなかった")
    logger.info(
        "tts session=%s character=%s chars=%s latency_ms=%s",
        session.session_id,
        body.character,
        len(body.text),
        int((time.monotonic() - started) * 1000),
    )
    return Response(content=audio, media_type="audio/wav")


@router.post("/sessions/{session_id}/advance")
async def post_advance(
    session_id: str, request: Request, context: AppContext = Depends(get_context)
) -> dict:
    session = _find_session(context, session_id)
    require_device(request, context, session)
    session, _ = _apply(context, session, Advance(), _now())
    context.store.save()
    return {"current_problem_no": session.current_problem_no, "state": session.state}


@router.post("/sessions/{session_id}/end")
async def post_end(session_id: str, request: Request, context: AppContext = Depends(get_context)) -> dict:
    session = _find_session(context, session_id)
    require_device_or_operator(request, context, session)
    session, _ = _apply(context, session, End(), _now())
    context.store.save()
    return {"state": session.state, "ended_at": iso(session.ended_at)}


@router.post("/demo/reset")
async def demo_reset(request: Request, context: AppContext = Depends(get_context)) -> dict:
    require_operator(request, context)
    if not context.demo_mode:
        fail(404, "DEMO_MODE が 1 でない")
    removed = context.store.clear()
    context.frames.clear()
    for session_id in list(context.prefetches):
        discard_prefetch(context, session_id)
    context.store.save()
    return {"ok": True, "removed_sessions": removed}


@router.get("/healthz")
async def healthz(context: AppContext = Depends(get_context)) -> dict:
    return {
        "ok": True,
        "ai": "ok" if context.ai else "missing",
        "mode_default": MODE_DEFAULT,
    }
