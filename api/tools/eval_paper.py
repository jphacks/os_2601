import asyncio
import io
import os
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from photos import photo

from app.check import judge
from app.gemini import AIUnavailable, Gemini
from app.hints import compose_answer, compose_hint, read_problem

MODEL = os.environ.get("HINT_MODEL", "gemini-3.5-flash-lite")
ROUNDS = int(os.environ.get("ROUNDS", "1"))
PAUSE_SECONDS = 6
SIZE = (1024, 576)


def jpeg(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", quality=70)
    return buffer.getvalue()


def noise() -> bytes:
    return jpeg(Image.frombytes("RGB", SIZE, random.Random(1).randbytes(SIZE[0] * SIZE[1] * 3)))


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


def pacman() -> bytes:
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


NO_PAPER = {
    "机": lambda: jpeg(Image.new("RGB", SIZE, (120, 86, 60))),
    "ノイズ": noise,
    "キーボード": keyboard,
    "画面": pacman,
    "顔": face,
}
PAPER = {
    "答案の途中": lambda: photo(["3x + 5 = 20", "3x = 15"]),
    "問題だけ": lambda: photo(["2x - 7 = 4x + 3"]),
    "誤りのある答案": lambda: photo(["4x + 5 = 1", "4x = 1 - 4", "4x = -4"]),
    "正しい答案": lambda: photo(["3x + 5 = 20", "3x = 15", "x = 5"]),
}


async def run(ai: Gemini, name: str, image: bytes) -> tuple[bool, bool, bool, str]:
    problem = await read_problem(ai, MODEL, image, None)
    await asyncio.sleep(PAUSE_SECONDS)
    hint = await compose_hint(ai, MODEL, image, 1, [], None, [], "teacher")
    await asyncio.sleep(PAUSE_SECONDS)
    try:
        reply = await compose_answer(ai, MODEL, image, "次どうすればいい？", [], None, [], "teacher")
    except AIUnavailable:
        reply = None
    await asyncio.sleep(PAUSE_SECONDS)
    verdict = (await judge(ai, MODEL, image, None)).verdict
    await asyncio.sleep(PAUSE_SECONDS)
    voiced = reply is not None and reply.source == "ai"
    print(f"  {name}: 問題文={problem!r} ヒント={hint.source}「{hint.speech}」 声={reply.source if reply else None}「{reply.speech if reply else ''}」 できた={verdict}")
    return problem is not None, hint.source == "ai", voiced, verdict


async def main() -> None:
    ai = Gemini(os.environ["GEMINI_API_KEY"])
    invented = read_ok = hinted = voiced = correct_sheets = judged_correct = no_paper_runs = paper_runs = 0
    print("紙が無い写真（問題文・ヒント・声の答え・できたの判定のどれかを作ったら誤り）")
    for _ in range(0 if os.environ.get("ONLY") == "paper" else ROUNDS):
        for name, make in NO_PAPER.items():
            problem, hint, voice, verdict = await run(ai, name, make())
            invented += problem or hint or voice or verdict != "unreadable"
            no_paper_runs += 1
    print("紙の写真（問題文を読み、AI のヒントを出せば正しい）")
    for _ in range(0 if os.environ.get("ONLY") == "no_paper" else ROUNDS):
        for name, make in PAPER.items():
            problem, hint, voice, verdict = await run(ai, name, make())
            read_ok += problem
            hinted += hint
            voiced += voice
            if name == "正しい答案":
                correct_sheets += 1
                judged_correct += verdict == "correct"
            paper_runs += 1
    print(f"紙が無い {no_paper_runs} 回のうち、作り話 {invented} 回")
    print(f"紙の写真 {paper_runs} 回のうち、問題文を読めた {read_ok} 回、AI のヒント {hinted} 回、AI の声の答え {voiced} 回")
    print(f"正しい答案 {correct_sheets} 回のうち、正解と判定 {judged_correct} 回")


asyncio.run(main())
