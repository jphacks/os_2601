from dataclasses import replace
from unittest.mock import patch

import pytest

from app.hints import ANSWER_FALLBACK, CHECK_REPLY, FALLBACK_HINTS, UNREADABLE_ANSWER, UNREADABLE_HINTS
from app.personas import PERSONAS, end_message, fallback_message, get_persona, persona_options


def test_only_teacher_and_ikemen_are_available_with_their_end_messages():
    assert set(PERSONAS) == {"teacher", "ikemen"}
    assert get_persona().persona_id == "teacher"
    options = persona_options()
    assert [(item["id"], item["display_name"]) for item in options] == [("teacher", "家庭教師"), ("ikemen", "イケメン")]
    for option in options:
        assert option["end_message"] == end_message(option["id"]).display
        assert set(option) == {"id", "display_name", "end_message"}


@pytest.mark.parametrize("persona", ["friend", "sister", "normal", "Teacher", " teacher ", "", None, 1, [], {}])
def test_invalid_and_removed_personas_are_rejected(persona):
    with pytest.raises(ValueError):
        get_persona(persona)


def test_mismatched_configuration_is_rejected():
    with patch.dict(PERSONAS, {"teacher": PERSONAS["ikemen"]}):
        with pytest.raises(ValueError, match="人格ID"):
            get_persona("teacher")


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
    message = fallback_message(text, "teacher")
    assert message.speech == message.display == text


@pytest.mark.parametrize(("original", "expected"), [
    ("今、何を求めようとしてる？", "さて、今は何を求めようとしてる？"),
    ("もう少し明るいところで見せてみて", "もう少し明るいところで見せてみようか。"),
    ("紙を枠の中に入れてみて", "紙を枠の中に入れてみようか。"),
    ("できたボタンを押してみて", "できたボタンを押してみようか。"),
])
def test_ikemen_rewords_known_fixed_replies_without_adding_math(original, expected):
    assert fallback_message(original, "ikemen").speech == expected
    assert fallback_message(original, "ikemen").display == expected


@pytest.mark.parametrize("persona", ["teacher", "ikemen"])
def test_unknown_text_is_preserved_without_a_template_or_a_new_shorter_limit(persona):
    text = "見" * 60
    assert fallback_message(text, persona).speech == text
    assert fallback_message(text, persona).display == text


def test_fixed_and_ending_wording_can_be_customized_in_the_persona_setting():
    original = "紙を枠の中に入れてみて"
    custom = replace(PERSONAS["ikemen"], fixed_messages={original: "紙を枠の中に入れてみよう。"}, end_message="今日の取り組みを振り返ってみよう。")
    with patch.dict(PERSONAS, {"ikemen": custom}):
        assert fallback_message(original, "ikemen").speech == "紙を枠の中に入れてみよう。"
        assert end_message("ikemen").speech == "今日の取り組みを振り返ってみよう。"


@pytest.mark.parametrize(("persona", "expected"), [
    ("teacher", "今日もよく頑張りました。できるようになったことを記録で振り返ってみましょう。"),
    ("ikemen", "今日はここまで。よくやったじゃん。頑張った証拠、記録で確かめてみな。"),
])
def test_ending_uses_the_selected_personas_full_fixed_message(persona, expected):
    assert end_message(persona).speech == end_message(persona).display == expected


@pytest.mark.parametrize("text", ["", " ", "　", None, 1, [], {}])
def test_empty_or_non_text_fixed_messages_are_rejected(text):
    with pytest.raises(ValueError):
        fallback_message(text)
