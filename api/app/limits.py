from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timedelta

from fastapi import Request

from app.context import AppContext
from app.errors import fail

MAX_FRAME_BYTES = 600 * 1024
OPEN_SESSIONS_PER_MINUTE = 10
OPEN_SESSIONS_PER_MINUTE_TOTAL = 30
AI_CALLS_PER_MINUTE = 20
BACKGROUND_CALLS_PER_MINUTE = 12
SPEECHES_PER_MINUTE = 40


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[-1].strip()
    return request.client.host if request.client else "unknown"


def allow_open(context: AppContext, ip: str, now: datetime) -> bool:
    context.opened_at = {
        key: recent
        for key, times in context.opened_at.items()
        if (recent := [opened for opened in times if now - opened < timedelta(minutes=1)])
    }
    total = sum(len(times) for times in context.opened_at.values())
    if total >= OPEN_SESSIONS_PER_MINUTE_TOTAL or len(context.opened_at.get(ip, [])) >= OPEN_SESSIONS_PER_MINUTE:
        return False
    context.opened_at[ip] = [*context.opened_at.get(ip, []), now]
    return True


def try_count_call(calls: dict[str, list[datetime]], session_id: str, limit: int, now: datetime) -> bool:
    recent = [called for called in calls.get(session_id, []) if now - called < timedelta(minutes=1)]
    if len(recent) >= limit:
        return False
    calls[session_id] = [*recent, now]
    return True


def count_call(calls: dict[str, list[datetime]], session_id: str, limit: int, now: datetime) -> None:
    if not try_count_call(calls, session_id, limit, now):
        fail(429, "少し待ってから、もう一度")


@contextmanager
def one_at_a_time(context: AppContext, session_id: str, kind: str) -> Iterator[None]:
    key = (session_id, kind)
    if key in context.busy:
        fail(429, "前の問い合わせが終わってから、もう一度")
    context.busy.add(key)
    try:
        yield
    finally:
        context.busy.discard(key)
