import math
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Literal

State = Literal["created", "watching", "still", "stuck", "speaking", "cooldown", "checking", "ended"]
Mode = Literal["live", "scripted"]
Trigger = Literal["auto", "manual", "voice"]
Verdict = Literal["correct", "incorrect", "unreadable"]
ProblemStatus = Literal["pending", "working", "done", "skipped"]

NEXT_ACTION = "send_frame_and_request_hint"
HINTABLE_STATES: tuple[State, ...] = ("watching", "still", "cooldown")
SETTINGS_EDITABLE_STATES: tuple[State, ...] = ("created", "watching", "still", "cooldown")
ADVANCEABLE_STATES: tuple[State, ...] = ("watching", "still", "cooldown", "speaking")
TIMEOUT_STATES: tuple[State, ...] = ("watching", "still", "stuck")


@dataclass(frozen=True)
class Thresholds:
    motion_threshold: float
    signal_timeout_seconds: float
    speech_seconds_per_char: float
    speech_seconds_base: float


@dataclass
class SessionSettings:
    stuck_seconds: int
    cooldown_seconds: int
    max_level: int


@dataclass
class LeakCheck:
    ok: bool
    fallback: bool


@dataclass
class Hint:
    hint_id: str
    level: int
    trigger: Trigger
    speech: str
    display: str
    stuck_point: str
    source: Literal["gpt", "fallback", "scripted"]
    leak_check: LeakCheck
    model: str | None
    latency_ms: int
    created_at: datetime


@dataclass
class Check:
    check_id: str
    verdict: Verdict
    speech: str
    display: str
    created_at: datetime


@dataclass
class Problem:
    problem_no: int
    status: ProblemStatus = "pending"
    stuck_count: int = 0
    started_at: datetime | None = None
    finished_at: datetime | None = None
    hints: list[Hint] = field(default_factory=list)
    check: Check | None = None
    problem_text: str | None = None
    answer: str | None = None
    leak_strings: list[str] = field(default_factory=list)


@dataclass
class Session:
    session_id: str
    session_token: str
    worksheet_id: str
    learner_label: str
    mode: Mode
    settings: SessionSettings
    problems: list[Problem]
    created_at: datetime
    state: State = "created"
    current_problem_no: int = 1
    leak_blocked_count: int = 0
    ended_at: datetime | None = None
    still_since: datetime | None = None
    speaking_until: datetime | None = None
    cooldown_until: datetime | None = None
    last_signal_at: datetime | None = None
    speaking_after_correct: bool = False

    @property
    def current_problem(self) -> Problem:
        return self.problems[self.current_problem_no - 1]


@dataclass(frozen=True)
class Signal:
    motion: float | None
    camera_ok: bool
    force_stuck: bool = False


@dataclass(frozen=True)
class ChangeSettings:
    stuck_seconds: int | None
    cooldown_seconds: int | None


@dataclass(frozen=True)
class HintRequested:
    trigger: Trigger


@dataclass(frozen=True)
class HintIssued:
    speech_chars: int


@dataclass(frozen=True)
class CheckRequested:
    pass


@dataclass(frozen=True)
class CheckDone:
    verdict: Verdict
    speech_chars: int


@dataclass(frozen=True)
class Advance:
    pass


@dataclass(frozen=True)
class End:
    pass


@dataclass(frozen=True)
class Tick:
    pass


Event = Signal | ChangeSettings | HintRequested | HintIssued | CheckRequested | CheckDone | Advance | End | Tick


@dataclass(frozen=True)
class Accepted:
    next_action: str | None = None
    level: int | None = None


@dataclass(frozen=True)
class Rejected:
    code: str = "STATE_CONFLICT"


Result = Accepted | Rejected


def still_seconds(session: Session, now: datetime) -> int:
    if session.state != "still" or session.still_since is None:
        return 0
    return int((now - session.still_since).total_seconds())


def cooldown_remaining(session: Session, now: datetime) -> int:
    if session.state != "cooldown" or session.cooldown_until is None:
        return 0
    return max(0, math.ceil((session.cooldown_until - now).total_seconds()))


def _enter_stuck(session: Session) -> None:
    session.state = "stuck"
    session.still_since = None
    session.current_problem.stuck_count += 1


def _enter_speaking(session: Session, now: datetime, speech_chars: int, thresholds: Thresholds) -> None:
    session.state = "speaking"
    session.still_since = None
    session.speaking_after_correct = False
    session.speaking_until = now + timedelta(
        seconds=speech_chars * thresholds.speech_seconds_per_char + thresholds.speech_seconds_base
    )


def _return_to_watching(session: Session) -> None:
    session.state = "watching"
    session.still_since = None
    session.speaking_until = None
    session.cooldown_until = None
    session.speaking_after_correct = False


def _start_problem(session: Session, problem_no: int, now: datetime) -> None:
    session.current_problem_no = problem_no
    problem = session.current_problem
    problem.status = "working"
    problem.started_at = now


def _end_session(session: Session, now: datetime) -> None:
    session.state = "ended"
    session.ended_at = now


