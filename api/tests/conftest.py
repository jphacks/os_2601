from collections.abc import Iterator
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
