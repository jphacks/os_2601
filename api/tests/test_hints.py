import asyncio
from dataclasses import replace
from unittest.mock import patch

import pytest

from app.check import CORRECT_TEXT, FAILED_TEXT, judge
from app.gemini import AIUnavailable
from app.hints import (
    ANSWER_FALLBACK,
    UNREADABLE_ANSWER,
    ANSWER_SPEECH_MAX_CHARS,
    DISPLAY_MAX_CHARS,
    FALLBACK_HINTS,
    SPEECH_MAX_CHARS,
    UNREADABLE_HINT,
    compose_answer,
    compose_hint,
)
from app.state import LeakCheck
from app.personas import PERSONAS, get_persona, render_h2

FRAME = b"\xff\xd8jpeg"
MODEL = "gemini-test"


class FakeAI:
    def __init__(self, reply: dict | None = None, error: Exception | None = None) -> None:
        self.reply = reply
        self.error = error
        self.requests: list[str] = []
        self.systems: list[str] = []
        self.schemas: list[dict] = []

    async def generate_json(self, model: str, system: str, text: str, image_jpeg: bytes, schema: dict) -> dict:
        self.requests.append(text)
        self.systems.append(system)
        self.schemas.append(schema)
        if self.error:
            raise self.error
        return self.reply


def ai_hint(focus: str, action: str = "review", variant: str = "plain") -> dict:
    return {
        "readable": True,
        "problem_text": "2x - 7 = 4x + 3",
        "final_answer": "x = -5",
        "key_values": ["-2x = 10"],
        "stuck_point": "移項の符号",
        "focus": focus,
        "action": action,
        "variant": variant,
    }


def compose(ai: FakeAI | None, frame: bytes | None = FRAME, level: int = 1, known_leaks: list[str] | None = None, persona: str = "teacher"):
    return asyncio.run(compose_hint(ai, MODEL, frame, level, ["前のヒント"], "2x - 7 = 4x + 3", known_leaks or [], persona))


def test_ai_hint_is_used_from_the_first_stuck_and_answer_is_kept_server_side() -> None:
    ai = FakeAI(ai_hint("右辺に移したときの符号"))
    hint = compose(ai)
    assert (hint.speech, hint.source, hint.model) == ("右辺に移したときの符号を見直してみましょう。", "gpt", MODEL)
    assert hint.display == hint.speech
    assert len(ai.requests) == 1
    assert hint.leak_check == LeakCheck(ok=True, fallback=False)
    assert hint.problem_text == "2x - 7 = 4x + 3"
    assert {"x=-5", "-5", "-2x=10"} <= set(hint.leak_strings)
    assert "段階 1" in ai.requests[0] and "前のヒント" in ai.requests[0] and "前に読み取った問題文" in ai.requests[0]


def test_hint_that_says_the_answer_is_replaced_with_a_fixed_question() -> None:
    hint = compose(FakeAI(ai_hint("x は マイナス 5 だよ")), level=2)
    assert hint.speech == FALLBACK_HINTS[2]
    assert (hint.source, hint.leak_check) == ("fallback", LeakCheck(ok=False, fallback=True))


def test_answer_from_an_earlier_hint_still_blocks_a_leak() -> None:
    reply = ai_hint("-2x = 10 にしてみて")
    reply.update(final_answer="", key_values=[])
    hint = compose(FakeAI(reply), known_leaks=["-2x=10"])
    assert hint.leak_check == LeakCheck(ok=False, fallback=True)


def test_unreadable_or_empty_hint_falls_back_to_a_fixed_question() -> None:
    unreadable = ai_hint("見てみて")
    unreadable.update(readable=False, unreadable_reason="other")
    assert compose(FakeAI(unreadable)).speech == UNREADABLE_HINT
    assert compose(FakeAI(ai_hint("   "))).source == "fallback"


