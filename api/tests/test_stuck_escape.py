from dataclasses import replace

import pytest
from conftest import Device
from test_voice_answer import ListeningAI, start_watching


@pytest.fixture
def ai() -> ListeningAI:
    return ListeningAI()


def test_check_is_accepted_while_stuck_and_the_late_auto_hint_is_dropped(device: Device, ai: ListeningAI) -> None:
    frame_id = start_watching(device)
    assert device.force_stuck(2)["state"] == "stuck"
    response = device.client.post(f"/sessions/{device.session_id}/check", json={"frame_id": frame_id}, headers=device.headers)
    assert response.status_code == 200
    late = device.client.post(
        f"/sessions/{device.session_id}/hints", json={"trigger": "auto", "frame_id": frame_id}, headers=device.headers
    )
    assert late.status_code == 409


def test_advance_is_accepted_while_stuck(device: Device, ai: ListeningAI) -> None:
    start_watching(device)
    assert device.force_stuck(2)["state"] == "stuck"
    response = device.client.post(f"/sessions/{device.session_id}/advance", headers=device.headers)
    assert (response.status_code, response.json()["state"], response.json()["current_problem_no"]) == (200, "watching", 2)


def test_a_hint_abandoned_because_the_persona_changed_does_not_block_the_next_request(device: Device, ai: ListeningAI) -> None:
    frame_id = start_watching(device)
    store = device.client.app.state.context.store

    def switch_during_generation() -> None:
        old = store.get(device.session_id)
        store.put(replace(old, settings=replace(old.settings, persona="ikemen")))

    ai.on_call = switch_during_generation
    aborted = device.client.post(
        f"/sessions/{device.session_id}/hints", json={"trigger": "manual", "frame_id": frame_id}, headers=device.headers
    )
    assert aborted.status_code == 409
    ai.on_call = lambda: None
    retry = device.client.post(
        f"/sessions/{device.session_id}/hints", json={"trigger": "manual", "frame_id": frame_id}, headers=device.headers
    )
    assert retry.status_code == 200
