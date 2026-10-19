import json
from dataclasses import replace
from pathlib import Path

import pytest
from conftest import OPERATOR_KEY, Device, ScriptedAI
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def ai() -> ScriptedAI:
    return ScriptedAI({"readable": True, "final_answer_seen": "x = -5", "verdict": "correct"})


def check(device: Device) -> dict:
    device.signal(0, 0.05)
    frame_id = device.frame()
    response = device.client.post(f"/sessions/{device.session_id}/check", json={"frame_id": frame_id}, headers=device.headers)
    assert response.status_code == 200
    return response.json()


def test_correct_moves_to_the_next_problem_and_records_the_check(device: Device) -> None:
    result = check(device)
    assert (result["verdict"], result["speech"], result["problem_no"], result["next_problem_no"]) == ("correct", "正解。その調子", 1, 2)
    detail = device.client.get(f"/sessions/{device.session_id}", headers=device.headers).json()
    assert (detail["problems"][0]["status"], detail["problems"][0]["check"]["verdict"]) == ("done", "correct")
    assert detail["current_problem_no"] == 2


def test_incorrect_stays_on_the_problem(device: Device, ai: ScriptedAI) -> None:
    ai.reply["verdict"] = "incorrect"
    result = check(device)
    assert (result["speech"], result["next_problem_no"], result["state"]) == ("もう一回、途中の式を見てみて", 1, "speaking")


def test_the_answer_the_ai_read_is_never_in_the_response_or_the_record(device: Device) -> None:
    result = check(device)
    assert set(result) == {"check_id", "problem_no", "verdict", "speech", "display", "next_problem_no", "state"}
    detail = device.client.get(f"/sessions/{device.session_id}", headers=device.headers).json()
    assert "-5" not in json.dumps(result) and "-5" not in json.dumps(detail)


def test_before_any_frame_is_sent_the_check_says_it_could_not_read(device: Device) -> None:
    device.signal(0, 0.05)
    response = device.client.post(f"/sessions/{device.session_id}/check", json={"frame_id": "frm_none"}, headers=device.headers)
    assert response.status_code == 200
    assert (response.json()["verdict"], response.json()["speech"]) == ("unreadable", "うまく読めなかった。もう一回、できたを押してみて")


def test_sessions_come_back_after_the_app_restarts(device: Device) -> None:
    check(device)
    with TestClient(create_app()) as restarted:
        response = restarted.get(f"/sessions/{device.session_id}", headers=device.headers)
    assert response.status_code == 200
    detail = response.json()
    assert (detail["state"], detail["current_problem_no"], detail["problems"][0]["check"]["verdict"]) == ("watching", 2, "correct")


def test_a_broken_save_file_is_set_aside_and_the_app_still_starts(device: Device, tmp_path: Path) -> None:
    (tmp_path / "tonari.json").write_text('{"sessions": {"ses_x": {"session_id": "ses_x"}}}')
    with TestClient(create_app()) as restarted:
        assert restarted.get("/sessions", headers={"X-Operator-Key": OPERATOR_KEY}).json() == {"sessions": []}
    assert len(list(tmp_path.glob("tonari.*.broken"))) == 1


def test_a_save_writes_changed_sessions_and_drops_removed_ones(device: Device, tmp_path: Path) -> None:
    store = device.client.app.state.context.store
    store.save()
    session = store.get(device.session_id)
    session.learner_label = "変えた"
    store.put(session)
    other = replace(session, session_id="ses_other", learner_label="消す")
    store.put(other)
    store.save()
    store.remove("ses_other")
    store.save()
    saved = json.loads((tmp_path / "tonari.json").read_text())
    assert {session_id: body["learner_label"] for session_id, body in saved["sessions"].items()} == {device.session_id: "変えた"}


@pytest.mark.parametrize("content", ['{"sessions": []}', '{"sessions": "x"}', "not json"])
def test_any_unreadable_save_file_is_set_aside(device: Device, tmp_path: Path, content: str) -> None:
    (tmp_path / "tonari.json").write_text(content)
    with TestClient(create_app()) as restarted:
        assert restarted.get("/sessions", headers={"X-Operator-Key": OPERATOR_KEY}).json() == {"sessions": []}
    assert [path.read_text() for path in tmp_path.glob("tonari.*.broken")] == [content]


def test_ended_sessions_are_listed_without_being_advanced(device: Device) -> None:
    device.client.post(f"/sessions/{device.session_id}/end", headers=device.headers)
    store = device.client.app.state.context.store
    ended = store.get(device.session_id)
    device.client.get("/sessions", headers={"X-Operator-Key": OPERATOR_KEY})
    assert store.get(device.session_id) is ended


def test_operator_endpoints_need_the_key_and_device_endpoints_need_the_token(device: Device) -> None:
    assert device.client.get("/sessions").status_code == 401
    assert device.client.get("/sessions", headers={"X-Operator-Key": OPERATOR_KEY}).status_code == 200
    assert device.client.get(f"/sessions/{device.session_id}").status_code == 401
    operator = {"X-Operator-Key": OPERATOR_KEY}
    assert device.client.post(f"/sessions/{device.session_id}/check", json={"frame_id": "frm_x"}, headers=operator).status_code == 403
    other = device.client.post("/sessions", json={"worksheet_id": "FREE", "mode": "live"}, headers=operator).json()
    other_token = {"Authorization": f"Bearer {other['session_token']}"}
    assert device.client.get(f"/sessions/{device.session_id}", headers=other_token).status_code == 401
    assert device.client.post(f"/sessions/{device.session_id}/check", json={"frame_id": "frm_x"}, headers=other_token).status_code == 401
    assert device.client.get(f"/sessions/{device.session_id}", headers={"Authorization": "Bearer tok_wrong"}).status_code == 401
