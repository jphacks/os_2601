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
        self.requests: list[str] = []
        self.on_call: Callable[[], None] = lambda: None

    async def generate_json(self, model: str, system: str, text: str, image_jpeg: bytes, schema: dict) -> dict:
        self.requests.append(text)
        self.on_call()
        if self.fail:
            raise AIUnavailable("timeout")
        return {
            "respond": self.respond,
            "problem_text": "2x - 7 = 4x + 3",
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
    assert (response.json()["speech"], response.json()["source"], response.json()["state"]) == (ANSWER, "gpt", "speaking")
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


def test_scripted_session_does_not_answer_what_it_hears(device: Device, ai: ListeningAI) -> None:
    created = device.client.post(
        "/sessions", json={"worksheet_id": "FREE", "mode": "scripted"}, headers={"X-Operator-Key": OPERATOR_KEY}
    ).json()
    scripted = Device(device.client, created["session_id"], {"Authorization": f"Bearer {created['session_token']}"})
    assert ask(scripted, start_watching(scripted), "これ分からない").status_code == 204
    assert ai.requests == []
