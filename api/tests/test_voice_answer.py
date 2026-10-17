import pytest
from conftest import Device

ANSWER = "移項は、項を反対の辺に移すこと。符号が変わるよ"


class ListeningAI:
    def __init__(self) -> None:
        self.respond = True
        self.requests: list[str] = []

    async def generate_json(self, model: str, system: str, text: str, image_jpeg: bytes, schema: dict) -> dict:
        self.requests.append(text)
        return {
            "problem_text": "2x - 7 = 4x + 3",
            "final_answer": "x = -5",
            "key_values": ["-2x = 10"],
            "respond": self.respond,
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


def test_question_is_answered_with_an_explanation_and_recorded_as_voice(device: Device, ai: ListeningAI) -> None:
    hint = device.hint(start_watching(device), trigger="voice", utterance="移項って何？")
    assert (hint["speech"], hint["source"], hint["state"]) == (ANSWER, "gpt", "speaking")
    assert "移項って何？" in ai.requests[0]
    assert [(recorded["trigger"], recorded["display"]) for recorded in device.recorded_hints()] == [("voice", ANSWER)]


def test_talk_that_is_not_for_the_tutor_gets_no_answer_and_leaves_no_trace(device: Device, ai: ListeningAI) -> None:
    ai.respond = False
    frame_id = start_watching(device)
    hint = device.hint(frame_id, trigger="voice", utterance="お母さん、ご飯まだ？")
    assert (hint["speech"], hint["display"], hint["state"]) == (None, "", "watching")
    assert device.recorded_hints() == []
    ai.respond = True
    assert device.hint(frame_id, trigger="voice", utterance="移項って何？")["speech"] == ANSWER
