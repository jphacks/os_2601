from collections.abc import Callable

import pytest
from conftest import OPERATOR_KEY, Device

from app.gemini import AIUnavailable
from app.hints import ANSWER_FALLBACK, CHECK_REPLY

ANSWER = "移項は、項を反対の辺に移すこと。符号が変わるよ"


class ListeningAI:
    def __init__(self) -> None:
        self.respond = True
        self.fail = False
        self.unreadable = False
        self.problem_text = "2x - 7 = 4x + 3"
        self.requests: list[str] = []
        self.on_call: Callable[[], None] = lambda: None

    async def generate_json(self, model: str, system: str, text: str, image_jpeg: bytes, schema: dict) -> dict:
        self.requests.append(text)
        self.on_call()
        if self.fail:
            raise AIUnavailable("timeout")
        return {
            "respond": self.respond,
            "readable": not self.unreadable,
            "unreadable_reason": "dark" if self.unreadable else "none",
            "problem_text": "" if self.unreadable else self.problem_text,
            "final_answer": "x = -5",
            "key_values": ["-2x = 10"],
            "stuck_point": "移項の意味",
            "speech": ANSWER if self.respond else "",
            "display": ANSWER if self.respond else "",
        }


@pytest.fixture
def ai() -> ListeningAI:
    return ListeningAI()


def start_watching(device: Device) -> str:
    device.signal(0, 0.05)
    device.signal(1, 0.05)
    return device.frame()


def ask(device: Device, frame_id: str, utterance: str):
    body = {"trigger": "voice", "frame_id": frame_id, "utterance": utterance}
    return device.client.post(f"/sessions/{device.session_id}/hints", json=body, headers=device.headers)


def test_question_is_answered_with_an_explanation_and_recorded_as_voice(device: Device, ai: ListeningAI) -> None:
    response = ask(device, start_watching(device), "移項って何？")
    assert (response.json()["speech"], response.json()["source"], response.json()["state"]) == (ANSWER, "ai", "speaking")
    assert response.json()["problem_text"] == "2x - 7 = 4x + 3"
    assert device.client.get(f"/sessions/{device.session_id}", headers=device.headers).json()["problems"][0]["problem_text"] == "2x - 7 = 4x + 3"
    assert "移項って何？" in ai.requests[0]
    assert [(recorded["trigger"], recorded["display"]) for recorded in device.recorded_hints()] == [("voice", ANSWER)]


def test_buttons_are_not_blocked_while_the_ai_considers_what_was_heard(device: Device, ai: ListeningAI) -> None:
    store = device.client.app.state.context.store
    waiting: list[object] = []
    ai.on_call = lambda: waiting.append(store.get(device.session_id).pending_until)
    ask(device, start_watching(device), "移項って何？")
    assert waiting == [None]


def test_talk_that_is_not_for_the_tutor_gets_no_content_and_leaves_no_trace(device: Device, ai: ListeningAI) -> None:
    ai.respond = False
    frame_id = start_watching(device)
    assert ask(device, frame_id, "お母さん、ご飯まだ？").status_code == 204
    assert device.recorded_hints() == []
    ai.respond = True
    assert ask(device, frame_id, "移項って何？").json()["speech"] == ANSWER


def test_when_the_ai_is_down_only_a_call_for_help_gets_a_fixed_reply(device: Device, ai: ListeningAI) -> None:
    ai.fail = True
    frame_id = start_watching(device)
    assert ask(device, frame_id, "お母さん、ご飯まだ？").status_code == 204
    reply = ask(device, frame_id, "これ分からない")
    assert (reply.json()["speech"], reply.json()["source"]) == (ANSWER_FALLBACK, "fallback")


def test_asking_if_it_is_correct_gets_the_fixed_reply_without_calling_the_ai(device: Device, ai: ListeningAI) -> None:
    reply = ask(device, start_watching(device), "これで合ってる？")
    assert (reply.json()["speech"], reply.json()["state"]) == (CHECK_REPLY, "speaking")
    assert ai.requests == []


@pytest.mark.parametrize(
    ("utterance", "stuck_points"),
    [("移項って何？", [{"label": "その他", "count": 1}]), ("これで合ってる？", [])],
)
def test_stuck_points_count_only_the_labels_the_ai_chose(device: Device, ai: ListeningAI, utterance: str, stuck_points: list[dict]) -> None:
    ask(device, start_watching(device), utterance)
    assert device.client.get(f"/sessions/{device.session_id}", headers=device.headers).json()["stuck_points"] == stuck_points


def test_scripted_session_does_not_answer_what_it_hears(device: Device, ai: ListeningAI) -> None:
    created = device.client.post(
        "/sessions", json={"worksheet_id": "FREE", "mode": "scripted"}, headers={"X-Operator-Key": OPERATOR_KEY}
    ).json()
    scripted = Device(device.client, created["session_id"], {"Authorization": f"Bearer {created['session_token']}"})
    assert ask(scripted, start_watching(scripted), "これ分からない").status_code == 204
    assert ai.requests == []


def read(device: Device, frame_id: str):
    return device.client.post(f"/sessions/{device.session_id}/problem", json={"frame_id": frame_id}, headers=device.headers)


def test_problem_text_is_read_from_the_latest_frame_without_a_hint(device: Device, ai: ListeningAI) -> None:
    frame_id = start_watching(device)
    assert read(device, frame_id).json() == {"problem_no": 1, "problem_text": "2x - 7 = 4x + 3", "state": "watching"}
    assert "問題文" in ai.requests[0]
    assert device.client.get(f"/sessions/{device.session_id}", headers=device.headers).json()["problems"][0]["problem_text"] == "2x - 7 = 4x + 3"
    assert device.recorded_hints() == []


def test_unreadable_frame_keeps_the_problem_text_and_a_new_text_resets_the_leak_strings(device: Device, ai: ListeningAI) -> None:
    frame_id = start_watching(device)
    ask(device, frame_id, "移項って何？")
    store = device.client.app.state.context.store
    assert store.get(device.session_id).problems[0].leak_strings != []
    ai.unreadable = True
    assert read(device, frame_id).json()["problem_text"] == "2x - 7 = 4x + 3"
    ai.unreadable = False
    ai.problem_text = "3x + 2 = 8"
    assert read(device, frame_id).json()["problem_text"] == "3x + 2 = 8"
    assert store.get(device.session_id).problems[0].leak_strings == []


def test_the_same_problem_read_with_other_spacing_keeps_the_leak_strings(device: Device, ai: ListeningAI) -> None:
    frame_id = start_watching(device)
    ask(device, frame_id, "移項って何？")
    store = device.client.app.state.context.store
    leaks = store.get(device.session_id).problems[0].leak_strings
    ai.problem_text = "2x-7=4x+3"
    assert read(device, frame_id).json()["problem_text"] == "2x-7=4x+3"
    assert store.get(device.session_id).problems[0].leak_strings == leaks != []


def test_reading_after_the_session_ended_is_rejected(device: Device, ai: ListeningAI) -> None:
    frame_id = start_watching(device)
    device.client.post(f"/sessions/{device.session_id}/end", headers=device.headers)
    assert read(device, frame_id).status_code == 409
