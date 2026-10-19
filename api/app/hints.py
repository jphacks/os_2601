import logging
from dataclasses import dataclass

from app.gemini import AIUnavailable, Gemini
from app.leak import contains_leak, leak_strings, same_problem, states_an_answer, without_written
from app.paper import PAPER_POINTERS
from app.personas import fallback_message
from app.prompts import (
    ANSWER_PROMPT,
    ANSWER_SCHEMA,
    HINT_SCHEMA,
    LEVEL_INSTRUCTIONS,
    READ_PROMPT,
    READ_SCHEMA,
    STUCK_POINTS,
    SYSTEM_PROMPT,
    context_lines,
    persona_prompt,
)
from app.reading import to_reading
from app.state import HintSource, LeakCheck

SPEECH_MAX_CHARS = 60
DISPLAY_MAX_CHARS = 80
ANSWER_SPEECH_MAX_CHARS = 100
ANSWER_DISPLAY_MAX_CHARS = 120
UNREADABLE_HINT = "途中の式を、1 行ずつ声に出して読んでみて"
UNREADABLE_ANSWER = "答案がうまく見えない。紙を明るい所で、枠の中に入れてみて"
UNREADABLE_HINTS = {
    "dark": "もう少し明るいところで見せてみて",
    "blurry": "スマホを少し離して、ピントを合わせてみて",
    "out_of_frame": "紙を枠の中に入れてみて",
    "hidden": "手やペンをどけて、式が見えるようにしてみて",
}
FALLBACK_HINTS = {1: "今、何を求めようとしてる？", 2: UNREADABLE_HINT}
FALLBACK_STUCK_POINT = "読み取れず"
ANSWER_FALLBACK = "一緒に考えよう。今どこまでできたか、声に出してみて"
CHECK_REPLY = "できたボタンを押してみて"
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ComposedHint:
    speech: str
    display: str
    stuck_point: str
    source: HintSource
    model: str | None
    leak_check: LeakCheck
    problem_text: str | None
    leak_strings: list[str]


def fixed_hint(text: str, source: HintSource, leak_check: LeakCheck, known_leaks: list[str], persona: str = "teacher") -> ComposedHint:
    rendered = fallback_message(text, persona)
    if contains_leak(rendered, known_leaks):
        rendered = fallback_message(text, "teacher")
    return ComposedHint(rendered, rendered, FALLBACK_STUCK_POINT, source, None, leak_check, None, known_leaks)


def _read_problem(out: dict, known_problem: str | None, known_leaks: list[str]) -> tuple[str | None, list[str], bool]:
    problem_text = out["problem_text"] or None
    same = same_problem(problem_text, known_problem)
    inherited = known_leaks if same or not problem_text else []
    from_answer = leak_strings(out["final_answer"], [])
    written = out.get("written_lines") or []
    guarded = set(inherited) | set(leak_strings(out["final_answer"], out["key_values"]))
    answer_guarded = bool(from_answer) or (same and bool(known_leaks))
    return problem_text, without_written(sorted(guarded), written), answer_guarded


def _no_paper_in_hint(out: dict, known_problem: str | None) -> bool:
    if out["readable"] is not True:
        return False
    return out.get("paper_visible") is False or not (out["problem_text"] or out.get("written_lines") or known_problem)


def _unreadable(out: dict, fallback: str, leaks: list[str], persona: str = "teacher") -> ComposedHint:
    reason = str(out.get("unreadable_reason", "other"))
    logger.info("unreadable reason=%s", reason)
    return fixed_hint(UNREADABLE_HINTS.get(reason, fallback), "fallback", LeakCheck(ok=True, fallback=False), leaks, persona)


def _checked(
    out: dict, model: str, problem_text: str | None, leaks: list[str], limits: tuple[int, int], fallback: str, persona: str
) -> ComposedHint:
    written_speech = out["speech"].strip()
    speech = to_reading(written_speech)
    display = out["display"].strip()
    stuck_point = out["stuck_point"] if out["stuck_point"] in STUCK_POINTS else STUCK_POINTS[-1]
    if any(contains_leak(text, leaks) for text in (speech, display)):
        return fixed_hint(fallback, "fallback", LeakCheck(ok=False, fallback=True), leaks, persona)
    speech_limit, display_limit = limits
    if not speech or not display or len(written_speech) > speech_limit or len(display) > display_limit:
        return fixed_hint(fallback, "fallback", LeakCheck(ok=True, fallback=False), leaks, persona)
    return ComposedHint(speech, display, stuck_point, "ai", model, LeakCheck(ok=True, fallback=False), problem_text, leaks)


def _unchecked_fallback(known_leaks: list[str], fallback: str, persona: str) -> ComposedHint:
    logger.warning("ai gave no answer to guard against; falling back")
    return fixed_hint(fallback, "fallback", LeakCheck(ok=True, fallback=False), known_leaks, persona)


