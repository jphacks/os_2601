import pytest
from conftest import OPERATOR_KEY, Device

from app.check import CORRECT_TEXT, FAILED_TEXT, INCORRECT_TEXT
from app.store import SessionStore


class JudgingAI:
    def __init__(self) -> None:
        self.verdict = "correct"

    async def generate_json(self, model: str, system: str, text: str, image_jpeg: bytes, schema: dict) -> dict:
        return {"readable": True, "final_answer_seen": "", "verdict": self.verdict}


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
    assert (result["verdict"], result["speech"], result["problem_no"], result["next_problem_no"]) == ("correct", CORRECT_TEXT, 1, 2)
    detail = device.client.get(f"/sessions/{device.session_id}", headers=device.headers).json()
    assert (detail["problems"][0]["status"], detail["problems"][0]["check"]["verdict"]) == ("done", "correct")
    assert detail["current_problem_no"] == 2


def test_incorrect_stays_on_the_problem(device: Device, ai: JudgingAI) -> None:
    ai.verdict = "incorrect"
    result = check(device)
    assert (result["speech"], result["next_problem_no"], result["state"]) == (INCORRECT_TEXT, 1, "speaking")


def test_the_answer_value_is_never_in_the_response(device: Device) -> None:
    result = check(device)
    assert set(result) == {"check_id", "problem_no", "verdict", "speech", "display", "next_problem_no", "state"}


def test_without_a_frame_the_check_says_it_could_not_read(device: Device) -> None:
    device.signal(0, 0.05)
    response = device.client.post(f"/sessions/{device.session_id}/check", json={"frame_id": "frm_none"}, headers=device.headers)
    assert (response.json()["verdict"], response.json()["speech"]) == ("unreadable", FAILED_TEXT)


def test_saved_sessions_come_back_after_a_restart(device: Device) -> None:
    check(device)
    store: SessionStore = device.client.app.state.context.store
    restarted = SessionStore(store._path)
    restarted.load()
    session = restarted.get(device.session_id)
    assert session is not None
    assert (session.state, session.current_problem_no, session.problems[0].check.verdict) == ("watching", 2, "correct")


def test_operator_endpoints_need_the_key_and_device_endpoints_need_the_token(device: Device) -> None:
    assert device.client.get("/sessions").status_code == 401
    assert device.client.get("/sessions", headers={"X-Operator-Key": OPERATOR_KEY}).status_code == 200
    assert device.client.get(f"/sessions/{device.session_id}").status_code == 401
    operator = {"X-Operator-Key": OPERATOR_KEY}
    assert device.client.post(f"/sessions/{device.session_id}/check", json={"frame_id": "frm_x"}, headers=operator).status_code == 403
