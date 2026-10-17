import asyncio
import base64
import json

import httpx

API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
TIMEOUT_SECONDS = 8


class AIUnavailable(Exception):
    pass


class Gemini:
    def __init__(self, api_key: str) -> None:
        self._client = httpx.AsyncClient(headers={"x-goog-api-key": api_key})

    async def generate_json(self, model: str, system: str, text: str, image_jpeg: bytes, schema: dict) -> dict:
        body = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"text": text},
                        {"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(image_jpeg).decode()}},
                    ],
                }
            ],
            "generationConfig": {"responseMimeType": "application/json", "responseSchema": schema},
        }
        try:
            async with asyncio.timeout(TIMEOUT_SECONDS):
                response = await self._client.post(API_URL.format(model=model), json=body)
            response.raise_for_status()
            reply = json.loads(response.json()["candidates"][0]["content"]["parts"][-1]["text"])
        except (TimeoutError, httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as error:
            raise AIUnavailable(f"{model}: {error!r}") from error
        if not isinstance(reply, dict):
            raise AIUnavailable(f"{model}: JSON がオブジェクトでない")
        return reply
