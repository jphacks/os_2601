import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from app.state import Check, Hint, LeakCheck, Problem, Session, SessionSettings

RUNTIME_FIELDS = ("still_since", "speaking_until", "cooldown_until", "last_signal_at", "speaking_after_correct", "pending_until", "prefetch_requested")


def _encode(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _encode(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_encode(item) for item in value]
    return value


def _parse_time(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def _decode_hint(raw: dict) -> Hint:
    return Hint(
        **{**raw, "leak_check": LeakCheck(**raw["leak_check"]), "created_at": datetime.fromisoformat(raw["created_at"])}
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
    settings = dict(raw["settings"])
    # 保存済みの旧人格だけを移行する。新規の不正な入力は API 側で拒否する。
    if settings.get("persona") not in ("teacher", "ikemen"):
        settings["persona"] = "teacher"
    return Session(
        session_id=raw["session_id"],
        session_token=raw["session_token"],
        worksheet_id=raw["worksheet_id"],
        learner_label=raw["learner_label"],
        mode=raw["mode"],
        settings=SessionSettings(**settings),
        problems=[_decode_problem(problem) for problem in raw["problems"]],
        created_at=datetime.fromisoformat(raw["created_at"]),
        state=raw["state"] if raw["state"] == "ended" else "watching",
        current_problem_no=raw["current_problem_no"],
        leak_blocked_count=raw["leak_blocked_count"],
        ended_at=_parse_time(raw["ended_at"]),
    )


class SessionStore:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._sessions: dict[str, Session] = {}

    def load(self) -> None:
        if not self._path.exists():
            return
        raw = json.loads(self._path.read_text(encoding="utf-8"))
        self._sessions = {session_id: _decode_session(body) for session_id, body in raw["sessions"].items()}

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        sessions = {}
        for session_id, session in self._sessions.items():
            body = asdict(session)
            for name in RUNTIME_FIELDS:
                body.pop(name)
            sessions[session_id] = _encode(body)
        temporary = self._path.with_suffix(".tmp")
        temporary.write_text(json.dumps({"sessions": sessions}, ensure_ascii=False), encoding="utf-8")
        temporary.replace(self._path)

    def get(self, session_id: str) -> Session | None:
        return self._sessions.get(session_id)

    def put(self, session: Session) -> None:
        self._sessions[session.session_id] = session

    def all(self) -> list[Session]:
        return list(self._sessions.values())

    def clear(self) -> int:
        removed = len(self._sessions)
        self._sessions = {}
        return removed
