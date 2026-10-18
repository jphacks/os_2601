import json

import pytest
from conftest import OPERATOR_KEY, Device
from fastapi.testclient import TestClient

from app.main import create_app


class JudgingAI:
    def __init__(self) -> None:
        self.verdict = "correct"

    async def generate_json(self, model: str, system: str, text: str, image_jpeg: bytes, schema: dict) -> dict:
        return {"readable": True, "final_answer_seen": "x = -5", "verdict": self.verdict}


@pytest.fixture
def ai() -> JudgingAI:
    return JudgingAI()


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


def test_incorrect_stays_on_the_problem(device: Device, ai: JudgingAI) -> None:
    ai.verdict = "incorrect"
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
