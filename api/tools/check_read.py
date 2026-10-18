import asyncio
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from photos import photo

from app.gemini import Gemini
from app.hints import read_problem

MODEL = os.environ.get("HINT_MODEL", "gemini-3.5-flash-lite")
PAPERS = {
    "問題だけ": ["(1) 2x - 7 = 4x + 3", "", "(2) 3x + 2 = 8"],
    "1 問目を途中まで": ["(1) 2x - 7 = 4x + 3", "2x - 4x = 3 + 7", "", "(2) 3x + 2 = 8"],
    "白紙": [],
}


async def main() -> None:
    ai = Gemini(os.environ["GEMINI_API_KEY"])
    for name, lines in PAPERS.items():
        started = time.monotonic()
        text = await read_problem(ai, MODEL, photo(lines), None)
        print(f"{name}（{time.monotonic() - started:.1f} 秒）→ {text!r}")


asyncio.run(main())
