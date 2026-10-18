import asyncio
from dataclasses import dataclass, field
from datetime import datetime

from fastapi import Request

from app.gemini import Gemini
from app.hints import ComposedHint
from app.state import SessionSettings, Thresholds
from app.store import SessionStore
from app.voicevox import Voicevox


@dataclass
class Prefetch:
    problem_no: int
    stuck_count: int
    composing: asyncio.Task[ComposedHint]
    persona: str


@dataclass
class AppContext:
    thresholds: Thresholds
    default_settings: SessionSettings
    store: SessionStore
    operator_key: str
    demo_mode: bool
    open_sessions: bool
    ai: Gemini | None
    hint_model: str
    check_model: str
    frames: dict[str, tuple[str, bytes]] = field(default_factory=dict)
    prefetches: dict[str, Prefetch] = field(default_factory=dict)
    voice: Voicevox | None = None
    opened_at: dict[str, list[datetime]] = field(default_factory=dict)
    ai_calls: dict[str, list[datetime]] = field(default_factory=dict)
    background_calls: dict[str, list[datetime]] = field(default_factory=dict)
    speeches: dict[str, list[datetime]] = field(default_factory=dict)
    busy: set[tuple[str, str]] = field(default_factory=set)


def get_context(request: Request) -> AppContext:
    return request.app.state.context
