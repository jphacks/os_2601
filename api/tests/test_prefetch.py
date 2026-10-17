import asyncio
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import routes
from app.main import create_app

START = datetime(2026, 10, 17, 7, 0, tzinfo=UTC)
OPERATOR_KEY = "operator-test"
STUCK_SECONDS = 10
MOVING = 0.05
STILL = 0.01
HINT_SPEECH = "右辺に移したときの符号を見てみて"


class SlowAI:
    def __init__(self) -> None:
        self.delay = 0.05
        self.started = 0
        self.cancelled = 0

    async def generate_json(self, model: str, system: str, text: str, image_jpeg: bytes, schema: dict) -> dict:
        self.started += 1
        try:
            await asyncio.sleep(self.delay)
        except asyncio.CancelledError:
            self.cancelled += 1
            raise
        return {
            "readable": True,
            "problem_text": "2x - 7 = 4x + 3",
            "final_answer": "x = -5",
            "key_values": ["-2x = 10"],
            "stuck_point": "移項の符号",
            "speech": HINT_SPEECH,
            "display": HINT_SPEECH,
        }


@dataclass
class Device:
    client: TestClient
    session_id: str
    headers: dict[str, str]
    now: datetime = START

    def signal(self, second: int, motion: float) -> dict:
        self.now = START + timedelta(seconds=second)
        body = {"ts": self.now.isoformat(), "motion": motion, "camera_ok": True}
        return self.client.post(f"/sessions/{self.session_id}/signals", json=body, headers=self.headers).json()

    def force_stuck(self, second: int) -> dict:
        self.now = START + timedelta(seconds=second)
        body = {"ts": self.now.isoformat(), "force_stuck": True}
        operator = {"X-Operator-Key": OPERATOR_KEY}
        return self.client.post(f"/sessions/{self.session_id}/signals", json=body, headers=operator).json()

    def frame(self) -> str:
        files = {"frame": ("frame.jpg", b"\xff\xd8jpeg", "image/jpeg")}
        return self.client.post(f"/sessions/{self.session_id}/frames", files=files, headers=self.headers).json()["frame_id"]

    def auto_hint(self, frame_id: str) -> dict:
        body = {"trigger": "auto", "frame_id": frame_id}
        return self.client.post(f"/sessions/{self.session_id}/hints", json=body, headers=self.headers).json()


def wait_until(condition: Callable[[], bool]) -> None:
    deadline = time.monotonic() + 2
    while not condition():
        assert time.monotonic() < deadline
        time.sleep(0.01)


def stay_still_until_frame_is_requested(device: Device) -> list[str | None]:
    return [device.signal(second, MOVING if second < 2 else STILL)["next_action"] for second in range(9)]


@pytest.fixture
def ai() -> SlowAI:
    return SlowAI()


@pytest.fixture
def device(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, ai: SlowAI) -> Iterator[Device]:
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


def test_auto_hint_at_stuck_is_the_one_prepared_from_the_earlier_frame(device: Device, ai: SlowAI) -> None:
    assert stay_still_until_frame_is_requested(device) == [None] * 8 + ["send_frame"]
    frame_id = device.frame()
    wait_until(lambda: ai.started == 1)
    assert [device.signal(second, STILL)["next_action"] for second in range(9, 12)] == [
        None,
        None,
        "send_frame_and_request_hint",
    ]
    hint = device.auto_hint(frame_id)
    assert (hint["speech"], hint["source"], hint["level"], hint["state"]) == (HINT_SPEECH, "gpt", 1, "speaking")
    assert ai.started == 1


def test_hint_being_prepared_is_dropped_when_the_hand_moves_again(device: Device, ai: SlowAI) -> None:
    ai.delay = 30
    stay_still_until_frame_is_requested(device)
    device.frame()
    wait_until(lambda: ai.started == 1)
    assert device.signal(9, MOVING)["state"] == "watching"
    wait_until(lambda: ai.cancelled == 1)


def test_hint_prepared_before_a_signal_gap_is_dropped_when_the_next_stillness_starts(device: Device, ai: SlowAI) -> None:
    ai.delay = 30
    stay_still_until_frame_is_requested(device)
    device.frame()
    wait_until(lambda: ai.started == 1)
    signal = device.signal(15, STILL)
    assert (signal["state"], signal["still_seconds"]) == ("still", 0)
    wait_until(lambda: ai.cancelled == 1)


def test_hint_prepared_for_an_earlier_stuck_is_not_used_for_the_next_one(device: Device, ai: SlowAI) -> None:
    stay_still_until_frame_is_requested(device)
    device.signal(11, STILL)
    assert device.auto_hint(device.frame())["level"] == 1
    device.signal(15, MOVING)
    assert [device.signal(second, STILL)["next_action"] for second in range(16, 23)][-1] == "send_frame"
    frame_id = device.frame()
    wait_until(lambda: ai.started == 2)
    assert [device.signal(second, STILL)["state"] for second in range(23, 26)][-1] == "stuck"
    assert device.force_stuck(31)["state"] == "stuck"
    hint = device.auto_hint(frame_id)
    assert (hint["level"], hint["source"]) == (2, "gpt")
    assert ai.started == 3
