import asyncio

import httpx

TIMEOUT_SECONDS = 8
VOICES = {"handsome": ("青山龍星", "しっとり"), "teacher": ("冥鳴ひまり", "ノーマル")}


class VoiceUnavailable(Exception):
    pass


class Voicevox:
    def __init__(self, base_url: str) -> None:
        self._client = httpx.AsyncClient(base_url=base_url, timeout=TIMEOUT_SECONDS)
        self._speakers: dict[str, int] = {}

    async def _speaker(self, character: str) -> int:
        if not self._speakers:
            response = await self._client.get("/speakers")
            response.raise_for_status()
            styles = {(speaker["name"], style["name"]): style["id"] for speaker in response.json() for style in speaker["styles"]}
            self._speakers = {name: styles[voice] for name, voice in VOICES.items()}
        return self._speakers[character]

    async def synthesize(self, text: str, character: str) -> bytes:
        try:
            async with asyncio.timeout(TIMEOUT_SECONDS):
                params = {"speaker": await self._speaker(character)}
                query = await self._client.post("/audio_query", params={**params, "text": text})
                query.raise_for_status()
                audio = await self._client.post("/synthesis", params=params, json=query.json())
            audio.raise_for_status()
        except (TimeoutError, httpx.HTTPError, ValueError, KeyError, TypeError) as error:
            raise VoiceUnavailable(repr(error)) from error
        return audio.content
