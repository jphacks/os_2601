import base64
import json
from dataclasses import replace
from datetime import timedelta

import httpx
import pytest
from conftest import OPERATOR_KEY, Device, ScriptedAI

from app.gemini import Gemini
from app.personas import PERSONAS, get_persona


def analysis(speech="右辺に移したときの符号を見てみて", display="右辺に移した項の符号を確認してみて"):
    return {
        "readable": True, "unreadable_reason": "none",
        "problem_text": "2x - 7 = 4x + 3", "final_answer": "x = -5",
        "key_values": ["-2x = 10"], "written_lines": [],
        "stuck_point": "移項の符号", "speech": speech, "display": display,
    }


@pytest.fixture
def ai():
    return ScriptedAI(analysis())


def select(device, persona):
    return device.client.patch(
        f"/sessions/{device.session_id}/settings", json={"persona": persona}, headers=device.headers
    )


@pytest.mark.parametrize("persona", ["teacher", "ikemen"])
def test_selected_persona_uses_the_camera_and_keeps_answers_private(device: Device, ai, persona):
    assert select(device, persona).json()["settings"]["persona"] == persona
    initial = device.client.get(f"/sessions/{device.session_id}", headers=device.headers).json()
    assert initial["problems"][0]["problem_text"] is None
    speech = "右辺に移したときの符号を見てみましょう。" if persona == "teacher" else "右辺に移したときの符号を見てごらん。"
    display = "右辺に移した項の符号を確認してみましょう。" if persona == "teacher" else "右辺に移した項の符号を確認してみようか。"
    ai.reply = analysis(speech, display)
    result = device.hint(device.start_watching(), "manual")
    assert result["source"] == "ai"
    assert result["problem_text"] == "2x - 7 = 4x + 3"
    assert (result["speech"], result["display"]) == (speech, display)
    assert len(result["speech"]) <= 60 and len(result["display"]) <= 80
    assert len(ai.requests) == 1 and ai.frames[0] == b"\xff\xd8jpeg"
    assert get_persona(persona).style_instruction in ai.systems[0]
    detail = device.client.get(f"/sessions/{device.session_id}", headers=device.headers).json()
    assert detail["problems"][0]["problem_text"] == result["problem_text"]
    assert {option["id"] for option in detail["persona_options"]} == {"teacher", "ikemen"}
    assert next(option["end_message"] for option in detail["persona_options"] if option["id"] == persona) == PERSONAS[persona].end_message
    encoded = json.dumps([result, detail], ensure_ascii=False)
    assert "final_answer" not in encoded and "leak_strings" not in encoded and "key_values" not in encoded
    assert "x=-5" not in encoded and "-2x=10" not in encoded


@pytest.mark.parametrize("persona", ["teacher", "ikemen"])
def test_startup_read_remains_separate_from_the_persona_hint_and_keeps_analysis_private(device: Device, ai, persona):
    assert select(device, persona).status_code == 200
    frame_id = device.start_watching()
    read = device.client.post(
        f"/sessions/{device.session_id}/problem", headers=device.headers, json={"frame_id": frame_id}
    )
    assert read.status_code == 200
    assert read.json() == {"problem_no": 1, "problem_text": "2x - 7 = 4x + 3", "state": "watching"}
    assert len(ai.requests) == 1 and ai.frames[0] == b"\xff\xd8jpeg"
    assert set(ai.schemas[0]["properties"]) == {"paper_visible", "problem_text", "readable"}
    initial = device.client.get(f"/sessions/{device.session_id}", headers=device.headers).json()
    assert initial["problems"][0]["hints"] == []
    assert initial["problems"][0]["stuck_count"] == 0
    assert initial["stuck_points"] == []

    hint = device.hint(frame_id, "manual")
    assert hint["source"] == "ai"
    assert (hint["speech"], hint["display"]) == (ai.reply["speech"], ai.reply["display"])
    assert len(ai.requests) == 2
    assert "前に読み取った問題文：2x - 7 = 4x + 3" in ai.requests[1]
    assert {"speech", "display"} <= set(ai.schemas[1]["required"])
    assert get_persona(persona).style_instruction in ai.systems[1]
    detail = device.client.get(f"/sessions/{device.session_id}", headers=device.headers).json()
    assert detail["stuck_points"] == [{"label": "移項の符号", "count": 1}]
    encoded = json.dumps([read.json(), initial, hint, detail], ensure_ascii=False)
    for private_value in ("final_answer", "key_values", "leak_strings", "x=-5", "-2x=10"):
        assert private_value not in encoded


