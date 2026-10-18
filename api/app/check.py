from dataclasses import dataclass

from app.gemini import AIUnavailable, Gemini
from app.state import Verdict

CORRECT_TEXT = "正解。その調子"
INCORRECT_TEXT = "もう一回、途中の式を見てみて"
UNREADABLE_TEXT = "もう少し明るいところで、もう一回見せて"
FAILED_TEXT = "うまく読めなかった。もう一回、できたを押してみて"
REQUEST_TEXT = "写真の問題を自分で解き、学習者の最終の答えと比べてください。"

SYSTEM_PROMPT = """画像は、学習者が紙で問題を解いた答案の写真です。
写っている問題を自分で解き、学習者が書いた最終の答えと比べてください。
紙に問題が複数あるときは、答案が最後の行まで書かれている問題を見てください。問題文が渡されていて、その問題に答案が書かれていれば、それを見てください（答案が無ければ渡された問題文は無視する）。
正しければ correct、間違っていれば incorrect、答案の最終行が読めなければ unreadable を verdict に入れてください。
文は作らないでください。"""

CHECK_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "readable": {"type": "BOOLEAN"},
        "final_answer_seen": {"type": "STRING"},
        "verdict": {"type": "STRING", "enum": ["correct", "incorrect", "unreadable"]},
    },
    "required": ["readable", "final_answer_seen", "verdict"],
}

SPEECH_BY_VERDICT: dict[str, str] = {"correct": CORRECT_TEXT, "incorrect": INCORRECT_TEXT, "unreadable": UNREADABLE_TEXT}


@dataclass(frozen=True)
class Judgement:
    verdict: Verdict
    speech: str


async def judge(ai: Gemini | None, model: str, frame: bytes | None, known_problem: str | None) -> Judgement:
    if ai is None or frame is None:
        return Judgement("unreadable", FAILED_TEXT)
    request = REQUEST_TEXT if known_problem is None else f"{REQUEST_TEXT}\n見る問題：{known_problem}"
    try:
        out = await ai.generate_json(model, SYSTEM_PROMPT, request, frame, CHECK_SCHEMA)
        verdict = out["verdict"]
        return Judgement(verdict, SPEECH_BY_VERDICT[verdict])
    except (AIUnavailable, KeyError, TypeError):
        return Judgement("unreadable", FAILED_TEXT)