def test_leak_strings_of_a_different_problem_are_dropped() -> None:
    reply = ai_hint("かっこを外したところを見てみて")
    reply.update(problem_text="3(x + 2) = 2x + 11", final_answer="x = 5", key_values=[])
    hint = compose(FakeAI(reply), known_leaks=["x=-5"])
    assert "x=-5" not in hint.leak_strings


def test_hint_uses_the_final_length_without_cutting_the_focus() -> None:
    focus = "見" * (SPEECH_MAX_CHARS - len("を見直してみましょう。"))
    hint = compose(FakeAI(ai_hint(focus)))
    assert len(hint.speech) == SPEECH_MAX_CHARS
    assert hint.speech == hint.display
    assert compose(FakeAI(ai_hint(focus + "見"))).source == "fallback"


def test_label_outside_the_fixed_list_becomes_other() -> None:
    reply = ai_hint("2行目の右辺を見てみて")
    reply["stuck_point"] = "x=-5 の確認"
    assert compose(FakeAI(reply)).stuck_point == "その他"
    reply["stuck_point"] = "係数で割る"
    assert compose(FakeAI(reply)).stuck_point == "係数で割る"


def test_speech_is_normalized_for_reading_before_the_leak_check() -> None:
    reply = ai_hint("二行目の 4x = -4")
    assert compose(FakeAI(reply)).speech == "2行目の 4エックス イコール マイナス 4を見直してみましょう。"
    assert compose(FakeAI(ai_hint("x = -5 にしてみて"))).leak_check == LeakCheck(ok=False, fallback=True)


def test_speech_length_is_measured_after_symbols_are_spelled_out() -> None:
    reply = ai_hint("3行目の 2x-7=4x+3 の左辺の -7")
    assert len(reply["focus"]) < 40
    assert compose(FakeAI(reply)).source == "fallback"


def test_inherited_short_values_stay_guarded() -> None:
    reply = ai_hint("エックス は マイナス 5 だよ")
    reply.update(final_answer="", key_values=[])
    assert compose(FakeAI(reply), known_leaks=["-5", "x=-5"]).leak_check == LeakCheck(ok=False, fallback=True)


def test_values_already_on_the_paper_may_be_quoted() -> None:
    reply = ai_hint("マイナス2エックス イコール 10")
    reply["written_lines"] = ["2x - 7 = 4x + 3", "-2x = 10"]
    assert compose(FakeAI(reply)).source == "gpt"


def test_unreadable_reason_picks_the_fixed_text() -> None:
    reply = ai_hint("見てみて")
    reply.update(readable=False, unreadable_reason="out_of_frame")
    assert compose(FakeAI(reply)).speech == "紙を枠の中に入れてみて"


def test_earlier_hints_are_listed_one_per_line_in_order() -> None:
    ai = FakeAI(ai_hint("2行目を見てみて"))
    asyncio.run(compose_hint(ai, MODEL, FRAME, 1, ["1 つ目", "2 つ目"], None, []))
    assert "1. 1 つ目\n2. 2 つ目" in ai.requests[0]


def test_ai_failure_or_missing_frame_falls_back_to_a_fixed_question() -> None:
    assert compose(FakeAI(error=AIUnavailable("timeout"))).speech == FALLBACK_HINTS[1]
    assert compose(FakeAI({"speech": "欠けた応答"})).source == "fallback"
    assert compose(FakeAI(ai_hint("見てみて")), frame=None).speech == FALLBACK_HINTS[1]
    assert compose(None).source == "fallback"


def test_check_uses_fixed_texts_and_falls_back_to_unreadable() -> None:
    ai = FakeAI({"readable": True, "final_answer_seen": "x=-5", "verdict": "correct"})
    correct = asyncio.run(judge(ai, MODEL, FRAME, "2x - 7 = 4x + 3"))
    assert (correct.verdict, correct.speech) == ("correct", CORRECT_TEXT)
    assert "見る問題：2x - 7 = 4x + 3" in ai.requests[0]
    odd = asyncio.run(judge(FakeAI({"verdict": "maybe"}), MODEL, FRAME, None))
    assert odd.speech == FAILED_TEXT
    failed = asyncio.run(judge(FakeAI(error=AIUnavailable("timeout")), MODEL, FRAME, None))
    assert (failed.verdict, failed.speech) == ("unreadable", FAILED_TEXT)


