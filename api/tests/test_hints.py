import asyncio
from dataclasses import replace
from unittest.mock import patch

import pytest

from app.check import CORRECT_TEXT, FAILED_TEXT, judge
from app.gemini import AIUnavailable
from app.hints import (
    ANSWER_FALLBACK,
    ANSWER_SPEECH_MAX_CHARS,
    DISPLAY_MAX_CHARS,
    FALLBACK_HINTS,
    SPEECH_MAX_CHARS,
    UNREADABLE_ANSWER,
    UNREADABLE_HINT,
    asks_if_correct,
    compose_answer,
    compose_hint,
    read_problem,
)
from app.personas import PERSONAS, fallback_message, get_persona
from app.state import LeakCheck

FRAME = b"\xff\xd8jpeg"
MODEL = "gemini-test"


class FakeAI:
    def __init__(self, reply: dict | None = None, error: Exception | None = None) -> None:
        self.reply = reply
        self.error = error
        self.requests: list[str] = []
        self.systems: list[str] = []
        self.schemas: list[dict] = []
        self.frames: list[bytes] = []

    async def generate_json(self, model: str, system: str, text: str, image_jpeg: bytes, schema: dict) -> dict:
        self.requests.append(text)
        self.systems.append(system)
        self.schemas.append(schema)
        self.frames.append(image_jpeg)
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


def compose(ai: FakeAI | None, frame: bytes | None = FRAME, level: int = 1, known_leaks: list[str] | None = None, persona: str = "teacher"):
    return asyncio.run(compose_hint(ai, MODEL, frame, level, ["前のヒント"], "2x - 7 = 4x + 3", known_leaks or [], persona))


def test_ai_hint_is_used_from_the_first_stuck_and_answer_is_kept_server_side() -> None:
    ai = FakeAI(ai_hint("右辺に移したときの符号を見てみて"))
    hint = compose(ai)
    assert (hint.speech, hint.source, hint.model) == ("右辺に移したときの符号を見てみて", "ai", MODEL)
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
    assert compose(FakeAI(reply)).source == "ai"


def test_inherited_short_values_stay_guarded() -> None:
    reply = ai_hint("エックス は マイナス 5 だよ")
    reply.update(final_answer="", key_values=[])
    assert compose(FakeAI(reply), known_leaks=["-5", "x=-5"]).leak_check == LeakCheck(ok=False, fallback=True)


def test_values_already_on_the_paper_may_be_quoted() -> None:
    reply = ai_hint("マイナス2エックス イコール 10 の両辺を見てみて")
    reply["written_lines"] = ["2x - 7 = 4x + 3", "-2x = 10"]
    assert compose(FakeAI(reply)).source == "ai"


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
    assert answer(FakeAI(reply)).source == "ai"


def test_answer_that_gives_away_the_value_is_replaced_and_an_overlong_one_falls_back() -> None:
    assert answer(FakeAI(ai_answer("答えは x イコール マイナス 5 だよ"))).leak_check == LeakCheck(ok=False, fallback=True)
    assert answer(FakeAI(ai_answer("見" * ANSWER_SPEECH_MAX_CHARS))).source == "ai"
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
def test_gemini_keeps_the_specific_location_operation_and_separate_display(persona: str) -> None:
    speech = "1行目の左辺の定数項を、反対の辺へ移してみて"
    display = "1行目の左辺の -7 を、右辺へ移してみて"
    reply = {**ai_hint(speech), "display": display}
    ai = FakeAI(reply)
    hint = compose(ai, level=2, persona=persona)
    assert (hint.speech, hint.display, hint.source) == (speech, display, "ai")
    assert len(ai.requests) == 1 and ai.frames == [FRAME]
    assert get_persona(persona).style_instruction in ai.systems[0]
    other = "ikemen" if persona == "teacher" else "teacher"
    assert get_persona(other).style_instruction not in ai.systems[0]
    assert {"speech", "display"} <= set(ai.schemas[0]["required"])
    assert not {"focus", "action", "variant"} & set(ai.schemas[0]["properties"])


def test_only_the_style_changes_in_the_hint_request_between_personas() -> None:
    teacher = FakeAI(ai_hint("1行目の左辺の符号を、もう一度確認してみましょう。"))
    ikemen = FakeAI(ai_hint("1行目の左辺の符号を、もう一度確認してみよう。"))
    teacher_hint = compose(teacher, persona="teacher")
    ikemen_hint = compose(ikemen, persona="ikemen")
    assert teacher.requests == ikemen.requests
    assert teacher.frames == ikemen.frames
    assert teacher.schemas == ikemen.schemas
    assert teacher.systems[0].replace(get_persona("teacher").style_instruction, "STYLE") == ikemen.systems[0].replace(get_persona("ikemen").style_instruction, "STYLE")
    assert teacher_hint.display != ikemen_hint.display
    assert "1行目の左辺の符号" in teacher_hint.display and "1行目の左辺の符号" in ikemen_hint.display


