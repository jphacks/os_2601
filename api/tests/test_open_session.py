from datetime import timedelta

import pytest
from conftest import OPERATOR_KEY, Device

from app import limits


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


def test_an_ip_can_open_ten_sessions_a_minute(device: Device) -> None:
    limit = limits.OPEN_SESSIONS_PER_MINUTE
    assert [open_session(device).status_code for _ in range(limit + 1)] == [201] * limit + [429]
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
    assert device.client.app.state.context.store.get(device.session_id).auto_end_at is None


def test_the_rightmost_forwarded_address_is_the_one_counted(device: Device) -> None:
    limit = limits.OPEN_SESSIONS_PER_MINUTE
    statuses = [open_session(device, ip=f"10.0.0.{number}, 203.0.113.9").status_code for number in range(limit + 1)]
    assert statuses == [201] * limit + [429]


def test_all_addresses_together_are_capped(device: Device) -> None:
    statuses = [open_session(device, ip=f"203.0.113.{number}").status_code for number in range(limits.OPEN_SESSIONS_PER_MINUTE_TOTAL + 1)]
    assert statuses[-1] == 429
    assert len(device.client.app.state.context.opened_at) == limits.OPEN_SESSIONS_PER_MINUTE_TOTAL


def test_expired_open_sessions_show_as_ended_in_the_list_and_are_forgotten_after_a_day(device: Device) -> None:
    created = open_session(device).json()
    operator = {"X-Operator-Key": OPERATOR_KEY}
    device.now += timedelta(minutes=31)
    listed = {item["session_id"]: item["state"] for item in device.client.get("/sessions", headers=operator).json()["sessions"]}
    assert listed[created["session_id"]] == "ended"
    device.now += timedelta(days=1)
    open_session(device, ip="203.0.113.50")
    assert device.client.app.state.context.store.get(created["session_id"]) is None
