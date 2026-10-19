import asyncio
from collections.abc import Callable, Iterator
from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import routes
from app.main import create_app
from app.voicevox import VoiceUnavailable

START = datetime(2026, 10, 17, 7, 0, tzinfo=UTC)
OPERATOR_KEY = "operator-test"
STUCK_SECONDS = 10
WAV = b"RIFF\x00\x00\x00\x00WAVE"


def ai_hint(speech: str) -> dict:
    return {
        "readable": True,
        "problem_text": "2x - 7 = 4x + 3",
        "final_answer": "x = -5",
        "key_values": ["-2x = 10"],
        "stuck_point": "移項の符号",
        "speech": speech,
        "display": speech,
    }


class ScriptedAI:
    def __init__(self, reply: dict | None = None, *, delay: float = 0, error: Exception | None = None) -> None:
        self.reply = reply
        self.delay = delay
        self.error = error
        self.on_call: Callable[[], None] = lambda: None
        self.requests: list[str] = []
        self.systems: list[str] = []
        self.schemas: list[dict] = []
        self.frames: list[bytes] = []
        self.cancelled = 0

    async def generate_json(self, model: str, system: str, text: str, image_jpeg: bytes, schema: dict) -> dict:
        self.requests.append(text)
        self.systems.append(system)
        self.schemas.append(schema)
        self.frames.append(image_jpeg)
        self.on_call()
        if self.delay:
            try:
                await asyncio.sleep(self.delay)
            except asyncio.CancelledError:
                self.cancelled += 1
                raise
        if self.error:
            raise self.error
        return deepcopy(self.reply)


class FakeVoice:
    def __init__(self) -> None:
        self.fail = False
        self.texts: list[str] = []
        self.characters: list[str] = []

    async def synthesize(self, text: str, character: str) -> bytes:
        self.texts.append(text)
        self.characters.append(character)
        if self.fail:
            raise VoiceUnavailable("timeout")
        return WAV


@dataclass
class Device:
    client: TestClient
    session_id: str
    headers: dict[str, str]
    now: datetime = START

    def signal(self, second: int, motion: float) -> dict:
        self.now = START + timedelta(seconds=second)
        body = {"motion": motion, "camera_ok": True}
        return self.client.post(f"/sessions/{self.session_id}/signals", json=body, headers=self.headers).json()

    def force_stuck(self, second: int) -> dict:
        self.now = START + timedelta(seconds=second)
        body = {"force_stuck": True}
        operator = {"X-Operator-Key": OPERATOR_KEY}
        return self.client.post(f"/sessions/{self.session_id}/signals", json=body, headers=operator).json()

    def frame(self) -> str:
        files = {"frame": ("frame.jpg", b"\xff\xd8jpeg", "image/jpeg")}
        return self.client.post(f"/sessions/{self.session_id}/frames", files=files, headers=self.headers).json()["frame_id"]

    def start_watching(self) -> str:
        self.signal(0, 0.05)
        self.signal(1, 0.05)
        return self.frame()

    def hint(self, frame_id: str, trigger: str = "auto", utterance: str | None = None) -> dict:
        body = {"trigger": trigger, "frame_id": frame_id, **({"utterance": utterance} if utterance else {})}
        return self.client.post(f"/sessions/{self.session_id}/hints", json=body, headers=self.headers).json()

    def recorded_hints(self) -> list[dict]:
        detail = self.client.get(f"/sessions/{self.session_id}", headers=self.headers).json()
        return [hint for problem in detail["problems"] for hint in problem["hints"]]


@pytest.fixture
def device(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, ai) -> Iterator[Device]:
    monkeypatch.setenv("OPERATOR_KEY", OPERATOR_KEY)
    monkeypatch.setenv("DATA_PATH", str(tmp_path / "tonari.json"))
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    app = create_app()
    app.state.context.ai = ai
    with TestClient(app) as client:
        settings = {"stuck_seconds": STUCK_SECONDS, "cooldown_seconds": 0}
        created = client.post(
            "/sessions",
            json={"worksheet_id": "FREE", "mode": "live", "settings": settings},
            headers={"X-Operator-Key": OPERATOR_KEY},
        ).json()
        device = Device(client, created["session_id"], {"Authorization": f"Bearer {created['session_token']}"})
        monkeypatch.setattr(routes, "_now", lambda: device.now)
        yield device
