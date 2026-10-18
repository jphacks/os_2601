from datetime import timedelta

import pytest
from conftest import Device

from app import routes


@pytest.fixture
def ai() -> None:
    return None


def open_session(device: Device, ip: str = "203.0.113.1"):
    return device.client.post("/sessions/open", headers={"x-forwarded-for": ip})


def test_anyone_can_open_a_session_and_start(device: Device) -> None:
    response = open_session(device)
    created = response.json()
    assert response.status_code == 201
    assert (created["mode"], created["state"], created["worksheet"]["worksheet_id"]) == ("live", "created", "FREE")
    headers = {"Authorization": f"Bearer {created['session_token']}"}
    detail = device.client.get(f"/sessions/{created['session_id']}", headers=headers).json()
    assert detail["learner_label"] == "自分で始めた"


def test_an_ip_can_open_three_sessions_a_minute(device: Device) -> None:
    assert [open_session(device).status_code for _ in range(4)] == [201, 201, 201, 429]
    assert open_session(device, ip="203.0.113.2").status_code == 201
    device.now += timedelta(minutes=1, seconds=1)
    assert open_session(device).status_code == 201


def test_an_opened_session_ends_by_itself_after_thirty_minutes(device: Device) -> None:
    created = open_session(device).json()
    headers = {"Authorization": f"Bearer {created['session_token']}"}
    device.now += timedelta(minutes=29)
    assert device.client.get(f"/sessions/{created['session_id']}", headers=headers).json()["state"] == "created"
    device.now += timedelta(minutes=2)
    assert device.client.get(f"/sessions/{created['session_id']}", headers=headers).json()["state"] == "ended"


def test_the_open_door_can_be_closed(device: Device) -> None:
    device.client.app.state.context.open_sessions = False
    assert open_session(device).status_code == 404


def test_operator_sessions_never_end_by_themselves(device: Device) -> None:
    device.now += timedelta(hours=2)
    assert device.client.get(f"/sessions/{device.session_id}", headers=device.headers).json()["state"] != "ended"
    assert timedelta(minutes=30) == routes.OPEN_SESSION_LIFETIME
