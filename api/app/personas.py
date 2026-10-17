"""H2専用の人格設定と、外部サービスを使わない文章の組み立て。

カスタマイズはPERSONASの各設定だけを編集する。
テンプレートは{focus}を1回だけ含め、前後には口調や短いユーモアだけを
加える。別の着眼点、計算指示、答え、正誤の断定、褒め言葉は加えない。
生徒の名前、実在人物の模倣、恋愛的・性的な表現も使わない。

focusは検査済みの着眼点を受け取る。このモジュールは正答を持たないため、
答え漏れの意味的な判定はしない。将来APIに接続するときは、完成した文を
docs/05の答え漏れ検査に通す。H1と既存APIはここでは扱わない。
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class PersonaConfig:
    persona_id: str
    display_name: str
    description: str
    h2_template: str
    style_instruction: str


# 人格の設定はここに集約する。性格・口調の作り込みはチームで後から行う。
# style_instructionは将来のAI生成用の設定で、現在は送信・実行しない。
PERSONAS: dict[str, PersonaConfig] = {
    "teacher": PersonaConfig(
        persona_id="teacher",
        display_name="教師",
        description="落ち着いて考える手助けをする教師。",
        h2_template="{focus}を、見直してみましょう。",
        style_instruction="中学生に穏やかな丁寧語で、見直す場所を短く提案する。",
    ),
    "friend": PersonaConfig(
        persona_id="friend",
        display_name="友達",
        description="対等な立場で一緒に考える友達。",
        h2_template="{focus}を、見直してみよう。",
        style_instruction="中学生に自然な会話調で、見直す場所を短く提案する。",
    ),
    "sister": PersonaConfig(
        persona_id="sister",
        display_name="お姉さん",
        description="急がせずに考える手助けをする、頼れるお姉さん。",
        h2_template="{focus}を、見直してみてね。",
        style_instruction="中学生を幼児扱いせず、柔らかい提案形で見直す場所を示す。",
    ),
}


@dataclass(frozen=True)
class HintText:
    speech: str
    display: str


SPEECH_MAX_CHARS = 40
DISPLAY_MAX_CHARS = 60
_FOCUS_FIELD = "{focus}"
_MATH_SYMBOLS = frozenset("×✕÷²³=＝+＋-−－*/／＊^＾<>＜＞≤≥≠√±%％")


def _validate_template(template: str) -> tuple[str, str]:
    """単一の{focus}以外の置換・書式指定・波括弧は受け付けない。"""
    if not isinstance(template, str) or template.count(_FOCUS_FIELD) != 1:
        raise ValueError("H2テンプレートには{focus}が1回だけ必要です")
    before, after = template.split(_FOCUS_FIELD)
    if any(char in before + after for char in "{}"):
        raise ValueError("H2テンプレートは{focus}以外の波括弧を使えません")
    return before, after


def render_h2(focus: str, persona: str = "teacher") -> HintText:
    """着眼点を変更せず1回挿入し、同じ文をspeechとdisplayに返す。

    空の着眼点、不正な人格・テンプレート、数式記号、文字数超過はValueError。
    focusはstrip・正規化・再解釈・切り詰めを行わない。
    """
    if not isinstance(focus, str) or not focus.strip():
        raise ValueError("focusには空でない文字列が必要です")
    if not isinstance(persona, str) or persona not in PERSONAS:
        raise ValueError("未定義の人格です")

    config = PERSONAS[persona]
    if not isinstance(config, PersonaConfig) or config.persona_id != persona:
        raise ValueError("人格IDと設定が一致しません")
    before, after = _validate_template(config.h2_template)
    text = before + focus + after

    if any(char in _MATH_SYMBOLS for char in text):
        raise ValueError("speechには数式記号を使わず、言葉で表してください")
    if len(text) > SPEECH_MAX_CHARS or len(text) > DISPLAY_MAX_CHARS:
        raise ValueError("speechは40文字以内、displayは60文字以内にしてください")
    return HintText(speech=text, display=text)