def _apply_clock(session: Session, now: datetime, thresholds: Thresholds) -> None:
    signal_lost = (
        session.last_signal_at is not None
        and (now - session.last_signal_at).total_seconds() >= thresholds.signal_timeout_seconds
    )
    if session.state in TIMEOUT_STATES and signal_lost:
        session.state = "watching"
        session.still_since = None
        session.last_signal_at = None
    if session.state == "speaking" and session.speaking_until is not None and now >= session.speaking_until:
        session.state = "cooldown"
        session.speaking_until = None
        session.speaking_after_correct = False
        session.cooldown_until = now + timedelta(seconds=session.settings.cooldown_seconds)
    if session.state == "cooldown" and session.cooldown_until is not None and now >= session.cooldown_until:
        session.state = "watching"
        session.cooldown_until = None


def _on_signal(session: Session, signal: Signal, now: datetime, thresholds: Thresholds) -> Result:
    if signal.force_stuck:
        if session.state == "stuck":
            return Accepted(next_action=NEXT_ACTION)
        if session.state not in HINTABLE_STATES:
            return Rejected()
        _enter_stuck(session)
        return Accepted(next_action=NEXT_ACTION)

    previous_signal_at = session.last_signal_at
    if previous_signal_at and (now - previous_signal_at).total_seconds() >= thresholds.signal_timeout_seconds:
        previous_signal_at = None
    session.last_signal_at = now
    if session.state == "created":
        session.state = "watching"
    elif session.state in ("watching", "still"):
        moving = not signal.camera_ok or signal.motion is None or signal.motion >= thresholds.motion_threshold
        if moving:
            session.state = "watching"
            session.still_since = None
        elif session.state == "watching":
            session.state = "still"
            session.still_since = previous_signal_at or now
        elif session.still_since is not None and (now - session.still_since).total_seconds() >= session.settings.stuck_seconds:
            _enter_stuck(session)
    return Accepted(next_action=NEXT_ACTION if session.state == "stuck" else None)


def _on_change_settings(session: Session, change: ChangeSettings) -> Result:
    if session.state not in SETTINGS_EDITABLE_STATES:
        return Rejected()
    if change.stuck_seconds is not None:
        session.settings.stuck_seconds = change.stuck_seconds
    if change.cooldown_seconds is not None:
        session.settings.cooldown_seconds = change.cooldown_seconds
    return Accepted()


def _on_hint_requested(session: Session, request: HintRequested) -> Result:
    problem = session.current_problem
    if request.trigger == "auto":
        if session.state != "stuck":
            return Rejected()
        return Accepted(level=min(problem.stuck_count, session.settings.max_level))
    if session.state not in HINTABLE_STATES:
        return Rejected()
    return Accepted(level=problem.hints[-1].level if problem.hints else 1)


def _on_check_done(session: Session, done: CheckDone, now: datetime, thresholds: Thresholds) -> Result:
    if session.state != "checking":
        return Rejected()
    if done.verdict == "correct":
        problem = session.current_problem
        problem.status = "done"
        problem.finished_at = now
        if session.current_problem_no == len(session.problems):
            _end_session(session, now)
            return Accepted()
        _start_problem(session, session.current_problem_no + 1, now)
        _enter_speaking(session, now, done.speech_chars, thresholds)
        session.speaking_after_correct = True
        return Accepted()
    _enter_speaking(session, now, done.speech_chars, thresholds)
    return Accepted()


def _on_advance(session: Session, now: datetime) -> Result:
    if session.state not in ADVANCEABLE_STATES:
        return Rejected()
    if session.speaking_after_correct:
        _return_to_watching(session)
        return Accepted()
    problem = session.current_problem
    if problem.status != "done":
        problem.status = "skipped"
        problem.finished_at = now
    if session.current_problem_no == len(session.problems):
        _end_session(session, now)
        return Accepted()
    _start_problem(session, session.current_problem_no + 1, now)
    _return_to_watching(session)
    return Accepted()


def _on_ended(event: Event) -> Result:
    if isinstance(event, Signal) and not event.force_stuck:
        return Accepted()
    if isinstance(event, (Tick, End)):
        return Accepted()
    return Rejected()


def step(session: Session, event: Event, now: datetime, thresholds: Thresholds) -> tuple[Session, Result]:
    next_session = deepcopy(session)
    if next_session.state == "ended":
        return next_session, _on_ended(event)
    _apply_clock(next_session, now, thresholds)

    match event:
        case Signal():
            return next_session, _on_signal(next_session, event, now, thresholds)
        case ChangeSettings():
            return next_session, _on_change_settings(next_session, event)
        case HintRequested():
            return next_session, _on_hint_requested(next_session, event)
        case HintIssued(speech_chars=chars):
            _enter_speaking(next_session, now, chars, thresholds)
            return next_session, Accepted()
        case CheckRequested():
            if next_session.state not in HINTABLE_STATES:
                return next_session, Rejected()
            next_session.state = "checking"
            return next_session, Accepted()
        case CheckDone():
            return next_session, _on_check_done(next_session, event, now, thresholds)
        case Advance():
            return next_session, _on_advance(next_session, now)
        case End():
            _end_session(next_session, now)
            return next_session, Accepted()
        case Tick():
            return next_session, Accepted()
