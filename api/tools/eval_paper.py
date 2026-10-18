import asyncio
import io
import os
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from photos import photo

from app.gemini import Gemini
from app.hints import compose_hint, read_problem

MODEL = os.environ.get("HINT_MODEL", "gemini-3.5-flash-lite")
ROUNDS = int(os.environ.get("ROUNDS", "1"))
PAUSE_SECONDS = 6
SIZE = (1024, 576)


def jpeg(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", quality=70)
    return buffer.getvalue()


def desk() -> bytes:
    return jpeg(Image.new("RGB", SIZE, (120, 86, 60)))


def noise() -> bytes:
    generator = random.Random(1)
    image = Image.new("RGB", SIZE)
    image.putdata([tuple(generator.randrange(256) for _ in range(3)) for _ in range(SIZE[0] * SIZE[1])])
    return jpeg(image)


def keyboard() -> bytes:
    image = Image.new("RGB", SIZE, (40, 40, 44))
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=40)
    for row, keys in enumerate(["QWERTYUIOP", "ASDFGHJKL", "ZXCVBNM"]):
        for column, key in enumerate(keys):
            x, y = 60 + column * 90 + row * 30, 80 + row * 140
            draw.rounded_rectangle((x, y, x + 76, y + 110), radius=12, fill=(70, 70, 76))
            draw.text((x + 24, y + 30), key, fill="white", font=font)
    return jpeg(image)


def english() -> bytes:
    return photo(["The quick brown fox", "jumps over the lazy dog.", "Please read chapter 3."])


def screen() -> bytes:
    image = Image.new("RGB", SIZE, (30, 160, 60))
    ImageDraw.Draw(image).pieslice((380, 160, 640, 420), start=30, end=330, fill=(250, 220, 40))
    return jpeg(image)


def face() -> bytes:
    image = Image.new("RGB", SIZE, (200, 210, 220))
    draw = ImageDraw.Draw(image)
    draw.ellipse((360, 80, 660, 480), fill=(240, 200, 170))
    draw.ellipse((430, 210, 470, 250), fill="black")
    draw.ellipse((550, 210, 590, 250), fill="black")
    draw.arc((440, 300, 580, 400), start=20, end=160, fill="black", width=6)
    return jpeg(image)


NO_PAPER = {"机": desk, "ノイズ": noise, "キーボード": keyboard, "英文": english, "画面": screen, "顔": face}
PAPER = {
    "答案の途中": lambda: photo(["3x + 5 = 20", "3x = 15"]),
    "問題だけ": lambda: photo(["2x - 7 = 4x + 3"]),
    "誤りのある答案": lambda: photo(["4x + 5 = 1", "4x = 1 - 4", "4x = -4"]),
}


async def run(ai: Gemini, name: str, image: bytes) -> tuple[bool, bool]:
    problem = await read_problem(ai, MODEL, image, None)
    await asyncio.sleep(PAUSE_SECONDS)
    hint = await compose_hint(ai, MODEL, image, 1, [], None, [], "teacher")
    await asyncio.sleep(PAUSE_SECONDS)
    print(f"  {name}: 問題文={problem!r} ヒント={hint.source}「{hint.speech}」")
    return problem is not None, hint.source == "ai"


async def main() -> None:
    ai = Gemini(os.environ["GEMINI_API_KEY"])
    invented = read_ok = hinted = no_paper_runs = paper_runs = 0
    print("紙が無い写真（問題文やヒントを作ったら誤り）")
    for _ in range(0 if os.environ.get("ONLY") == "paper" else ROUNDS):
        for name, make in NO_PAPER.items():
            problem, hint = await run(ai, name, make())
            invented += problem or hint
            no_paper_runs += 1
    print("紙の写真（問題文を読み、AI のヒントを出せば正しい）")
    for _ in range(0 if os.environ.get("ONLY") == "no_paper" else ROUNDS):
        for name, make in PAPER.items():
            problem, hint = await run(ai, name, make())
            read_ok += problem
            hinted += hint
            paper_runs += 1
    print(f"紙が無い {no_paper_runs} 回のうち、作り話 {invented} 回")
    print(f"紙の写真 {paper_runs} 回のうち、問題文を読めた {read_ok} 回、AI のヒント {hinted} 回")


asyncio.run(main())
