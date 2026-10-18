import asyncio

import httpx
import pytest

from app.voicevox import VoiceUnavailable, Voicevox

SPEAKERS = [
    {"name": "青山龍星", "styles": [{"name": "ノーマル", "id": 13}, {"name": "しっとり", "id": 84}]},
    {"name": "冥鳴ひまり", "styles": [{"name": "ノーマル", "id": 14}]},
]


def engine(speakers: list[dict], used: list[str]) -> Voicevox:
    def handle(request: httpx.Request) -> httpx.Response:
        used.append(f"{request.url.path} {request.url.params.get('speaker')}")
        if request.url.path == "/speakers":
            return httpx.Response(200, json=speakers)
        if request.url.path == "/audio_query":
            return httpx.Response(200, json={"accent_phrases": []})
        return httpx.Response(200, content=b"RIFF")

    voice = Voicevox("http://voicevox")
    voice._client = httpx.AsyncClient(base_url="http://voicevox", transport=httpx.MockTransport(handle))
    return voice


def test_each_character_speaks_with_the_style_looked_up_by_name_once() -> None:
    used: list[str] = []
    voice = engine(SPEAKERS, used)
    assert asyncio.run(voice.synthesize("見てごらん", "handsome")) == b"RIFF"
    asyncio.run(voice.synthesize("見てみましょう", "teacher"))
    assert used == ["/speakers None", "/audio_query 84", "/synthesis 84", "/audio_query 14", "/synthesis 14"]


def test_a_missing_voice_makes_the_browser_read_instead() -> None:
    voice = engine([{"name": "冥鳴ひまり", "styles": [{"name": "ノーマル", "id": 14}]}], [])
    with pytest.raises(VoiceUnavailable):
        asyncio.run(voice.synthesize("見てごらん", "handsome"))
