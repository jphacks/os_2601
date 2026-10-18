import asyncio

import httpx

TIMEOUT_SECONDS = 8


class VoiceUnavailable(Exception):
    pass


class Voicevox:
    def __init__(self, base_url: str, speaker: int) -> None:
        self._client = httpx.AsyncClient(base_url=base_url, timeout=TIMEOUT_SECONDS)
        self._speaker = speaker

    async def synthesize(self, text: str) -> bytes:
        params = {"speaker": self._speaker}
        try:
            async with asyncio.timeout(TIMEOUT_SECONDS):
                query = await self._client.post("/audio_query", params={**params, "text": text})
                query.raise_for_status()
                audio = await self._client.post("/synthesis", params=params, json=query.json())
            audio.raise_for_status()
        except (TimeoutError, httpx.HTTPError, ValueError) as error:
            raise VoiceUnavailable(repr(error)) from error
        return audio.content
