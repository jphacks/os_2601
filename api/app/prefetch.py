import asyncio
import logging
import time
from datetime import datetime

from app.composer import compose
from app.context import AppContext, Prefetch
from app.hints import ComposedHint
from app.limits import allow_background_call
from app.state import Problem, Session, auto_hint_level

logger = logging.getLogger(__name__)


async def _compose_ahead(
    context: AppContext, session_id: str, problem: Problem, level: int, frame: bytes, persona: str
) -> ComposedHint:
    started = time.monotonic()
    composed = await compose(context, problem, level, frame, persona)
    logger.info(
        "prefetch session=%s level=%s source=%s ai_ms=%s",
        session_id,
        level,
        composed.source,
        int((time.monotonic() - started) * 1000),
    )
    return composed


def _wanted(session: Session) -> bool:
    return session.state == "still" and session.prefetch_requested


def _matches(prefetch: Prefetch, session: Session, stuck_count: int) -> bool:
    return (prefetch.problem_no, prefetch.stuck_count, prefetch.persona) == (
        session.current_problem_no, stuck_count, session.settings.persona
    )


def start_prefetch(context: AppContext, session: Session, frame: bytes, now: datetime) -> None:
    if not _wanted(session) or session.session_id in context.prefetches:
        return
    if not allow_background_call(context, session.session_id, frame, now):
        return
    problem = session.current_problem
    stuck_count = problem.stuck_count + 1
    level = auto_hint_level(stuck_count, session.settings)
    composing = asyncio.create_task(_compose_ahead(context, session.session_id, problem, level, frame, session.settings.persona))
    context.prefetches[session.session_id] = Prefetch(session.current_problem_no, stuck_count, composing, session.settings.persona)


def settle_prefetch(context: AppContext, session: Session) -> None:
    prefetch = context.prefetches.get(session.session_id)
    if prefetch is None:
        return
    if _wanted(session) and _matches(prefetch, session, session.current_problem.stuck_count + 1):
        return
    if session.state == "stuck" and _matches(prefetch, session, session.current_problem.stuck_count):
        return
    discard_prefetch(context, session.session_id)


def discard_prefetch(context: AppContext, session_id: str) -> None:
    prefetch = context.prefetches.pop(session_id, None)
    if prefetch:
        prefetch.composing.cancel()


def take_prefetch(context: AppContext, session: Session) -> asyncio.Task[ComposedHint] | None:
    prefetch = context.prefetches.pop(session.session_id, None)
    if prefetch is None:
        return None
    if _matches(prefetch, session, session.current_problem.stuck_count):
        return prefetch.composing
    prefetch.composing.cancel()
    return None
