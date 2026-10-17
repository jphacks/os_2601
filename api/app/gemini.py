import base64
import json
from dataclasses import dataclass

import httpx

API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
TIMEOUT_SECONDS = 8


class AIUnavailable(Exception):
    pass


@dataclass(frozen=True)
class Gemini:
    api_key: str

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
            async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
                response = await client.post(
                    API_URL.format(model=model), json=body, headers={"x-goog-api-key": self.api_key}
                )
            response.raise_for_status()
            return json.loads(response.json()["candidates"][0]["content"]["parts"][-1]["text"])
        except (httpx.HTTPError, KeyError, IndexError, ValueError) as error:
            raise AIUnavailable(f"{model}: {error!r}") from error
