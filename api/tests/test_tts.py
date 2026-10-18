import pytest
from conftest import Device

from app.voicevox import VoiceUnavailable

WAV = b"RIFF\x00\x00\x00\x00WAVE"


class FakeVoice:
    def __init__(self) -> None:
        self.fail = False
        self.texts: list[str] = []

    async def synthesize(self, text: str) -> bytes:
        self.texts.append(text)
        if self.fail:
            raise VoiceUnavailable("timeout")
        return WAV


@pytest.fixture
def ai() -> None:
    return None


@pytest.fixture
def voice(device: Device) -> FakeVoice:
    fake = FakeVoice()
    device.client.app.state.context.voice = fake
    return fake


def speak(device: Device, text: str, headers: dict[str, str] | None = None):
    return device.client.post(f"/sessions/{device.session_id}/tts", json={"text": text}, headers=headers or device.headers)


def test_text_is_returned_as_wav_audio(device: Device, voice: FakeVoice) -> None:
    response = speak(device, "最初の行を見てみて")
    assert (response.status_code, response.headers["content-type"], response.content) == (200, "audio/wav", WAV)
    assert voice.texts == ["最初の行を見てみて"]


def test_without_a_voice_engine_the_browser_reads_instead(device: Device) -> None:
    assert speak(device, "最初の行を見てみて").status_code == 503


def test_engine_failure_is_503(device: Device, voice: FakeVoice) -> None:
    voice.fail = True
    assert speak(device, "最初の行を見てみて").status_code == 503


@pytest.mark.parametrize("text", ["", "あ" * 121])
def test_text_length_is_limited(device: Device, voice: FakeVoice, text: str) -> None:
    assert speak(device, text).status_code == 422
    assert voice.texts == []


def test_only_the_session_device_can_speak(device: Device, voice: FakeVoice) -> None:
    assert speak(device, "最初の行を見てみて", {"Authorization": "Bearer tok_wrong"}).status_code == 401
    assert voice.texts == []