def check_reply(known_leaks: list[str], persona: str = "teacher") -> ComposedHint:
    rendered = fallback_message(CHECK_REPLY, persona)
    return ComposedHint(rendered, rendered, "答えの確認", "fallback", None, LeakCheck(ok=True, fallback=False), None, known_leaks)


def answer_fallback(known_leaks: list[str], persona: str = "teacher") -> ComposedHint:
    return fixed_hint(ANSWER_FALLBACK, "fallback", LeakCheck(ok=True, fallback=False), known_leaks, persona)


async def compose_hint(
    ai: Gemini | None,
    model: str,
    frame: bytes | None,
    level: int,
    previous: list[str],
    known_problem: str | None,
    known_leaks: list[str],
    persona: str = "teacher",
) -> ComposedHint:
    if ai is None or frame is None:
        return fixed_hint(FALLBACK_HINTS[level], "fallback", LeakCheck(ok=True, fallback=False), known_leaks, persona)
    try:
        request = "\n".join([LEVEL_INSTRUCTIONS[level], *context_lines(previous, known_problem)])
        out = await ai.generate_json(model, persona_prompt(SYSTEM_PROMPT, persona), request, frame, HINT_SCHEMA)
        if out.get("paper_visible") is False and out["readable"] is not True:
            return _unreadable(out, UNREADABLE_HINT, known_leaks, persona)
        if _no_paper_in_hint(out, known_problem):
            return _unreadable({**out, "unreadable_reason": "out_of_frame"}, UNREADABLE_HINT, known_leaks, persona)
        problem_text, leaks, answer_guarded = _read_problem(out, known_problem, known_leaks)
        readable = out["readable"] is True
        if readable and not answer_guarded:
            return _unchecked_fallback(known_leaks, FALLBACK_HINTS[level], persona)
        hint = _checked(out, model, problem_text, leaks, (SPEECH_MAX_CHARS, DISPLAY_MAX_CHARS), FALLBACK_HINTS[level], persona)
    except (AIUnavailable, KeyError, TypeError, AttributeError) as error:
        logger.warning("hint failed: %r", error)
        return fixed_hint(FALLBACK_HINTS[level], "fallback", LeakCheck(ok=True, fallback=False), known_leaks, persona)
    if not readable and hint.leak_check.ok:
        return _unreadable(out, UNREADABLE_HINT, leaks, persona)
    return hint


async def compose_answer(
    ai: Gemini | None,
    model: str,
    frame: bytes | None,
    utterance: str,
    previous: list[str],
    known_problem: str | None,
    known_leaks: list[str],
    persona: str = "teacher",
) -> ComposedHint | None:
    if ai is None or frame is None:
        raise AIUnavailable("AI かフレームが無い")
    request = "\n".join([f"学習者の発話：「{utterance}」", *context_lines(previous, known_problem)])
    out = await ai.generate_json(model, persona_prompt(ANSWER_PROMPT, persona), request, frame, ANSWER_SCHEMA)
    try:
        if out["respond"] is not True:
            return None
        if out["readable"] is not True:
            return _unreadable(out, UNREADABLE_ANSWER, known_leaks, persona)
        if out.get("paper_visible") is False:
            if PAPER_POINTERS.search(f"{out['speech']} {out['display']}"):
                return _unreadable({**out, "unreadable_reason": "out_of_frame"}, UNREADABLE_ANSWER, known_leaks, persona)
            out = {**out, "problem_text": "", "written_lines": []}
        problem_text, leaks, answer_guarded = _read_problem(out, known_problem, known_leaks)
        if not answer_guarded and (problem_text or states_an_answer(f"{out['speech']} {out['display']}")):
            return _unchecked_fallback(known_leaks, ANSWER_FALLBACK, persona)
        return _checked(
            out, model, problem_text, leaks, (ANSWER_SPEECH_MAX_CHARS, ANSWER_DISPLAY_MAX_CHARS), ANSWER_FALLBACK, persona
        )
    except (KeyError, TypeError, AttributeError) as error:
        raise AIUnavailable("AI の応答の形が違う") from error


async def read_problem(ai: Gemini | None, model: str, frame: bytes | None, known_problem: str | None) -> str | None:
    if ai is None or frame is None:
        return None
    request = "\n".join(context_lines([], known_problem)) or "問題文を読み取ってください。"
    try:
        out = await ai.generate_json(model, READ_PROMPT, request, frame, READ_SCHEMA)
        if out.get("paper_visible") is False or out["readable"] is not True:
            return None
        return out["problem_text"].strip() or None
    except (AIUnavailable, KeyError, TypeError, AttributeError) as error:
        logger.warning("read problem failed: %r", error)
        return None
