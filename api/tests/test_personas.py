import unittest
from dataclasses import replace
from unittest.mock import patch

from app.personas import PERSONAS, render_h2


class RenderH2Tests(unittest.TestCase):
    def test_three_personas_render_speech_and_display(self):
        expected = {
            "teacher": "移項した項の符号を、見直してみましょう。",
            "friend": "移項した項の符号を、見直してみよう。",
            "ikemen": "焦りは脇役さ。移項した項の符号を見直してみよう。",
        }
        self.assertEqual(set(PERSONAS), set(expected))
        for persona, text in expected.items():
            with self.subTest(persona=persona):
                hint = render_h2("移項した項の符号", persona)
                self.assertEqual(hint.speech, text)
                self.assertEqual(hint.display, hint.speech)
                self.assertLessEqual(len(hint.speech), 40)
                self.assertLessEqual(len(hint.display), 60)

    def test_default_persona_is_teacher(self):
        self.assertEqual(render_h2("移項の符号"), render_h2("移項の符号", "teacher"))

    def test_unsupported_persona_ids_are_rejected(self):
        for persona in ("sister", "normal"):
            with self.subTest(persona=persona), self.assertRaisesRegex(ValueError, "人格"):
                render_h2("移項の符号", persona)

    def test_configuration_alone_changes_tone_and_humor(self):
        focus = "移項の符号"
        original = render_h2(focus, "ikemen")
        customized = replace(
            PERSONAS["ikemen"],
            display_name="余裕のある先輩",
            description="舞台の比喩を添える先輩。",
            h2_template="さて、{focus}にスポットライトを当ててみよう。",
            style_instruction="穏やかな提案に短い舞台の比喩を添える。",
        )
        with patch.dict(PERSONAS, {"ikemen": customized}):
            hint = render_h2(focus, "ikemen")
            self.assertEqual(hint.speech, "さて、移項の符号にスポットライトを当ててみよう。")
            self.assertEqual(hint.display, hint.speech)
            self.assertNotEqual(hint, original)
        self.assertEqual(render_h2(focus, "ikemen"), original)

    def test_focus_is_preserved_for_every_persona(self):
        for focus in ("移項した項の符号", "かっこの中の二つ目の項へのかけ方", "両辺を割ったときの符号"):
            for persona in ("teacher", "friend", "ikemen"):
                with self.subTest(focus=focus, persona=persona):
                    hint = render_h2(focus, persona)
                    self.assertEqual(hint.speech.count(focus), 1)
                    self.assertEqual(hint.display, hint.speech)
                    self.assertLessEqual(len(hint.speech), 40)

    def test_focus_is_not_stripped_or_interpreted_as_a_template(self):
        focus = " かっこの{内側} "
        self.assertEqual(render_h2(focus).speech, " かっこの{内側} を、見直してみましょう。")

    def test_empty_or_non_string_focus_is_rejected(self):
        for focus in ("", " ", "\t\r\n", "　", None, 123, [], {}):
            with self.subTest(focus=focus), self.assertRaisesRegex(ValueError, "focus"):
                render_h2(focus)

    def test_unknown_or_non_string_persona_is_rejected(self):
        for persona in ("", "unknown", "Ikemen", " ikemen ", None, 123, [], {}):
            with self.subTest(persona=persona), self.assertRaisesRegex(ValueError, "人格"):
                render_h2("移項の符号", persona)

    def test_invalid_templates_are_rejected(self):
        templates = (
            "", "見直してみよう。", "{focus}{focus}", "{other}", "{}", "{focus", "focus}",
            "{focus!r}", "{focus!s}", "{focus:}", "{focus:>10}", "{focus:.2}",
            "{focus[0]}", "{focus.__class__}", "{focus}{other}", "{focus:{width}}",
            "{{focus}}", "{{{focus}}}", None, 123,
        )
        for template in templates:
            config = replace(PERSONAS["ikemen"], h2_template=template)
            with self.subTest(template=template), patch.dict(PERSONAS, {"ikemen": config}):
                with self.assertRaisesRegex(ValueError, "テンプレート"):
                    render_h2("移項の符号", "ikemen")

    def test_mismatched_persona_configuration_is_rejected(self):
        config = replace(PERSONAS["ikemen"], persona_id="other")
        with patch.dict(PERSONAS, {"ikemen": config}):
            with self.assertRaisesRegex(ValueError, "人格ID"):
                render_h2("移項の符号", "ikemen")

    def test_forty_characters_are_accepted_and_longer_text_is_rejected(self):
        for persona in ("teacher", "friend", "ikemen"):
            template_chars = len(PERSONAS[persona].h2_template.replace("{focus}", ""))
            with self.subTest(persona=persona, length=40):
                focus = "あ" * (40 - template_chars)
                hint = render_h2(focus, persona)
                self.assertEqual(len(hint.speech), 40)
                self.assertIn(focus, hint.speech)
                self.assertEqual(hint.display, hint.speech)
            for length in (41, 60, 61):
                with self.subTest(persona=persona, length=length), self.assertRaisesRegex(ValueError, "40文字"):
                    render_h2("あ" * (length - template_chars), persona)

    def test_template_text_is_included_in_the_length_limit(self):
        config = replace(PERSONAS["ikemen"], h2_template="{focus}を見てみよう。")
        with patch.dict(PERSONAS, {"ikemen": config}):
            with self.assertRaisesRegex(ValueError, "40文字"):
                render_h2("あ" * 40, "ikemen")

    def test_math_symbols_in_focus_or_template_are_rejected(self):
        for focus in ("x=5", "二×三", "二÷三", "二²", "二＋三", "二−三"):
            with self.subTest(focus=focus), self.assertRaisesRegex(ValueError, "数式記号"):
                render_h2(focus)
        config = replace(PERSONAS["ikemen"], h2_template="{focus}＝答え")
        with patch.dict(PERSONAS, {"ikemen": config}):
            with self.assertRaisesRegex(ValueError, "数式記号"):
                render_h2("移項の符号", "ikemen")


if __name__ == "__main__":
    unittest.main()