def test_changing_the_persona_setting_updates_the_next_prompt() -> None:
    custom = replace(PERSONAS["ikemen"], style_instruction="穏やかなタメ口で、一つだけ問いかける。")
    ai = FakeAI(ai_hint("左辺を見てみて"))
    with patch.dict(PERSONAS, {"ikemen": custom}):
        assert compose(ai, persona="ikemen").source == "ai"
    assert custom.style_instruction in ai.systems[0]


@pytest.mark.parametrize("persona", ["teacher", "ikemen"])
def test_both_personas_keep_the_main_hint_and_answer_length_limits(persona: str) -> None:
    reply = {**ai_hint("見" * 60), "display": "見" * 80}
    hint = compose(FakeAI(reply), persona=persona)
    assert (len(hint.speech), len(hint.display), hint.source) == (60, 80, "ai")
    for field, limit in (("speech", 60), ("display", 80)):
        assert compose(FakeAI({**reply, field: "見" * (limit + 1)}), persona=persona).source == "fallback"
    reply = {**ai_answer("見" * 100), "display": "見" * 120}
    hint = asyncio.run(compose_answer(FakeAI(reply), MODEL, FRAME, "移項って何？", [], None, [], persona))
    assert (len(hint.speech), len(hint.display), hint.source) == (100, 120, "ai")
    for field, limit in (("speech", 100), ("display", 120)):
        too_long = {**reply, field: "見" * (limit + 1)}
        assert asyncio.run(compose_answer(FakeAI(too_long), MODEL, FRAME, "移項って何？", [], None, [], persona)).source == "fallback"


@pytest.mark.parametrize("field", ["speech", "display"])
@pytest.mark.parametrize("persona", ["teacher", "ikemen"])
def test_each_generated_output_still_runs_through_the_answer_leak_check(field: str, persona: str) -> None:
    reply = {**ai_hint("左辺を見てみて"), field: "答えは x=-5 だよ"}
    hint = compose(FakeAI(reply), level=2, persona=persona)
    assert hint.leak_check == LeakCheck(ok=False, fallback=True)
    assert hint.speech == fallback_message(FALLBACK_HINTS[2], persona)
    assert "x=-5" not in hint.display


@pytest.mark.parametrize("persona", ["teacher", "ikemen"])
def test_fixed_failures_and_unreadable_replies_use_the_persona_without_more_ai_calls(persona: str) -> None:
    assert compose(None, persona=persona).speech == fallback_message(FALLBACK_HINTS[1], persona)
    ai = FakeAI({**ai_hint("左辺を見てみて"), "readable": False, "unreadable_reason": "dark"})
    hint = compose(ai, persona=persona)
    assert hint.speech == hint.display == fallback_message("もう少し明るいところで見せてみて", persona)
    assert hint.source == "fallback" and len(ai.requests) == 1


@pytest.mark.parametrize("persona", ["teacher", "ikemen"])
def test_voice_answer_uses_the_same_style_and_preserves_gemini_display(persona: str) -> None:
    speech = "移項は、項を反対の辺に移すことだよ"
    display = "移項は、項を反対の辺へ移し、符号を変えることです。"
    ai = FakeAI({**ai_answer(speech), "display": display})
    hint = asyncio.run(compose_answer(ai, MODEL, FRAME, "移項って何？", [], None, [], persona))
    assert (hint.speech, hint.display, hint.source) == (speech, display, "ai")
    assert get_persona(persona).style_instruction in ai.systems[0]
    assert len(ai.requests) == 1 and ai.frames == [FRAME]


def test_unknown_persona_is_rejected_before_a_missing_frame_fallback() -> None:
    with pytest.raises(ValueError):
        compose(None, persona="friend")


def test_a_hint_without_the_ai_s_own_answer_falls_back_because_it_cannot_be_checked() -> None:
    reply = {**ai_hint("エックスは2だよ"), "final_answer": "", "key_values": []}
    hint = compose(FakeAI(reply))
    assert (hint.speech, hint.source) == (FALLBACK_HINTS[1], "fallback")


@pytest.mark.parametrize("utterance", ["正解がわからない、教えて", "正しいやり方がわからない"])
def test_asking_for_help_is_not_taken_as_asking_if_the_answer_is_right(utterance: str) -> None:
    assert not asks_if_correct(utterance)


