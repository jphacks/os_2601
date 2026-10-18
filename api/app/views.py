from dataclasses import asdict
from datetime import datetime

from app.state import Hint, Problem, Session


def iso(value: datetime | None) -> str | None:
    return value.isoformat(timespec="seconds").replace("+00:00", "Z") if value else None


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
        "created_at": iso(hint.created_at),
    }


def problem_record(problem: Problem, session: Session, now: datetime) -> dict:
    check = problem.check
    return {
        "problem_no": problem.problem_no,
        "problem_text": problem.problem_text,
        "status": problem.status,
        "stuck_count": problem.stuck_count,
        "max_level": max((hint.level for hint in problem.hints), default=0),
        "seconds_spent": _seconds_spent(problem, session, now),
        "hints": [_hint_record(hint) for hint in problem.hints],
        "check": {"verdict": check.verdict, "display": check.display, "created_at": iso(check.created_at)} if check else None,
    }


def stuck_points(session: Session) -> list[dict]:
    counts: dict[str, int] = {}
    for problem in session.problems:
        for hint in problem.hints:
            if hint.source == "ai":
                counts[hint.stuck_point] = counts.get(hint.stuck_point, 0) + 1
    return [{"label": label, "count": count} for label, count in sorted(counts.items(), key=lambda item: -item[1])]