def answer(ai: FakeAI | None, utterance: str = "移項って何？"):
    return asyncio.run(compose_answer(ai, MODEL, FRAME, utterance, [], None, []))


def ai_answer(speech: str, respond: bool = True) -> dict:
    reply = ai_hint(speech)
    reply["respond"] = respond
    reply["speech"] = speech
    reply["display"] = speech
    return reply


def test_answer_about_an_unreadable_paper_tells_the_reason_instead_of_guessing() -> None:
    reply = ai_answer("2行目の右辺の4を見てみて")
    reply.update(readable=False, unreadable_reason="dark")
    hint = answer(FakeAI(reply))
    assert (hint.speech, hint.source) == ("もう少し明るいところで見せてみて", "fallback")
    reply.update(unreadable_reason="other")
    assert answer(FakeAI(reply)).speech == UNREADABLE_ANSWER


def test_question_that_needs_no_paper_is_answered_even_without_anything_to_guard() -> None:
    reply = ai_answer("移項は、項を反対の辺に移すことだよ")
    reply.update(problem_text="", final_answer="", key_values=[])
    assert answer(FakeAI(reply)).source == "gpt"


def test_answer_that_gives_away_the_value_is_replaced_and_an_overlong_one_falls_back() -> None:
    assert answer(FakeAI(ai_answer("答えは x イコール マイナス 5 だよ"))).leak_check == LeakCheck(ok=False, fallback=True)
    assert answer(FakeAI(ai_answer("見" * ANSWER_SPEECH_MAX_CHARS))).source == "gpt"
    assert answer(FakeAI(ai_answer("見" * (ANSWER_SPEECH_MAX_CHARS + 1)))).source == "fallback"


def test_no_answer_when_the_ai_decides_not_to_respond() -> None:
    assert answer(FakeAI(ai_answer("", respond=False))) is None


def test_ai_failure_is_raised_so_the_caller_can_choose_a_fixed_reply() -> None:
    with pytest.raises(AIUnavailable):
        answer(FakeAI(error=AIUnavailable("timeout")))
    with pytest.raises(AIUnavailable):
        answer(None)


def test_answer_with_nothing_to_check_leaks_against_is_not_used() -> None:
    reply = ai_answer("移項は、項を反対の辺に移すことだよ")
    reply.update(final_answer="", key_values=[])
    assert answer(FakeAI(reply)).speech == ANSWER_FALLBACK


@pytest.mark.parametrize("persona", ["teacher", "ikemen"])
@pytest.mark.parametrize("action", ["review", "read", "compare", "next_step"])
def test_persona_uses_one_shared_focus_and_action_in_a_single_ai_request(persona: str, action: str) -> None:
    focus = "1行目と2行目"
    ai = FakeAI(ai_hint(focus, action, "warm"))
    hint = compose(ai, persona=persona)
    expected = render_h2(focus, persona, action, "warm")
    assert hint.source == "gpt"
    assert (hint.speech, hint.display) == (expected.speech, expected.display)
    assert hint.speech.count(focus) == 1
    assert (hint.focus, hint.action) == (focus, action)
    assert len(ai.requests) == 1
    assert get_persona(persona).style_instruction in ai.systems[0]
    assert {"focus", "action", "variant"} <= set(ai.schemas[0]["required"])
    assert "speech" not in ai.schemas[0]["properties"]


