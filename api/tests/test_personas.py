from dataclasses import replace
from unittest.mock import patch

import pytest

from app.hints import ANSWER_FALLBACK, CHECK_REPLY, FALLBACK_HINTS, UNREADABLE_ANSWER, UNREADABLE_HINTS
from app.personas import PERSONAS, fallback_message, get_persona, persona_options


def test_only_teacher_and_ikemen_are_available_with_their_end_messages():
    assert set(PERSONAS) == {"teacher", "ikemen"}
    assert get_persona().persona_id == "teacher"
    options = persona_options()
    assert [(item["id"], item["display_name"]) for item in options] == [("teacher", "家庭教師"), ("ikemen", "イケメン")]
    for option in options:
        assert option["end_message"] == PERSONAS[option["id"]].end_message
        assert set(option) == {"id", "display_name", "end_message"}


@pytest.mark.parametrize("persona", ["friend", "sister", "normal", "Teacher", " teacher ", ""])
def test_invalid_and_removed_personas_are_rejected(persona):
    with pytest.raises(ValueError):
        get_persona(persona)


def test_teacher_and_ikemen_supply_distinct_wording_instructions():
    teacher = get_persona("teacher").style_instruction
    ikemen = get_persona("ikemen").style_instruction
    assert "丁寧語" in teacher and "見てみましょう" in teacher
    assert "タメ口" in ikemen and "見てごらん" in ikemen
    assert "架空" in ikemen and "実在の人物をまねない" in ikemen
    assert teacher != ikemen
    for style in (teacher, ikemen):
        assert "SMAP" not in style and "ちょ、待てよ" not in style


@pytest.mark.parametrize("text", [*FALLBACK_HINTS.values(), *UNREADABLE_HINTS.values(), UNREADABLE_ANSWER, ANSWER_FALLBACK, CHECK_REPLY])
def test_teacher_keeps_each_existing_main_fixed_reply(text):
    assert fallback_message(text, "teacher") == text


@pytest.mark.parametrize(("original", "expected"), [
    ("今、何を求めようとしてる？", "さて、今は何を求めようとしてる？"),
    ("もう少し明るいところで見せてみて", "もう少し明るいところで見せてみようか。"),
    ("紙を枠の中に入れてみて", "紙を枠の中に入れてみようか。"),
    ("できたボタンを押してみて", "できたボタンを押してみようか。"),
])
def test_ikemen_rewords_known_fixed_replies_without_adding_math(original, expected):
    assert fallback_message(original, "ikemen") == expected


@pytest.mark.parametrize("persona", ["teacher", "ikemen"])
def test_unknown_text_is_preserved_without_a_template_or_a_new_shorter_limit(persona):
    text = "見" * 60
    assert fallback_message(text, persona) == text


def test_fixed_wording_can_be_customized_in_the_persona_setting():
    original = "紙を枠の中に入れてみて"
    custom = replace(PERSONAS["ikemen"], fixed_messages={original: "紙を枠の中に入れてみよう。"})
    with patch.dict(PERSONAS, {"ikemen": custom}):
        assert fallback_message(original, "ikemen") == "紙を枠の中に入れてみよう。"


@pytest.mark.parametrize(("persona", "expected"), [
    ("teacher", "今日もよく頑張りました。できるようになったことを記録で振り返ってみましょう。"),
    ("ikemen", "今日はここまで。よくやったじゃん。頑張った証拠、記録で確かめてみな。"),
])
def test_ending_uses_the_selected_personas_full_fixed_message(persona, expected):
    assert PERSONAS[persona].end_message == expected
