import pytest
from conftest import OPERATOR_KEY, Device, ScriptedAI

from app.gemini import AIUnavailable
from app.hints import ANSWER_FALLBACK, CHECK_REPLY

ANSWER = "移項は、項を反対の辺に移すこと。符号が変わるよ"


def heard(respond: bool = True, unreadable: bool = False, problem_text: str = "2x - 7 = 4x + 3") -> dict:
    return {
        "respond": respond,
        "readable": not unreadable,
        "unreadable_reason": "dark" if unreadable else "none",
        "problem_text": "" if unreadable else problem_text,
        "final_answer": "x = -5",
        "key_values": ["-2x = 10"],
        "stuck_point": "移項の意味",
        "speech": ANSWER if respond else "",
        "display": ANSWER if respond else "",
    }


@pytest.fixture
def ai() -> ScriptedAI:
    return ScriptedAI(heard())


def ask(device: Device, frame_id: str, utterance: str):
    body = {"trigger": "voice", "frame_id": frame_id, "utterance": utterance}
    return device.client.post(f"/sessions/{device.session_id}/hints", json=body, headers=device.headers)


def test_question_is_answered_with_an_explanation_and_recorded_as_voice(device: Device, ai: ScriptedAI) -> None:
    response = ask(device, device.start_watching(), "移項って何？")
    assert (response.json()["speech"], response.json()["source"], response.json()["state"]) == (ANSWER, "ai", "speaking")
    assert response.json()["problem_text"] == "2x - 7 = 4x + 3"
    assert device.client.get(f"/sessions/{device.session_id}", headers=device.headers).json()["problems"][0]["problem_text"] == "2x - 7 = 4x + 3"
    assert "移項って何？" in ai.requests[0]
    assert [(recorded["trigger"], recorded["display"]) for recorded in device.recorded_hints()] == [("voice", ANSWER)]


def test_buttons_are_not_blocked_while_the_ai_considers_what_was_heard(device: Device, ai: ScriptedAI) -> None:
    store = device.client.app.state.context.store
    waiting: list[object] = []
    ai.on_call = lambda: waiting.append(store.get(device.session_id).pending_until)
    ask(device, device.start_watching(), "移項って何？")
    assert waiting == [None]


def test_talk_that_is_not_for_the_tutor_gets_no_content_and_leaves_no_trace(device: Device, ai: ScriptedAI) -> None:
    ai.reply = heard(respond=False)
    frame_id = device.start_watching()
    assert ask(device, frame_id, "お母さん、ご飯まだ？").status_code == 204
    assert device.recorded_hints() == []
    ai.reply = heard()
    assert ask(device, frame_id, "移項って何？").json()["speech"] == ANSWER


def test_when_the_ai_is_down_only_a_call_for_help_gets_a_fixed_reply(device: Device, ai: ScriptedAI) -> None:
    ai.error = AIUnavailable("timeout")
    frame_id = device.start_watching()
    assert ask(device, frame_id, "お母さん、ご飯まだ？").status_code == 204
    reply = ask(device, frame_id, "これ分からない")
    assert (reply.json()["speech"], reply.json()["source"]) == (ANSWER_FALLBACK, "fallback")


def test_asking_if_it_is_correct_gets_the_fixed_reply_without_calling_the_ai(device: Device, ai: ScriptedAI) -> None:
    reply = ask(device, device.start_watching(), "これで合ってる？")
    assert (reply.json()["speech"], reply.json()["state"]) == (CHECK_REPLY, "speaking")
    assert ai.requests == []


@pytest.mark.parametrize(
    ("utterance", "stuck_points"),
    [("移項って何？", [{"label": "その他", "count": 1}]), ("これで合ってる？", [])],
)
def test_stuck_points_count_only_the_labels_the_ai_chose(device: Device, ai: ScriptedAI, utterance: str, stuck_points: list[dict]) -> None:
    ask(device, device.start_watching(), utterance)
    assert device.client.get(f"/sessions/{device.session_id}", headers=device.headers).json()["stuck_points"] == stuck_points


def test_scripted_session_does_not_answer_what_it_hears(device: Device, ai: ScriptedAI) -> None:
    created = device.client.post(
        "/sessions", json={"worksheet_id": "FREE", "mode": "scripted"}, headers={"X-Operator-Key": OPERATOR_KEY}
    ).json()
    scripted = Device(device.client, created["session_id"], {"Authorization": f"Bearer {created['session_token']}"})
    assert ask(scripted, scripted.start_watching(), "これ分からない").status_code == 204
    assert ai.requests == []


def read(device: Device, frame_id: str):
    return device.client.post(f"/sessions/{device.session_id}/problem", json={"frame_id": frame_id}, headers=device.headers)


def test_problem_text_is_read_from_the_latest_frame_without_a_hint(device: Device, ai: ScriptedAI) -> None:
    frame_id = device.start_watching()
    assert read(device, frame_id).json() == {"problem_no": 1, "problem_text": "2x - 7 = 4x + 3", "state": "watching"}
    assert "問題文" in ai.requests[0]
    assert device.client.get(f"/sessions/{device.session_id}", headers=device.headers).json()["problems"][0]["problem_text"] == "2x - 7 = 4x + 3"
    assert device.recorded_hints() == []


def test_unreadable_frame_keeps_the_problem_text_and_a_new_text_resets_the_leak_strings(device: Device, ai: ScriptedAI) -> None:
    frame_id = device.start_watching()
    ask(device, frame_id, "移項って何？")
    store = device.client.app.state.context.store
    assert store.get(device.session_id).problems[0].leak_strings != []
    ai.reply = heard(unreadable=True)
    assert read(device, frame_id).json()["problem_text"] == "2x - 7 = 4x + 3"
    ai.reply = heard(problem_text="3x + 2 = 8")
    assert read(device, frame_id).json()["problem_text"] == "3x + 2 = 8"
    assert store.get(device.session_id).problems[0].leak_strings == []


def test_the_same_problem_read_with_other_spacing_keeps_the_leak_strings(device: Device, ai: ScriptedAI) -> None:
    frame_id = device.start_watching()
    ask(device, frame_id, "移項って何？")
    store = device.client.app.state.context.store
    leaks = store.get(device.session_id).problems[0].leak_strings
    ai.reply = heard(problem_text="2x-7=4x+3")
    assert read(device, frame_id).json()["problem_text"] == "2x-7=4x+3"
    assert store.get(device.session_id).problems[0].leak_strings == leaks != []


def test_reading_after_the_session_ended_is_rejected(device: Device, ai: ScriptedAI) -> None:
    frame_id = device.start_watching()
    device.client.post(f"/sessions/{device.session_id}/end", headers=device.headers)
    assert read(device, frame_id).status_code == 409
