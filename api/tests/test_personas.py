import unittest
from dataclasses import replace
from unittest.mock import patch

from app.personas import (
    HINT_ACTIONS,
    HINT_VARIANTS,
    IKEMEN_STYLE_PROMPT,
    PERSONAS,
    PersonaReferences,
    end_message,
    fallback_message,
    get_persona,
    persona_options,
    render_h2,
)

# Independent fixtures preserve the user's reference text, including quotation marks.
EXPECTED_NORMAL = (
    "「ちょ、待てよ！」その答えで決まり？ もう一歩、考えてみようぜ。",
    "できるかできないかじゃない。まずは、やるかやらないかだろ？",
    "おいおい、そこで諦めんのか？ 逃げるくらいなら、もう一回ぶつかってみな。",
    "いいじゃん。負けても楽しめるくらい、本気でやってみようぜ。",
    "「おっと、待った！」その公式、まだ使えるんじゃない？ ここで気づけたらカッコいいぜ。",
    "先が見えない？ だったら面白いじゃん。どんな答えにたどり着くか、楽しんでみな。",
    "手を抜くより、本気でやったほうが気持ちいいだろ？ さあ、次の一手だ。",
    "最初からできる必要なんてないさ。大事なのは、最後に自分で答えを出すことだろ？",
    "おっ、いい線いってるじゃん。でも、そこで満足するのはまだ早いぜ。",
    "「おっと、待った！」もう答えが分かった気になってない？ 最後まで考え抜いてこそ、カッコいいんじゃない？",
)
EXPECTED_SPECIAL = (
    "「あれこれ言うつもりはないさ。自分で気づいたことって、意外と忘れないもんだろ？ ヒントは出す。あとは自分で考えてみな。」",
    "「点数ばっか気にすんなよ。答案に書いてある自分の名前、胸張って言えるくらい頑張れたなら、それって結構カッコいいことだろ？」",
    "「点数より大事なもんもあるだろ？ ……おっと、待った！ 名前書き忘れて0点とか、そういう話じゃないからな？」",
)


