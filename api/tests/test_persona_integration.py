import base64
import json
from dataclasses import replace
from datetime import timedelta

import httpx
import pytest
from conftest import OPERATOR_KEY, Device

from app.gemini import Gemini
from app.personas import end_message
from app.store import SessionStore


def analysis(focus="右辺に移したときの符号"):
    return {
        "readable": True, "unreadable_reason": "none",
        "problem_text": "2x - 7 = 4x + 3", "final_answer": "x = -5",
        "key_values": ["-2x = 10"], "written_lines": [],
        "stuck_point": "移項の符号", "focus": focus,
        "action": "review", "variant": "playful",
    }


class ImageAI:
    def __init__(self):
        self.calls = []
        self.reply = analysis()
        self.on_call = lambda: None

    async def generate_json(self, model, system, text, image_jpeg, schema):
        self.calls.append((system, text, image_jpeg, schema))
        self.on_call()
        return self.reply


@pytest.fixture
def ai():
    return ImageAI()


def select(device, persona):
    return device.client.patch(
        f"/sessions/{device.session_id}/settings", json={"persona": persona}, headers=device.headers
    )


def start(device):
    device.signal(0, 0.05)
    device.signal(1, 0.05)
    return device.frame()


@pytest.mark.parametrize("persona", ["teacher", "ikemen"])
def test_selected_persona_uses_the_camera_and_keeps_answers_private(device: Device, ai, persona):
    assert select(device, persona).json()["settings"]["persona"] == persona
    initial = device.client.get(f"/sessions/{device.session_id}", headers=device.headers).json()
    assert initial["problems"][0]["problem_text"] is None
    result = device.hint(start(device), "manual")
    assert result["source"] == "gpt"
    assert result["problem_text"] == "2x - 7 = 4x + 3"
    assert result["speech"] == result["display"]
    assert len(result["speech"]) <= 40 and len(result["display"]) <= 60
    assert "右辺に移したときの符号" in result["display"]
    assert result["display"].endswith("ましょう。" if persona == "teacher" else "よう。")
    assert len(ai.calls) == 1 and ai.calls[0][2] == b"\xff\xd8jpeg"
    detail = device.client.get(f"/sessions/{device.session_id}", headers=device.headers).json()
    assert detail["problems"][0]["problem_text"] == result["problem_text"]
    assert {option["id"] for option in detail["persona_options"]} == {"teacher", "ikemen"}
    assert next(option["end_message"] for option in detail["persona_options"] if option["id"] == persona) == end_message(persona).display
    encoded = json.dumps([result, detail], ensure_ascii=False)
    assert "final_answer" not in encoded and "leak_strings" not in encoded and "key_values" not in encoded
    assert "x=-5" not in encoded and "-2x=10" not in encoded


@pytest.mark.parametrize("persona", ["teacher", "ikemen"])
def test_startup_read_remains_separate_from_the_persona_hint_and_keeps_analysis_private(device: Device, ai, persona):
    assert select(device, persona).status_code == 200
    frame_id = start(device)
    read = device.client.post(
        f"/sessions/{device.session_id}/problem", headers=device.headers, json={"frame_id": frame_id}
    )
    assert read.status_code == 200
    assert read.json() == {"problem_no": 1, "problem_text": "2x - 7 = 4x + 3", "state": "watching"}
    assert len(ai.calls) == 1 and ai.calls[0][2] == b"\xff\xd8jpeg"
    assert set(ai.calls[0][3]["properties"]) == {"problem_text", "readable"}
    initial = device.client.get(f"/sessions/{device.session_id}", headers=device.headers).json()
    assert initial["problems"][0]["hints"] == []
    assert initial["problems"][0]["stuck_count"] == 0
    assert initial["stuck_points"] == []

    hint = device.hint(frame_id, "manual")
    assert hint["source"] == "gpt"
    assert hint["speech"] == hint["display"] and len(hint["speech"]) <= 40
    assert len(ai.calls) == 2
    assert "前に読み取った問題文：2x - 7 = 4x + 3" in ai.calls[1][1]
    assert {"focus", "action", "variant"} <= set(ai.calls[1][3]["required"])
    detail = device.client.get(f"/sessions/{device.session_id}", headers=device.headers).json()
    assert detail["stuck_points"] == [{"label": "移項の符号", "count": 1}]
    encoded = json.dumps([read.json(), initial, hint, detail], ensure_ascii=False)
    for private_value in ("final_answer", "key_values", "leak_strings", "x=-5", "-2x=10"):
        assert private_value not in encoded