def test_asking_if_the_answer_is_right_is_still_recognized() -> None:
    assert asks_if_correct("これで合ってる？")


def test_a_hint_without_any_problem_text_or_answer_still_falls_back() -> None:
    reply = {**ai_hint("エックスは2だよ"), "problem_text": "", "final_answer": "", "key_values": [], "written_lines": ["2x = 4"]}
    assert asyncio.run(compose_hint(FakeAI(reply), MODEL, FRAME, 1, [], None, [], "teacher")).source == "fallback"


def test_a_hint_is_kept_when_the_learner_already_wrote_every_value() -> None:
    reply = {**ai_hint("最後の行を見直してみて"), "written_lines": ["2x - 7 = 4x + 3", "-2x = 10", "x = -5"]}
    assert compose(FakeAI(reply)).source == "ai"


def test_asking_if_unsure_whether_it_is_right_is_still_a_check_question() -> None:
    assert asks_if_correct("これ合ってるかわからない")


def test_a_hint_with_only_intermediate_values_on_a_new_problem_falls_back() -> None:
    reply = {**ai_hint("エックスはマイナス5だよ"), "final_answer": "", "key_values": ["-2x=10"]}
    assert asyncio.run(compose_hint(FakeAI(reply), MODEL, FRAME, 1, [], None, [], "teacher")).source == "fallback"


def test_a_hint_whose_answer_gives_nothing_to_guard_falls_back() -> None:
    reply = {**ai_hint("答えはイだよ"), "final_answer": "イ", "key_values": []}
    assert asyncio.run(compose_hint(FakeAI(reply), MODEL, FRAME, 1, [], None, [], "teacher")).source == "fallback"


def test_an_unguarded_voice_answer_that_states_a_value_falls_back() -> None:
    reply = ai_answer("x は 5 だよ")
    reply.update(problem_text="", final_answer="", key_values=[])
    assert answer(FakeAI(reply)).source == "fallback"


@pytest.mark.parametrize("utterance", ["これ正しいかわからない", "これ正解？", "合ってるかな"])
def test_check_questions_in_other_words(utterance: str) -> None:
    assert asks_if_correct(utterance)


@pytest.mark.parametrize("utterance", ["これで正しいですか", "正解ですか？", "これ正解だよね？", "あってますか", "合っていますか", "正解かどうかわからない", "正しいか教えて", "これで正解。"])
def test_polite_check_questions_are_recognized(utterance: str) -> None:
    assert asks_if_correct(utterance)


@pytest.mark.parametrize("utterance", ["何が正解かわからない", "どうすれば正解か教えて", "話し合っているの？"])
def test_help_that_mentions_the_right_answer_is_not_a_check_question(utterance: str) -> None:
    assert not asks_if_correct(utterance)


def test_an_unguarded_fallback_keeps_the_earlier_problem_and_guard() -> None:
    reply = {**ai_hint("見てみて"), "problem_text": "2x-7=4x+5", "final_answer": "", "key_values": []}
    hint = asyncio.run(compose_hint(FakeAI(reply), MODEL, FRAME, 1, [], "2x - 7 = 4x + 3", ["x=-5"], "teacher"))
    assert (hint.source, hint.problem_text, hint.leak_strings) == ("fallback", None, ["x=-5"])


def test_an_empty_problem_text_does_not_count_as_the_same_problem() -> None:
    reply = {**ai_hint("エックスは3だよ"), "problem_text": "", "final_answer": "", "key_values": [], "written_lines": ["3x = 9"]}
    hint = asyncio.run(compose_hint(FakeAI(reply), MODEL, FRAME, 1, [], "2x - 7 = 4x + 3", ["x=-5"], "teacher"))
    assert (hint.source, hint.speech) == ("fallback", FALLBACK_HINTS[1])


def test_an_example_equation_in_an_unguarded_explanation_is_kept() -> None:
    reply = ai_answer("例えば x+2=5 なら、2 を右辺に移すと x=5-2 になるよ")
    reply.update(problem_text="", final_answer="", key_values=[], written_lines=["2x = 4"])
    assert answer(FakeAI(reply)).source == "ai"


def test_a_photo_without_paper_gets_the_out_of_frame_reply() -> None:
    reply = {**ai_hint("1行目の右辺の計算を見てみましょう"), "paper_visible": False}
    hint = compose(FakeAI(reply))
    assert (hint.speech, hint.source, hint.problem_text) == ("紙を枠の中に入れてみて", "fallback", None)


def test_a_readable_photo_with_no_problem_and_no_writing_is_treated_as_no_paper() -> None:
    reply = {**ai_hint("1行目を見てみましょう"), "problem_text": "", "written_lines": []}
    assert asyncio.run(compose_hint(FakeAI(reply), MODEL, FRAME, 1, [], None, [], "teacher")).speech == "紙を枠の中に入れてみて"


