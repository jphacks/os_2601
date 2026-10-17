import asyncio
import io
import os
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.gemini import Gemini  # noqa: E402
from app.hints import compose_answer  # noqa: E402

MODEL = os.environ.get("HINT_MODEL", "gemini-3.5-flash-lite")
LINES = ["4x + 5 = 1", "4x = 1 - 5", "4x = -4"]
UTTERANCES = [
    "移項って何？",
    "4X = -4 の後何をすればいいの",
    "答え教えて",
    "お母さんご飯まだ？",
    "4x + 5 = 1",
]


def photo(lines: list[str]) -> bytes:
    image = Image.new("RGB", (1024, 576), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 60)
    for index, line in enumerate(lines):
        draw.text((60, 50 + index * 120), line, fill="black", font=font)
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", quality=70)
    return buffer.getvalue()


async def main() -> None:
    ai = Gemini(os.environ["GEMINI_API_KEY"])
    frame = photo(LINES)
    print(f"答案: {' / '.join(LINES)}")
    for utterance in UTTERANCES:
        started = time.monotonic()
        hint = await compose_answer(ai, MODEL, frame, utterance, [], None, [])
        seconds = time.monotonic() - started
        if hint is None:
            print(f"「{utterance}」（{seconds:.1f} 秒）→ 答えない")
            continue
        print(f"「{utterance}」（{seconds:.1f} 秒、{hint.source}、漏れ検査 {hint.leak_check.ok}、{len(hint.speech)} 字）")
        print(f"  → {hint.speech}")


asyncio.run(main())