@pytest.mark.parametrize("persona", ["teacher", "ikemen"])
def test_only_generated_hints_add_labels_when_persona_fallbacks_are_recorded(device: Device, ai, persona):
    assert select(device, persona).status_code == 200
    frame_id = start(device)
    assert device.hint(frame_id, "manual")["source"] == "gpt"
    device.signal(20, 0.05)
    ai.reply = {**analysis(), "readable": False, "unreadable_reason": "dark"}
    unreadable = device.hint(frame_id, "manual")
    assert unreadable["source"] == "fallback"
    assert "明る" in unreadable["display"]
    device.signal(40, 0.05)
    check = device.hint(frame_id, "voice", "これで合ってる？")
    assert check["source"] == "fallback" and check["stuck_point"] == "答えの確認"
    assert len(ai.calls) == 2
    for response in (unreadable, check):
        assert response["speech"] == response["display"] and len(response["speech"]) <= 40
    detail = device.client.get(f"/sessions/{device.session_id}", headers=device.headers).json()
    assert [hint["source"] for hint in detail["problems"][0]["hints"]] == ["gpt", "fallback", "fallback"]
    assert detail["stuck_points"] == [{"label": "移項の符号", "count": 1}]


def test_read_problem_survives_a_fallback_but_does_not_leak_into_the_next_problem(device: Device, ai):
    frame_id = start(device)
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


def test_existing_friend_data_migrates_to_teacher_without_reappearing(device: Device, tmp_path):
    path = tmp_path / "old-session.json"
    store = SessionStore(path)
    store.put(device.client.app.state.context.store.get(device.session_id))
    store.save()
    raw = json.loads(path.read_text(encoding="utf-8"))
    raw["sessions"][device.session_id]["settings"]["persona"] = "friend"
    path.write_text(json.dumps(raw), encoding="utf-8")
    restored = SessionStore(path)
    restored.load()
    assert restored.get(device.session_id).settings.persona == "teacher"
    restored.save()
    assert '"friend"' not in path.read_text(encoding="utf-8")


def test_switch_is_rejected_while_normal_hint_is_pending(device: Device):
    start(device)
    store = device.client.app.state.context.store
    session = store.get(device.session_id)
    store.put(replace(session, pending_until=device.now + timedelta(seconds=12)))
    assert select(device, "ikemen").status_code == 409
    assert store.get(device.session_id).settings.persona == "teacher"


def test_stale_voice_result_cannot_use_an_earlier_persona(device: Device, ai):
    frame = start(device)
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
    result = device.hint(start(device), "manual")
    assert len(sent) == 1 and result["source"] == "gpt"
    assert result["problem_text"] == "2x - 7 = 4x + 3"
    assert "右辺に移したときの符号" in result["display"]
    parts = sent[0]["contents"][0]["parts"]
    assert base64.b64decode(parts[1]["inline_data"]["data"]) == b"\xff\xd8jpeg"
    assert parts[1]["inline_data"]["mime_type"] == "image/jpeg"
    assert {"focus", "action", "variant"} <= set(sent[0]["generationConfig"]["responseSchema"]["required"])


def test_failed_reading_prompts_retake_without_inventing_an_error(device: Device, ai):
    ai.reply = {**analysis(), "readable": False, "unreadable_reason": "dark"}
    select(device, "ikemen")
    result = device.hint(start(device), "manual")
    assert result["source"] == "fallback"
    assert result["speech"] == result["display"] and len(result["speech"]) <= 40
    assert "明る" in result["display"] and "符号" not in result["display"]
