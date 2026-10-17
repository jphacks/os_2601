from dataclasses import dataclass

from app.gemini import AIUnavailable, Gemini
from app.leak import contains_leak, leak_strings, normalize
from app.state import LeakCheck

SPEECH_MAX_CHARS = 40
DISPLAY_MAX_CHARS = 60
FALLBACK_HINTS = {1: "今、何を求めようとしてる？", 2: "途中の式を、1 行ずつ声に出して読んでみて"}
FALLBACK_STUCK_POINT = "読み取れず"

SYSTEM_PROMPT = """あなたは中学生の隣に座っている家庭教師です。画像は、学習者が紙で問題を解いている手元の写真です。
1. 写真から、学習者がいま解いている問題の文を読み取り、problem_text に書いてください。
2. その問題を自分で解き、最終の答えを final_answer に、途中の決定的な値や式（移項した後の式、約分した値など）を key_values に書いてください。これらは学習者には見せません。
3. 学習者の答案を読み、詰まっている所を stuck_point に 10 文字以内で書いてください。
4. 学習者が自分で気づけるヒントを 1 つだけ、speech（読み上げ用。40 文字以内。記号は使わず「かける」「イコール」のように言葉にする）と display（字幕用。60 文字以内。数式は半角）に書いてください。

絶対に守ること：
- 答えの値、途中の決定的な値、正しい式の完成形を、ヒントに書かない。問題を解いて見せない。
- 見直す場所を 1 つ指すか、問いかける。何が違うかは言わない。
- 命令形でなく提案形（「見てみて」「やってみて」）。「惜しい」「違う」「答えは」は使わない。名前は呼ばない。
- 答案が読めないときは readable を false にし、ヒントは「途中の式を、1 行ずつ声に出して読んでみて」にする。"""

LEVEL_INSTRUCTIONS = {
    1: "段階 1：学習者が自分で気づけるよう、見直す場所を 1 つ指すか、問いかけてください。",
    2: "段階 2：段階 1 より少し具体的に、次に確かめる場所を 1 つ指してください。操作の結果の値は言わないでください。",
}

HINT_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "readable": {"type": "BOOLEAN"},
        "problem_text": {"type": "STRING"},
        "final_answer": {"type": "STRING"},
        "key_values": {"type": "ARRAY", "items": {"type": "STRING"}},
        "stuck_point": {"type": "STRING"},
        "speech": {"type": "STRING"},
        "display": {"type": "STRING"},
    },
    "required": ["readable", "problem_text", "final_answer", "key_values", "stuck_point", "speech", "display"],
}


@dataclass(frozen=True)
class ComposedHint:
    speech: str
    display: str
    stuck_point: str
    source: str
    model: str | None
    leak_check: LeakCheck
    problem_text: str | None
    leak_strings: list[str]


def fixed_hint(level: int, source: str, leak_check: LeakCheck, known_leaks: list[str]) -> ComposedHint:
    text = FALLBACK_HINTS[level]
    return ComposedHint(text, text, FALLBACK_STUCK_POINT, source, None, leak_check, None, known_leaks)


def _request_text(level: int, previous: list[str], known_problem: str | None) -> str:
    lines = [LEVEL_INSTRUCTIONS[level]]
    if known_problem:
        lines.append(f"前に読み取った問題文：{known_problem}")
    if previous:
        lines.append("この問題で既に出したヒント（同じことは言わず、別の着眼点で）：" + " / ".join(previous))
    return "\n".join(lines)


async def compose_hint(
    ai: Gemini | None,
    model: str,
    frame: bytes | None,
    level: int,
    previous: list[str],
    known_problem: str | None,
    known_leaks: list[str],
) -> ComposedHint:
    if ai is None or frame is None:
        return fixed_hint(level, "fallback", LeakCheck(ok=True, fallback=False), known_leaks)
    try:
        out = await ai.generate_json(model, SYSTEM_PROMPT, _request_text(level, previous, known_problem), frame, HINT_SCHEMA)
        problem_text = out["problem_text"] or None
        same_problem = bool(known_problem and problem_text) and normalize(known_problem) == normalize(problem_text)
        inherited = known_leaks if same_problem or not problem_text else []
        leaks = sorted(set(inherited) | set(leak_strings(out["final_answer"], out["key_values"])))
        speech = out["speech"][:SPEECH_MAX_CHARS].strip()
        display = out["display"][:DISPLAY_MAX_CHARS].strip()
        readable = out["readable"] is True
        stuck_point = out["stuck_point"][:10] or FALLBACK_STUCK_POINT
    except (AIUnavailable, KeyError, TypeError, AttributeError):
        return fixed_hint(level, "fallback", LeakCheck(ok=True, fallback=False), known_leaks)

    if not readable or not speech or not display:
        return fixed_hint(level, "fallback", LeakCheck(ok=True, fallback=False), leaks)
    if contains_leak(speech, leaks) or contains_leak(display, leaks):
        return fixed_hint(level, "fallback", LeakCheck(ok=False, fallback=True), leaks)
    return ComposedHint(
        speech=speech,
        display=display,
        stuck_point=stuck_point,
        source="gpt",
        model=model,
        leak_check=LeakCheck(ok=True, fallback=False),
        problem_text=problem_text,
        leak_strings=leaks,
    )