def test_same_mathematical_input_is_sent_for_both_personas() -> None:
    teacher = FakeAI(ai_hint("右辺の符号", "review", "playful"))
    ikemen = FakeAI(ai_hint("右辺の符号", "review", "playful"))
    teacher_hint = compose(teacher, persona="teacher")
    ikemen_hint = compose(ikemen, persona="ikemen")
    assert teacher.systems == ikemen.systems
    assert teacher.requests == ikemen.requests
    assert teacher.schemas == ikemen.schemas
    assert teacher_hint.focus == ikemen_hint.focus == "右辺の符号"
    assert teacher_hint.action == ikemen_hint.action == "review"
    assert teacher_hint.speech != ikemen_hint.speech


def test_persona_variants_do_not_replay_reference_lines_or_ai_free_text() -> None:
    reply = ai_hint("右辺の符号", variant="playful")
    reply.update(speech="答えは5です", display="答えは5です")
    hint = compose(FakeAI(reply), persona="ikemen")
    assert hint.speech == "ここはスマートに。右辺の符号を見直してみよう。"
    assert hint.display == hint.speech
    assert hint.speech not in PERSONAS["ikemen"].references.normal + PERSONAS["ikemen"].references.special


@pytest.mark.parametrize("change", [{"action": "solve"}, {"variant": "invent"}, {"focus": ""}, {"focus": "記号√"}])
def test_invalid_shared_focus_or_expression_falls_back_without_another_call(change: dict) -> None:
    reply = ai_hint("右辺の符号")
    reply.update(change)
    ai = FakeAI(reply)
    assert compose(ai).source == "fallback"
    assert len(ai.requests) == 1


def test_missing_shared_fields_never_uses_the_old_free_text_response() -> None:
    reply = ai_hint("右辺の符号")
    del reply["focus"]
    reply.update(speech="古い自由文", display="古い自由文")
    assert compose(FakeAI(reply)).source == "fallback"


def test_final_persona_expression_is_checked_for_leaks_too() -> None:
    config = replace(PERSONAS["ikemen"], h2_template="{focus}、マイナス5にしてみよう。")
    with patch.dict(PERSONAS, {"ikemen": config}):
        hint = compose(FakeAI(ai_hint("右辺の符号")), persona="ikemen")
    assert hint.leak_check == LeakCheck(ok=False, fallback=True)


def test_unknown_persona_is_rejected_even_without_a_frame() -> None:
    with pytest.raises(ValueError):
        compose(None, persona="friend")


def test_fallback_and_unreadable_text_follow_the_selected_persona() -> None:
    hint = compose(None, persona="ikemen")
    assert hint.speech == "一息つこう。" + FALLBACK_HINTS[1]
    reply = ai_hint("右辺の符号")
    reply.update(readable=False, unreadable_reason="dark")
    hint = compose(FakeAI(reply), persona="ikemen")
    assert hint.speech == hint.display == "一息つこう。もう少し明るいところで見せてみて"


def test_voice_answer_uses_persona_style_and_identical_bounded_text() -> None:
    ai = FakeAI(ai_answer("移項は、項を反対の辺に移すことだよ"))
    hint = asyncio.run(compose_answer(ai, MODEL, FRAME, "移項って何？", [], None, [], "ikemen"))
    assert hint.speech == hint.display == "移項は、項を反対の辺に移すことだよ"
    assert len(hint.speech) <= 40 and len(ai.requests) == 1
    assert get_persona("ikemen").style_instruction in ai.systems[0]
    assert "variantの選択だけ" not in ai.systems[0]


def test_voice_answer_checks_raw_display_and_final_normalized_length() -> None:
    reply = ai_answer("右辺を見てみて")
    reply["display"] = "答えは x=-5 だよ"
    assert answer(FakeAI(reply)).leak_check == LeakCheck(ok=False, fallback=True)
    reply = ai_answer("二行目の 2x-7=4x+3 の左辺の -7 を見てみて")
    assert len(reply["speech"]) <= 40
    assert answer(FakeAI(reply)).source == "fallback"
