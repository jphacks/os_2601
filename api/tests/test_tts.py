from datetime import timedelta

import pytest
from conftest import WAV, Device, FakeVoice


@pytest.fixture
def ai() -> None:
    return None


@pytest.fixture
def voice(device: Device) -> FakeVoice:
    fake = FakeVoice()
    device.client.app.state.context.voice = fake
    return fake


def speak(device: Device, text: str, headers: dict[str, str] | None = None, character: str | None = None):
    body = {"text": text, **({"character": character} if character else {})}
    return device.client.post(f"/sessions/{device.session_id}/tts", json=body, headers=headers or device.headers)


def test_text_is_returned_as_wav_audio(device: Device, voice: FakeVoice) -> None:
    response = speak(device, "最初の行を見てみて")
    assert (response.status_code, response.headers["content-type"], response.content) == (200, "audio/wav", WAV)
    assert voice.texts == ["最初の行を見てみて"]


def test_the_chosen_character_speaks_and_the_handsome_one_by_default(device: Device, voice: FakeVoice) -> None:
    speak(device, "最初の行を見てみて")
    speak(device, "最初の行を見てみましょう", character="teacher")
    assert voice.characters == ["handsome", "teacher"]
    assert speak(device, "最初の行を見てみて", character="friend").status_code == 422


def test_without_a_voice_engine_the_browser_reads_instead(device: Device) -> None:
    assert speak(device, "最初の行を見てみて").status_code == 503


def test_engine_failure_is_503(device: Device, voice: FakeVoice) -> None:
    voice.fail = True
    assert speak(device, "最初の行を見てみて").status_code == 503


@pytest.mark.parametrize("text", ["", "あ" * 201])
def test_text_length_is_limited(device: Device, voice: FakeVoice, text: str) -> None:
    assert speak(device, text).status_code == 422
    assert voice.texts == []


def test_the_last_words_after_the_end_are_spoken_but_not_later(device: Device, voice: FakeVoice) -> None:
    device.client.post(f"/sessions/{device.session_id}/end", headers=device.headers)
    assert speak(device, "正解。その調子").status_code == 200
    device.now += timedelta(minutes=2)
    assert speak(device, "正解。その調子").status_code == 409


def test_only_the_session_device_can_speak(device: Device, voice: FakeVoice) -> None:
    assert speak(device, "最初の行を見てみて", {"Authorization": "Bearer tok_wrong"}).status_code == 401
    assert voice.texts == []
