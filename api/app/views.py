from dataclasses import asdict
from datetime import datetime

from app.personas import persona_options
from app.state import Hint, Problem, Session, still_seconds

WORKSHEET_TITLE = "自由な問題"


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


def session_created(session: Session) -> dict:
    return {
        "session_id": session.session_id,
        "session_token": session.session_token,
        "mode": session.mode,
        "state": session.state,
        "worksheet": {"worksheet_id": session.worksheet_id, "title": WORKSHEET_TITLE, "problem_count": len(session.problems)},
        "settings": asdict(session.settings),
        "created_at": iso(session.created_at),
    }


def session_summary(session: Session) -> dict:
    return {
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


def session_detail(session: Session, now: datetime) -> dict:
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


def hint_response(hint: Hint, problem: Problem, session: Session) -> dict:
    return {
        "hint_id": hint.hint_id,
        "problem_no": problem.problem_no,
        "problem_text": problem.problem_text,
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
