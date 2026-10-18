import pytest
from conftest import OPERATOR_KEY, Device


@pytest.fixture
def ai() -> object:
    return object()


def test_health_reports_whether_the_ai_key_is_set(device: Device) -> None:
    assert device.client.get("/healthz").json() == {"ok": True, "ai": "ok", "mode_default": "live"}


def test_only_the_free_worksheet_can_start_a_session(device: Device) -> None:
    response = device.client.post(
        "/sessions", json={"worksheet_id": "WS-01", "mode": "live"}, headers={"X-Operator-Key": OPERATOR_KEY}
    )
    assert response.status_code == 422


def test_advance_needs_no_body(device: Device) -> None:
    device.signal(0, 0.05)
    response = device.client.post(f"/sessions/{device.session_id}/advance", headers=device.headers)
    assert (response.status_code, response.json()["current_problem_no"]) == (200, 2)


def test_signals_still_accept_the_old_device_time(device: Device) -> None:
    body = {"ts": "2026-10-17T07:00:00Z", "motion": 0.05, "camera_ok": True}
    assert device.client.post(f"/sessions/{device.session_id}/signals", json=body, headers=device.headers).status_code == 200
