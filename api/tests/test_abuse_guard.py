import asyncio
from datetime import timedelta
from pathlib import Path

import httpx
import pytest
from conftest import Device

from app import main, routes
from app.leak import leak_strings, normalize

WAV = b"RIFF\x00\x00\x00\x00WAVE"


class SlowAI:
    def __init__(self) -> None:
        self.calls = 0

    async def generate_json(self, model: str, system: str, text: str, image_jpeg: bytes, schema: dict) -> dict:
        self.calls += 1
        await asyncio.sleep(0.05)
        return {"problem_text": "2x = 4", "readable": True, "respond": False, "verdict": "correct", "final_answer_seen": ""}


class FakeVoice:
    async def synthesize(self, text: str, character: str) -> bytes:
        return WAV


@pytest.fixture
def ai() -> SlowAI:
    return SlowAI()


def opened(device: Device) -> tuple[str, dict[str, str]]:
    created = device.client.post("/sessions/open", headers={"x-forwarded-for": "203.0.113.7"}).json()
    return created["session_id"], {"Authorization": f"Bearer {created['session_token']}"}


def test_an_expired_open_session_cannot_read_problems_or_speak(device: Device) -> None:
    device.client.app.state.context.voice = FakeVoice()
    session_id, headers = opened(device)
    device.now += timedelta(minutes=31)
    assert device.client.post(f"/sessions/{session_id}/problem", json={"frame_id": "frm_x"}, headers=headers).status_code == 409
    device.now += timedelta(minutes=2)
    assert device.client.post(f"/sessions/{session_id}/tts", json={"text": "見てみて"}, headers=headers).status_code == 409


def test_parallel_problem_reads_call_the_ai_once(device: Device, ai: SlowAI) -> None:
    device.signal(0, 0.05)
    device.frame()

    async def read_ten() -> list[int]:
        transport = httpx.ASGITransport(app=device.client.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            path = f"/sessions/{device.session_id}/problem"
            responses = await asyncio.gather(*(client.post(path, json={"frame_id": "frm_x"}, headers=device.headers) for _ in range(10)))
        return [response.status_code for response in responses]

    statuses = asyncio.run(read_ten())
    assert statuses.count(200) == 1
    assert statuses.count(429) == 9
    assert ai.calls == 1


def test_a_session_can_call_the_ai_only_so_often_a_minute(device: Device, ai: SlowAI) -> None:
    device.signal(0, 0.05)
    device.frame()
    path = f"/sessions/{device.session_id}/problem"
    statuses = [device.client.post(path, json={"frame_id": "frm_x"}, headers=device.headers).status_code for _ in range(13)]
    assert statuses == [200] * 12 + [429]
    device.now += timedelta(minutes=1, seconds=1)
    assert device.client.post(path, json={"frame_id": "frm_x"}, headers=device.headers).status_code == 200


def test_a_session_can_speak_only_so_often_a_minute(device: Device) -> None:
    device.client.app.state.context.voice = FakeVoice()
    path = f"/sessions/{device.session_id}/tts"
    statuses = [device.client.post(path, json={"text": "見てみて"}, headers=device.headers).status_code for _ in range(41)]
    assert statuses == [200] * 40 + [429]


def test_a_huge_frame_is_refused_before_it_is_read(device: Device) -> None:
    response = device.client.post(
        "/sessions/ses_none/frames", content=b"x", headers={"content-length": str(10 * 1024 * 1024), "content-type": "multipart/form-data; boundary=b"}
    )
    assert response.status_code == 413


def test_frames_of_forgotten_sessions_are_dropped(device: Device) -> None:
    session_id, headers = opened(device)
    files = {"frame": ("frame.jpg", b"\xff\xd8jpeg", "image/jpeg")}
    assert device.client.post(f"/sessions/{session_id}/frames", files=files, headers=headers).status_code == 200
    device.now += timedelta(minutes=31) + routes.OPEN_SESSION_KEPT_FOR
    device.client.post("/sessions/open", headers={"x-forwarded-for": "203.0.113.8"})
    context = device.client.app.state.context
    assert context.store.get(session_id) is None
    assert session_id not in context.frames


def test_strange_answers_do_not_break_the_leak_check() -> None:
    assert "x=" + "9" * 400 + "/3" in leak_strings("x = " + "9" * 400 + "/3", [])
    assert normalize("1二分の3") == "3/12"
    assert normalize("二十分の一") == "1/20"


def test_an_unknown_max_level_stops_the_app_at_startup(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    settings = tmp_path / "settings.yaml"
    settings.write_text(main.SETTINGS_PATH.read_text(encoding="utf-8").replace("max_level: 2", "max_level: 3"), encoding="utf-8")
    monkeypatch.setattr(main, "SETTINGS_PATH", settings)
    with pytest.raises(ValueError, match="max_level"):
        main.create_app()