class PersonaTests(unittest.TestCase):
    def test_only_teacher_and_ikemen_are_available(self):
        self.assertEqual(set(PERSONAS), {"teacher", "ikemen"})
        self.assertEqual(get_persona().persona_id, "teacher")
        options = persona_options()
        self.assertEqual([(item["id"], item["display_name"]) for item in options], [("teacher", "家庭教師"), ("ikemen", "イケメン")])
        for option in options:
            self.assertEqual(option["end_message"], end_message(option["id"]).display)
            self.assertNotIn("references", option)

    def test_invalid_and_removed_personas_are_rejected(self):
        for value in ("friend", "sister", "normal", "Teacher", " teacher ", "", None, 1, [], {}):
            with self.subTest(persona=value), self.assertRaises(ValueError):
                render_h2("右辺", value)

    def test_shared_focus_and_action_are_preserved_for_both_personas(self):
        expected = {"teacher": "右辺の符号を見直してみましょう。", "ikemen": "右辺の符号を見直してみよう。"}
        for persona, text in expected.items():
            self.assertEqual(render_h2("右辺の符号", persona).speech, text)
        for persona in ("teacher", "ikemen"):
            for action in HINT_ACTIONS:
                for variant in HINT_VARIANTS:
                    with self.subTest(persona=persona, action=action, variant=variant):
                        hint = render_h2("1行目と2行目", persona, action, variant)
                        self.assertEqual(hint.speech.count("1行目と2行目"), 1)
                        self.assertEqual(hint.speech, hint.display)
                        self.assertLessEqual(len(hint.speech), 40)

    def test_action_keeps_its_meaning_across_personas(self):
        action_words = {"review": "見直して", "read": "声に出して読んで", "compare": "見比べて", "next_step": "一緒に考えて"}
        for action, word in action_words.items():
            for persona in ("teacher", "ikemen"):
                with self.subTest(action=action, persona=persona):
                    text = render_h2("右辺", persona, action).speech
                    self.assertIn(word, text)
                    if action == "next_step":
                        self.assertTrue(text.endswith("？"))

    def test_configuration_alone_can_change_register_without_changing_focus(self):
        config = replace(PERSONAS["ikemen"], h2_template="さて、{focus}を見直してみない？")
        with patch.dict(PERSONAS, {"ikemen": config}):
            self.assertEqual(render_h2("右辺の符号", "ikemen").speech, "さて、右辺の符号を見直してみない？")

    def test_focus_is_not_trimmed_or_interpreted_as_a_template(self):
        focus = " かっこの{内側} "
        self.assertEqual(render_h2(focus).speech, " かっこの{内側} を見直してみましょう。")

    def test_invalid_focus_and_expressions_are_rejected(self):
        for focus in ("", " ", "\t\r\n", "　", None, 123, [], {}):
            with self.subTest(focus=focus), self.assertRaises(ValueError):
                render_h2(focus)
        for action, variant in (("solve", "plain"), ("review", "invent"), (None, "plain"), ([], "plain")):
            with self.subTest(action=action, variant=variant), self.assertRaises(ValueError):
                render_h2("右辺", action=action, variant=variant)

    def test_invalid_templates_are_rejected(self):
        for template in ("", "no field", "{focus}{focus}", "{other}", "{}", "{focus", "focus}", "{focus!r}", "{focus:}", "{focus:>10}", "{focus[0]}", "{focus.__class__}", "{focus}{other}", "{{focus}}", None, 123):
            config = replace(PERSONAS["teacher"], h2_template=template)
            with self.subTest(template=template), patch.dict(PERSONAS, {"teacher": config}):
                with self.assertRaisesRegex(ValueError, "テンプレート"):
                    render_h2("右辺")

    def test_mismatched_configuration_is_rejected(self):
        with patch.dict(PERSONAS, {"teacher": PERSONAS["ikemen"]}):
            with self.assertRaisesRegex(ValueError, "人格ID"):
                get_persona("teacher")

    def test_every_persona_action_and_variant_obeys_the_final_length_limit(self):
        for persona in ("teacher", "ikemen"):
            for action in HINT_ACTIONS:
                for variant in HINT_VARIANTS:
                    with self.subTest(persona=persona, action=action, variant=variant):
                        overhead = len(render_h2("あ", persona, action, variant).speech) - 1
                        hint = render_h2("あ" * (40 - overhead), persona, action, variant)
                        self.assertEqual(len(hint.speech), 40)
                        self.assertEqual(hint.speech, hint.display)
                        with self.assertRaisesRegex(ValueError, "40文字"):
                            render_h2("あ" * (41 - overhead), persona, action, variant)

    def test_math_symbols_and_multiple_lines_are_rejected(self):
        for focus in ("x=5", "二×三", "二÷三", "二²", "二＋三", "二-三", "√二", "右辺\n左辺"):
            with self.subTest(focus=focus), self.assertRaises(ValueError):
                render_h2(focus)

    def test_end_messages_are_the_user_templates_and_fit_both_limits(self):
        expected = {
            "teacher": "今日もよく頑張りました。できるようになったことを記録で振り返ってみましょう。",
            "ikemen": "今日はここまで。よくやったじゃん。頑張った証拠、記録で確かめてみな。",
        }
        for persona, text in expected.items():
            with self.subTest(persona=persona):
                message = end_message(persona)
                self.assertEqual(message.speech, text)
                self.assertEqual(message.display, text)
                self.assertLessEqual(len(text), 40)

    def test_reference_lines_are_preserved_verbatim_without_replay(self):
        references = PERSONAS["ikemen"].references
        self.assertEqual(references.normal, EXPECTED_NORMAL)
        self.assertEqual(references.special, EXPECTED_SPECIAL)
        self.assertEqual(sum(line.count("ちょ、待てよ") for line in references.normal + references.special), 1)
        self.assertNotIn("SMAP", repr(PERSONAS["ikemen"]))
        baseline = render_h2("右辺", "ikemen")
        replacement = replace(PERSONAS["ikemen"], references=PersonaReferences(normal=("別の参考文",), special=("長い参考文。" * 20,)))
        with patch.dict(PERSONAS, {"ikemen": replacement}):
            self.assertEqual(render_h2("右辺", "ikemen"), baseline)

    def test_personas_do_not_include_removed_apology_reference(self):
        self.assertNotIn("騒動", repr(PERSONAS))

    def test_style_prompt_is_abstract_and_references_are_not_sent(self):
        self.assertEqual(PERSONAS["ikemen"].style_instruction, IKEMEN_STYLE_PROMPT)
        for line in EXPECTED_NORMAL + EXPECTED_SPECIAL:
            self.assertNotIn(line, IKEMEN_STYLE_PROMPT)
        self.assertNotIn("ちょ、待てよ", IKEMEN_STYLE_PROMPT)
        for term in ("中学生", "数学", "focus", "action", "実在人物", "模倣"):
            self.assertIn(term, IKEMEN_STYLE_PROMPT)

    def test_fallback_has_only_a_safe_bounded_persona_prefix(self):
        self.assertEqual(fallback_message("右辺を見てみて", "ikemen").speech, "一息つこう。右辺を見てみて")
        text = "あ" * 40
        self.assertEqual(fallback_message(text, "ikemen").speech, text)


if __name__ == "__main__":
    unittest.main()
