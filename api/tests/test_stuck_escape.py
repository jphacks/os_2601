from dataclasses import replace

import pytest
from conftest import Device, ScriptedAI, ai_hint

from app.state import CheckRequested, step


@pytest.fixture
def ai() -> ScriptedAI:
    return ScriptedAI(ai_hint("右辺に移したときの符号を見てみて"))


def test_check_is_accepted_while_stuck_and_the_late_auto_hint_is_dropped(device: Device, ai: ScriptedAI) -> None:
    frame_id = device.start_watching()
    assert device.force_stuck(2)["state"] == "stuck"
    response = device.client.post(f"/sessions/{device.session_id}/check", json={"frame_id": frame_id}, headers=device.headers)
    assert response.status_code == 200
    late = device.client.post(
        f"/sessions/{device.session_id}/hints", json={"trigger": "auto", "frame_id": frame_id}, headers=device.headers
    )
    assert late.status_code == 409


def test_advance_is_accepted_while_stuck(device: Device, ai: ScriptedAI) -> None:
    device.start_watching()
    assert device.force_stuck(2)["state"] == "stuck"
    response = device.client.post(f"/sessions/{device.session_id}/advance", headers=device.headers)
    assert (response.status_code, response.json()["state"], response.json()["current_problem_no"]) == (200, "watching", 2)


def test_a_hint_abandoned_because_the_persona_changed_does_not_block_the_next_request(device: Device, ai: ScriptedAI) -> None:
    frame_id = device.start_watching()
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


def test_an_auto_hint_finished_after_check_is_dropped_and_check_proceeds(device: Device, ai: ScriptedAI) -> None:
    frame_id = device.start_watching()
    assert device.force_stuck(2)["state"] == "stuck"
    store = device.client.app.state.context.store

    def check_during_generation() -> None:
        session = store.get(device.session_id)
        store.put(step(session, CheckRequested(), session.last_signal_at, device.client.app.state.context.thresholds)[0])

    ai.on_call = check_during_generation
    late = device.client.post(
        f"/sessions/{device.session_id}/hints", json={"trigger": "auto", "frame_id": frame_id}, headers=device.headers
    )
    assert late.status_code == 409
    assert store.get(device.session_id).state == "checking"
    assert device.recorded_hints() == []


def test_asking_if_correct_holds_and_then_releases_the_hint_lock(device: Device, ai: ScriptedAI) -> None:
    frame_id = device.start_watching()
    body = {"trigger": "voice", "frame_id": frame_id, "utterance": "これで合ってる？"}
    assert device.client.post(f"/sessions/{device.session_id}/hints", json=body, headers=device.headers).status_code == 200
    assert device.client.app.state.context.store.get(device.session_id).pending_until is None