@pytest.mark.parametrize("persona", ["teacher", "ikemen"])
def test_only_generated_hints_add_labels_when_persona_fallbacks_are_recorded(device: Device, ai, persona):
    assert select(device, persona).status_code == 200
    frame_id = device.start_watching()
    assert device.hint(frame_id, "manual")["source"] == "ai"
    device.signal(20, 0.05)
    ai.reply = {**analysis(), "readable": False, "unreadable_reason": "dark"}
    unreadable = device.hint(frame_id, "manual")
    assert unreadable["source"] == "fallback"
    assert "明る" in unreadable["display"]
    device.signal(40, 0.05)
    check = device.hint(frame_id, "voice", "これで合ってる？")
    assert check["source"] == "fallback" and check["stuck_point"] == "答えの確認"
    assert len(ai.requests) == 2
    for response in (unreadable, check):
        assert response["speech"] == response["display"] and len(response["speech"]) <= 60
    detail = device.client.get(f"/sessions/{device.session_id}", headers=device.headers).json()
    assert [hint["source"] for hint in detail["problems"][0]["hints"]] == ["ai", "fallback", "fallback"]
    assert detail["stuck_points"] == [{"label": "移項の符号", "count": 1}]


def test_read_problem_survives_a_fallback_but_does_not_leak_into_the_next_problem(device: Device, ai):
    frame_id = device.start_watching()
    assert device.hint(frame_id, "manual")["problem_text"] == "2x - 7 = 4x + 3"
    device.signal(20, 0.05)
    ai.reply = {**analysis(), "readable": False, "unreadable_reason": "dark"}
    fallback = device.hint(frame_id, "manual")
    assert fallback["source"] == "fallback"
    assert fallback["problem_text"] == "2x - 7 = 4x + 3"
    advanced = device.client.post(f"/sessions/{device.session_id}/advance", headers=device.headers)
    assert advanced.status_code == 200 and advanced.json()["current_problem_no"] == 2
    detail = device.client.get(f"/sessions/{device.session_id}", headers=device.headers).json()
    assert detail["problems"][0]["problem_text"] == fallback["problem_text"]
    assert detail["problems"][1]["problem_text"] is None


def test_friend_is_rejected_by_both_create_and_patch(device: Device):
    assert select(device, "friend").status_code == 422
    response = device.client.post(
        "/sessions", json={"worksheet_id": "FREE", "mode": "live", "settings": {"persona": "friend"}},
        headers={"X-Operator-Key": OPERATOR_KEY},
    )
    assert response.status_code == 422
    assert device.client.get(f"/sessions/{device.session_id}", headers=device.headers).json()["settings"]["persona"] == "teacher"


def test_switch_is_rejected_while_normal_hint_is_pending(device: Device):
    device.start_watching()
    store = device.client.app.state.context.store
    session = store.get(device.session_id)
    store.put(replace(session, pending_until=device.now + timedelta(seconds=12)))
    assert select(device, "ikemen").status_code == 409
    assert store.get(device.session_id).settings.persona == "teacher"


def test_stale_voice_result_cannot_use_an_earlier_persona(device: Device, ai):
    frame = device.start_watching()
    ai.reply = {**analysis(), "respond": True, "speech": "反対の辺に移すときは、符号を確かめましょう。", "display": "反対の辺に移すときは、符号を確かめましょう。"}
    store = device.client.app.state.context.store

    def switch_during_generation():
        old = store.get(device.session_id)
        store.put(replace(old, settings=replace(old.settings, persona="ikemen")))

    ai.on_call = switch_during_generation
    response = device.client.post(
        f"/sessions/{device.session_id}/hints", headers=device.headers,
        json={"trigger": "voice", "frame_id": frame, "utterance": "移項って何？"},
    )
    assert response.status_code == 204
    assert not device.recorded_hints()


def test_gemini_wire_format_sends_one_jpeg_and_structured_result_reaches_response(device: Device):
    sent = []

    def transport(request):
        sent.append(json.loads(request.content))
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": json.dumps(analysis(), ensure_ascii=False)}]}}]})

    gemini = Gemini("test-only-placeholder")
    gemini._client = httpx.AsyncClient(transport=httpx.MockTransport(transport))
    device.client.app.state.context.ai = gemini
    select(device, "ikemen")
    result = device.hint(device.start_watching(), "manual")
    assert len(sent) == 1 and result["source"] == "ai"
    assert result["problem_text"] == "2x - 7 = 4x + 3"
    assert result["speech"] == analysis()["speech"]
    assert result["display"] == analysis()["display"]
    parts = sent[0]["contents"][0]["parts"]
    assert base64.b64decode(parts[1]["inline_data"]["data"]) == b"\xff\xd8jpeg"
    assert parts[1]["inline_data"]["mime_type"] == "image/jpeg"
    schema = sent[0]["generationConfig"]["responseSchema"]
    assert {"speech", "display"} <= set(schema["required"])
    assert not {"focus", "action", "variant"} & set(schema["properties"])


def test_failed_reading_prompts_retake_without_inventing_an_error(device: Device, ai):
    ai.reply = {**analysis(), "readable": False, "unreadable_reason": "dark"}
    select(device, "ikemen")
    result = device.hint(device.start_watching(), "manual")
    assert result["source"] == "fallback"
    assert result["speech"] == result["display"] and len(result["speech"]) <= 60
    assert "明る" in result["display"] and "符号" not in result["display"]
