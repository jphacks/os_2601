import asyncio

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

FRAME = b"\xff\xd8jpeg"
MODEL = "gemini-test"


class FakeAI:
    def __init__(self, reply: dict | None = None, error: Exception | None = None) -> None:
        self.reply = reply
        self.error = error
        self.requests: list[str] = []

    async def generate_json(self, model: str, system: str, text: str, image_jpeg: bytes, schema: dict) -> dict:
        self.requests.append(text)
        if self.error:
            raise self.error
        return self.reply


def ai_hint(speech: str) -> dict:
    return {
        "readable": True,
        "problem_text": "2x - 7 = 4x + 3",
        "final_answer": "x = -5",
        "key_values": ["-2x = 10"],
        "stuck_point": "移項の符号",
        "speech": speech,
        "display": speech,
    }


def compose(ai: FakeAI | None, frame: bytes | None = FRAME, level: int = 1, known_leaks: list[str] | None = None):
    return asyncio.run(compose_hint(ai, MODEL, frame, level, ["前のヒント"], "2x - 7 = 4x + 3", known_leaks or []))


def test_ai_hint_is_used_from_the_first_stuck_and_answer_is_kept_server_side() -> None:
    ai = FakeAI(ai_hint("右辺に移したときの符号を見てみて"))
    hint = compose(ai)
    assert (hint.speech, hint.source, hint.model) == ("右辺に移したときの符号を見てみて", "gpt", MODEL)
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


def test_hint_over_the_requested_length_is_read_whole_up_to_the_limit_and_falls_back_beyond_it() -> None:
    at_limit = "見" * SPEECH_MAX_CHARS
    assert compose(FakeAI(ai_hint(at_limit))).speech == at_limit
    assert compose(FakeAI(ai_hint(at_limit + "て"))).source == "fallback"
    long_display = ai_hint("2行目を見てみて")
    long_display["display"] = "見" * (DISPLAY_MAX_CHARS + 1)
    assert compose(FakeAI(long_display)).source == "fallback"


def test_label_outside_the_fixed_list_becomes_other() -> None:
    reply = ai_hint("2行目の右辺を見てみて")
    reply["stuck_point"] = "x=-5 の確認"
    assert compose(FakeAI(reply)).stuck_point == "その他"
    reply["stuck_point"] = "係数で割る"
    assert compose(FakeAI(reply)).stuck_point == "係数で割る"


def test_speech_is_normalized_for_reading_before_the_leak_check() -> None:
    reply = ai_hint("二行目の 4x = -4 を見てみて")
    assert compose(FakeAI(reply)).speech == "2行目の 4エックス イコール マイナス 4 を見てみて"
    assert compose(FakeAI(ai_hint("x = -5 にしてみて"))).leak_check == LeakCheck(ok=False, fallback=True)


def test_speech_length_is_measured_before_symbols_are_spelled_out() -> None:
    reply = ai_hint("3行目の 2x-7=4x+3 の左辺の -7 を見てみて、そのあと右辺も")
    assert len(reply["speech"]) <= 60
    assert compose(FakeAI(reply)).source == "gpt"


def test_inherited_short_values_stay_guarded() -> None:
    reply = ai_hint("エックス は マイナス 5 だよ")
    reply.update(final_answer="", key_values=[])
    assert compose(FakeAI(reply), known_leaks=["-5", "x=-5"]).leak_check == LeakCheck(ok=False, fallback=True)


def test_values_already_on_the_paper_may_be_quoted() -> None:
    reply = ai_hint("マイナス2エックス イコール 10 の両辺を見てみて")
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