def test_a_dark_photo_keeps_its_own_reason() -> None:
    reply = {**ai_hint("見てみて"), "paper_visible": False, "readable": False, "unreadable_reason": "dark", "problem_text": "", "written_lines": []}
    assert compose(FakeAI(reply)).speech == "もう少し明るいところで見せてみて"


def test_reading_a_photo_without_paper_gives_no_problem_text() -> None:
    ai = FakeAI({"paper_visible": False, "problem_text": "3x + 5 = 20", "readable": True})
    assert asyncio.run(read_problem(ai, MODEL, FRAME, None)) is None



def test_a_known_problem_keeps_a_guarded_hint_even_if_this_reply_lost_the_text() -> None:
    reply = {**ai_hint("2行目を見てみましょう"), "problem_text": "", "written_lines": []}
    hint = asyncio.run(compose_hint(FakeAI(reply), MODEL, FRAME, 1, [], "2x - 7 = 4x + 3", [], "teacher"))
    assert hint.source == "ai"


def test_a_voice_answer_pointing_at_lines_without_paper_is_replaced() -> None:
    reply = ai_answer("最後の式の x の係数で両辺を割ってみて")
    reply.update(paper_visible=False)
    replied = asyncio.run(compose_answer(FakeAI(reply), MODEL, FRAME, "次どうすればいい？", [], None, [], "teacher"))
    assert replied.speech == "紙を枠の中に入れてみて"


def test_a_voice_explanation_without_paper_is_kept() -> None:
    reply = ai_answer("移項は、項の符号を変えて左辺から右辺に移すことだよ")
    reply.update(paper_visible=False, final_answer="x = 3", key_values=["3x = 9"])
    kept = asyncio.run(compose_answer(FakeAI(reply), MODEL, FRAME, "移項って何？", [], "2x - 7 = 4x + 3", ["x=-5"], "teacher"))
    assert (kept.source, kept.problem_text, kept.leak_strings) == ("ai", None, ["x=-5"])


def test_a_voice_answer_without_paper_that_mentions_the_right_side_is_replaced() -> None:
    reply = ai_answer("右辺に移したときの符号、もう一回見てみて")
    reply.update(paper_visible=False)
    replied = asyncio.run(compose_answer(FakeAI(reply), MODEL, FRAME, "次どうすればいい？", [], None, [], "teacher"))
    assert replied.source == "fallback"


def test_a_voice_answer_with_nothing_on_paper_is_replaced_even_if_the_ai_says_there_is_paper() -> None:
    reply = ai_answer("1行目の右辺の符号、もう一回見てみて")
    reply.update(problem_text="", written_lines=[], final_answer="")
    replied = asyncio.run(compose_answer(FakeAI(reply), MODEL, FRAME, "次どうすればいい？", [], None, [], "teacher"))
    assert replied.speech == "紙を枠の中に入れてみて"


def test_a_paperless_photo_with_an_other_reason_asks_for_the_paper() -> None:
    reply = {**ai_hint("見てみて"), "paper_visible": False, "readable": False, "unreadable_reason": "other"}
    assert compose(FakeAI(reply)).speech == "紙を枠の中に入れてみて"


def test_a_voice_answer_on_a_paperless_photo_said_to_be_hidden_asks_for_the_paper() -> None:
    reply = {**ai_answer("見てみて"), "paper_visible": False, "readable": False, "unreadable_reason": "hidden"}
    assert answer(FakeAI(reply)).speech == "紙を枠の中に入れてみて"


def test_a_voice_answer_without_paper_still_keeps_the_ai_answer_as_a_guard() -> None:
    reply = ai_answer("両辺を3で割ると5になるよ")
    reply.update(paper_visible=False, final_answer="x = 5", key_values=["3x = 15"])
    replied = asyncio.run(compose_answer(FakeAI(reply), MODEL, FRAME, "割るって何？", [], None, [], "teacher"))
    assert replied.leak_check == LeakCheck(ok=False, fallback=True)


def test_a_dark_paperless_photo_keeps_the_earlier_guard() -> None:
    reply = {**ai_hint("見てみて"), "paper_visible": False, "readable": False, "unreadable_reason": "dark", "problem_text": "x + 1 = 3", "final_answer": "x = 2"}
    hint = asyncio.run(compose_hint(FakeAI(reply), MODEL, FRAME, 1, [], "2x - 7 = 4x + 3", ["x=-5"], "teacher"))
    assert (hint.speech, hint.leak_strings) == ("もう少し明るいところで見せてみて", ["x=-5"])
