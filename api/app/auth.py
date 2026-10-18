import secrets

from fastapi import Request

from app.context import AppContext, fail
from app.state import Session


def _matches(given: str | None, expected: str) -> bool:
    return bool(given) and bool(expected) and secrets.compare_digest(given.encode(), expected.encode())


def _operator_ok(request: Request, context: AppContext) -> bool:
    return _matches(request.headers.get("X-Operator-Key"), context.operator_key)


def _device_ok(request: Request, session: Session) -> bool:
    scheme, _, token = request.headers.get("Authorization", "").partition(" ")
    return scheme.lower() == "bearer" and _matches(token, session.session_token)


def require_operator(request: Request, context: AppContext) -> None:
    if not _operator_ok(request, context):
        fail(401, "X-Operator-Key が無いか一致しない")


def require_device(request: Request, context: AppContext, session: Session) -> None:
    if _device_ok(request, session):
        return
    if _operator_ok(request, context):
        fail(403, "この操作はセッションのトークンでだけできる")
    fail(401, "セッションのトークンが無いか一致しない")


def require_device_or_operator(request: Request, context: AppContext, session: Session) -> None:
    if not (_device_ok(request, session) or _operator_ok(request, context)):
        fail(401, "セッションのトークンかオペレータの鍵が要る")
