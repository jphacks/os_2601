import asyncio
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.gemini import Gemini  # noqa: E402
from photos import photo  # noqa: E402
from app.hints import compose_hint  # noqa: E402

MODEL = os.environ.get("HINT_MODEL", "gemini-3.5-flash-lite")
ERROR = ["4x + 5 = 1", "4x = 1 - 4", "4x = -4"]
FIXED = ["4x + 5 = 1", "4x = 1 - 5", "4x = -4"]
SCENARIOS = {
    "誤り → 直した → 最後の一歩（高橋さんの答案）": [ERROR, FIXED, FIXED],
    "誤りが直らない": [ERROR, ERROR, ERROR],
    "誤りなし・途中で止まる": [["3(x - 2) = 9", "3x - 6 = 9"]] * 3,
}


async def main() -> None:
    ai = Gemini(os.environ["GEMINI_API_KEY"])
    for name, rounds in SCENARIOS.items():
        if len(sys.argv) > 1 and sys.argv[1] not in name:
            continue
        print(f"## {name}")
        previous: list[str] = []
        problem_text, leaks = None, []
        for round_number, (lines, level) in enumerate(zip(rounds, (1, 1, 2)), start=1):
            print(f"答案: {' / '.join(lines)}")
            started = time.monotonic()
            hint = await compose_hint(ai, MODEL, photo(lines), level, previous, problem_text, leaks)
            seconds = time.monotonic() - started
            print(f"{round_number} 回目（段階 {level}、{seconds:.1f} 秒、{hint.source}、漏れ検査 {hint.leak_check.ok}）")
            print(f"  読み上げ（{len(hint.speech)} 字）: {hint.speech}")
            print(f"  字幕: {hint.display}")
            print(f"  ラベル: {hint.stuck_point}")
            previous.append(hint.display)
            problem_text, leaks = hint.problem_text or problem_text, hint.leak_strings


asyncio.run(main())
