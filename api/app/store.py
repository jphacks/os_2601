import json
import logging
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from app.state import Check, Hint, LeakCheck, Problem, Session, SessionSettings

RUNTIME_FIELDS = (
    "still_since",
    "speaking_until",
    "cooldown_until",
    "last_signal_at",
    "speaking_after_correct",
    "pending_until",
    "prefetch_requested",
)
RENAMED_SOURCES = {"gpt": "ai"}

logger = logging.getLogger(__name__)


def _encode(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _encode(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_encode(item) for item in value]
    return value


def _encode_session(session: Session) -> dict:
    body = asdict(session)
    for name in RUNTIME_FIELDS:
        body.pop(name)
    return _encode(body)


def _parse_time(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def _decode_hint(raw: dict) -> Hint:
    return Hint(
        **{
            **raw,
            "source": RENAMED_SOURCES.get(raw["source"], raw["source"]),
            "leak_check": LeakCheck(**raw["leak_check"]),
            "created_at": datetime.fromisoformat(raw["created_at"]),
        }
    )


def _decode_problem(raw: dict) -> Problem:
    check = raw["check"]
    return Problem(
        problem_no=raw["problem_no"],
        status=raw["status"],
        stuck_count=raw["stuck_count"],
        started_at=_parse_time(raw["started_at"]),
        finished_at=_parse_time(raw["finished_at"]),
        hints=[_decode_hint(hint) for hint in raw["hints"]],
        check=Check(**{**check, "created_at": datetime.fromisoformat(check["created_at"])}) if check else None,
        problem_text=raw.get("problem_text"),
        leak_strings=raw.get("leak_strings", []),
    )


def _decode_session(raw: dict) -> Session:
    return Session(
        session_id=raw["session_id"],
        session_token=raw["session_token"],
        worksheet_id=raw["worksheet_id"],
        learner_label=raw["learner_label"],
        mode=raw["mode"],
        settings=SessionSettings(**raw["settings"]),
        problems=[_decode_problem(problem) for problem in raw["problems"]],
        created_at=datetime.fromisoformat(raw["created_at"]),
        state=raw["state"] if raw["state"] == "ended" else "watching",
        current_problem_no=raw["current_problem_no"],
        leak_blocked_count=raw["leak_blocked_count"],
        ended_at=_parse_time(raw["ended_at"]),
        auto_end_at=_parse_time(raw.get("auto_end_at")),
    )


class SessionStore:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._sessions: dict[str, Session] = {}
        self._encoded: dict[str, dict] = {}
        self._changed: set[str] = set()

    def load(self) -> None:
        if not self._path.exists():
            return
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            sessions = {session_id: _decode_session(body) for session_id, body in raw["sessions"].items()}
        except (ValueError, KeyError, TypeError) as error:
            broken = self._path.with_suffix(".broken")
            self._path.replace(broken)
            logger.warning("保存ファイルを読めないので %s に退けて空で始める: %r", broken.name, error)
            return
        self._sessions = sessions
        self._encoded = {}
        self._changed = set(sessions)

    def save(self) -> None:
        for session_id in self._changed:
            if session_id in self._sessions:
                self._encoded[session_id] = _encode_session(self._sessions[session_id])
        self._changed.clear()
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._path.with_suffix(".tmp")
        temporary.write_text(json.dumps({"sessions": self._encoded}, ensure_ascii=False), encoding="utf-8")
        temporary.replace(self._path)

    def get(self, session_id: str) -> Session | None:
        session = self._sessions.get(session_id)
        if session is not None:
            self._changed.add(session_id)
        return session

    def put(self, session: Session) -> None:
        self._sessions[session.session_id] = session
        self._changed.add(session.session_id)

    def all(self) -> list[Session]:
        return list(self._sessions.values())

    def remove(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)
        self._encoded.pop(session_id, None)

    def clear(self) -> int:
        removed = len(self._sessions)
        self._sessions = {}
        self._encoded = {}
        self._changed.clear()
        return removed
