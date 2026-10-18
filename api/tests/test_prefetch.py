import asyncio
import time
from collections.abc import Callable

import pytest
from conftest import Device

from app.personas import get_persona

MOVING = 0.05
STILL = 0.01
HINT_SPEECH = "右辺に移したときの符号を見てみて"


class SlowAI:
    def __init__(self) -> None:
        self.delay = 0.05
        self.started = 0
        self.cancelled = 0
        self.systems: list[str] = []

    async def generate_json(self, model: str, system: str, text: str, image_jpeg: bytes, schema: dict) -> dict:
        self.started += 1
        self.systems.append(system)
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


def test_auto_hint_at_stuck_is_the_one_prepared_from_the_earlier_frame(device: Device, ai: SlowAI) -> None:
    assert stay_still_until_frame_is_requested(device) == [None] * 8 + ["send_frame"]
    frame_id = device.frame()
    wait_until(lambda: ai.started == 1)
    assert [device.signal(second, STILL)["next_action"] for second in range(9, 12)] == [
        None,
        None,
        "send_frame_and_request_hint",
    ]
    hint = device.hint(frame_id)
    assert (hint["speech"], hint["source"], hint["level"], hint["state"]) == (HINT_SPEECH, "ai", 1, "speaking")
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
    assert device.hint(device.frame())["level"] == 1
    device.signal(15, MOVING)
    assert [device.signal(second, STILL)["next_action"] for second in range(16, 23)][-1] == "send_frame"
    frame_id = device.frame()
    wait_until(lambda: ai.started == 2)
    assert [device.signal(second, STILL)["state"] for second in range(23, 26)][-1] == "stuck"
    assert device.force_stuck(31)["state"] == "stuck"
    hint = device.hint(frame_id)
    assert (hint["level"], hint["source"]) == (2, "ai")
    assert ai.started == 3


def test_switching_persona_discards_the_old_prefetch_and_uses_the_new_style(device: Device, ai: SlowAI) -> None:
    ai.delay = 30
    stay_still_until_frame_is_requested(device)
    frame_id = device.frame()
    wait_until(lambda: ai.started == 1)
    assert get_persona("teacher").style_instruction in ai.systems[0]
    response = device.client.patch(
        f"/sessions/{device.session_id}/settings", json={"persona": "ikemen"}, headers=device.headers
    )
    assert response.status_code == 200
    wait_until(lambda: ai.cancelled == 1)
    ai.delay = 0
    for second in range(9, 12):
        device.signal(second, STILL)
    hint = device.hint(frame_id)
    assert (hint["speech"], hint["display"], hint["source"]) == (HINT_SPEECH, HINT_SPEECH, "ai")
    assert ai.started == 2
    assert get_persona("ikemen").style_instruction in ai.systems[-1]
    assert get_persona("teacher").style_instruction not in ai.systems[-1]
