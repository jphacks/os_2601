import asyncio
import logging
import time

from app.context import AppContext, Prefetch
from app.hints import ComposedHint, compose_hint
from app.state import Problem, Session, auto_hint_level

logger = logging.getLogger(__name__)


def ai_hints(problem: Problem) -> list[str]:
    return [hint.display for hint in problem.hints if hint.source == "ai"]


async def compose(context: AppContext, problem: Problem, level: int, frame: bytes | None, persona: str = "teacher") -> ComposedHint:
    return await compose_hint(
        context.ai, context.hint_model, frame, level, ai_hints(problem), problem.problem_text, problem.leak_strings, persona
    )


async def compose_ahead(
    context: AppContext, session_id: str, problem: Problem, level: int, frame: bytes, persona: str = "teacher"
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


def start_prefetch(context: AppContext, session: Session, frame: bytes) -> None:
    if session.session_id in context.prefetches:
        return
    problem = session.current_problem
    stuck_count = problem.stuck_count + 1
    level = auto_hint_level(stuck_count, session.settings)
    composing = asyncio.create_task(compose_ahead(context, session.session_id, problem, level, frame, session.settings.persona))
    context.prefetches[session.session_id] = Prefetch(session.current_problem_no, stuck_count, composing, session.settings.persona)


def discard_prefetch(context: AppContext, session_id: str) -> None:
    prefetch = context.prefetches.pop(session_id, None)
    if prefetch:
        prefetch.composing.cancel()


def take_prefetch(context: AppContext, session: Session) -> asyncio.Task[ComposedHint] | None:
    prefetch = context.prefetches.pop(session.session_id, None)
    if prefetch is None:
        return None
    if (prefetch.problem_no, prefetch.stuck_count, prefetch.persona) == (
        session.current_problem_no, session.current_problem.stuck_count, session.settings.persona
    ):
        return prefetch.composing
    prefetch.composing.cancel()
    return None
