from dataclasses import dataclass

from app.gemini import AIUnavailable, Gemini
from app.leak import contains_leak, leak_strings, normalize
from app.state import LeakCheck

SPEECH_MAX_CHARS = 60
DISPLAY_MAX_CHARS = 80
STUCK_POINT_MAX_CHARS = 12
UNREADABLE_HINT = "途中の式を、1 行ずつ声に出して読んでみて"
FALLBACK_HINTS = {1: "今、何を求めようとしてる？", 2: UNREADABLE_HINT}
FALLBACK_STUCK_POINT = "読み取れず"

SYSTEM_PROMPT = """あなたは中学生の隣に座っている家庭教師です。画像は、学習者が紙で問題を解いている手元の写真です。
あなたの役目は、答えを言わずに、学習者が自分の手で最後の答えまで書き切れるよう、次に考える所を 1 つだけ示すことです。

1. 写真から、学習者がいま解いている問題の文を読み取り、problem_text に書いてください。
2. その問題を自分で解き、最終の答えを final_answer に、途中の決定的な値や式（移項した後の式、約分した値など）を key_values に書いてください。これらは学習者には見せません。
3. 学習者の答案を 1 行目から順に、自分の解き方と比べて、ヒントで示す所を 1 つ決めてください。
   - 誤りのある行があれば、いちばん最初の誤りの行を示す。その後の行が正しく見えても、最初の誤りを先に示す。
   - 誤りが無ければ、最後に書いた行から答えまでの、次の一歩を示す。
   - 前に出したヒントが示した所が、答案で直っていれば、そこは示さず、次の誤りか次の一歩に進む。直っていなければ、同じ所をもう少し具体的に示す。前と同じ文は繰り返さない。
4. 示す所を、数学の内容で stuck_point に 12 文字以内で書いてください（例：移項の数字、係数で割る、かっこを外す）。「手が止まっている」「次の一手」のような様子は書かない。
5. ヒントを 1 つだけ、speech と display に書いてください。
   - speech は読み上げ用。35 文字以内の 1 文。数字は算用数字のまま、記号は言葉にする（= はイコール、- はマイナス、x はエックス）。漢字は普通に使う。
   - display は字幕用。50 文字以内。数式は半角。speech と同じ内容。

絶対に守ること：
- 答えの値、途中の決定的な値、正しい式の完成形を、ヒントに書かない。問題を解いて見せない。
- 誤りを示すときは、誤っている数字や記号そのものを、行と位置で指す（「2行目の右辺の 4」）。符号の誤りか、数字の誤りか、計算の誤りかを見分けて、その種類に合う言い方にする。正しい値は言わない。
- 学習者が正しく書いた式や値は、読み上げずに行と位置で指す（「最後の行の左辺」）。
- 次の一歩を示すときは、段階 1 では問いかけにする（「エックスだけにするには、どうする？」）。操作の結果の値は言わない。
- 命令形でなく、提案形（「見てみて」「やってみて」）か問いかけ。「惜しい」「違う」「答えは」は使わない。名前は呼ばない。
- 答案が読めないときは readable を false にし、ヒントは「途中の式を、1 行ずつ声に出して読んでみて」にする。"""

LEVEL_INSTRUCTIONS = {
    1: "段階 1：学習者が自分で気づけるよう、示す所を、行と場所を指すか問いかけで示してください。",
    2: (
        "段階 2：段階 1 より具体的に示してください。次の一歩なら、する操作を 1 つ言ってかまいません（「両辺を同じ数でわってみて」）。"
        "誤りなら、その数字や記号がどこから来たかを見比べさせてください（「1行目の +5 と見比べてみて」）。"
        "操作の結果の値や、直した後の正しい数字は言わないでください。"
    ),
}

HINT_SCHEMA = {
    "type": "OBJECT",
    "propertyOrdering": ["problem_text", "final_answer", "key_values", "readable", "stuck_point", "speech", "display"],
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


def fixed_hint(text: str, source: str, leak_check: LeakCheck, known_leaks: list[str]) -> ComposedHint:
    return ComposedHint(text, text, FALLBACK_STUCK_POINT, source, None, leak_check, None, known_leaks)


def _request_text(level: int, previous: list[str], known_problem: str | None) -> str:
    lines = [LEVEL_INSTRUCTIONS[level]]
    if known_problem:
        lines.append(f"前に読み取った問題文：{known_problem}（写真の問題が違えば、前のヒントは使わない）")
    if previous:
        lines.append("この問題で既に出したヒント（古い順）：")
        lines.extend(f"{number}. {text}" for number, text in enumerate(previous, start=1))
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
        return fixed_hint(FALLBACK_HINTS[level], "fallback", LeakCheck(ok=True, fallback=False), known_leaks)
    try:
        out = await ai.generate_json(model, SYSTEM_PROMPT, _request_text(level, previous, known_problem), frame, HINT_SCHEMA)
        problem_text = out["problem_text"] or None
        same_problem = bool(known_problem and problem_text) and normalize(known_problem) == normalize(problem_text)
        inherited = known_leaks if same_problem or not problem_text else []
        leaks = sorted(set(inherited) | set(leak_strings(out["final_answer"], out["key_values"])))
        speech = out["speech"].strip()
        display = out["display"].strip()
        readable = out["readable"] is True
        stuck_point = out["stuck_point"].strip()[:STUCK_POINT_MAX_CHARS] or FALLBACK_STUCK_POINT
    except (AIUnavailable, KeyError, TypeError, AttributeError):
        return fixed_hint(FALLBACK_HINTS[level], "fallback", LeakCheck(ok=True, fallback=False), known_leaks)

    if any(contains_leak(text, leaks) for text in (speech, display, stuck_point)):
        return fixed_hint(FALLBACK_HINTS[level], "fallback", LeakCheck(ok=False, fallback=True), leaks)
    if not readable:
        return fixed_hint(UNREADABLE_HINT, "fallback", LeakCheck(ok=True, fallback=False), leaks)
    if not speech or not display or len(speech) > SPEECH_MAX_CHARS or len(display) > DISPLAY_MAX_CHARS:
        return fixed_hint(FALLBACK_HINTS[level], "fallback", LeakCheck(ok=True, fallback=False), leaks)
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
