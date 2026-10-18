"""Persona settings and bounded expressions for the same mathematical focus.

Gemini chooses a focus, an action and a small expression variant once. Only the
templates below express those fields: a persona cannot add another calculation
or change the selected target. Reference lines are archival material, never a
playback list or an AI prompt. Completed hints still need the server leak check.
"""

from dataclasses import dataclass, field
from typing import Literal
import unicodedata

PersonaId = Literal["teacher", "ikemen"]
HINT_ACTIONS = ("review", "read", "compare", "next_step")
HINT_VARIANTS = ("plain", "warm", "playful")
SPEECH_MAX_CHARS = 40
DISPLAY_MAX_CHARS = 60


@dataclass(frozen=True)
class PersonaReferences:
    normal: tuple[str, ...] = ()
    special: tuple[str, ...] = ()


@dataclass(frozen=True)
class PersonaConfig:
    persona_id: PersonaId
    display_name: str
    description: str
    h2_template: str
    style_instruction: str
    end_message: str
    fallback_prefix: str = ""
    action_templates: dict[str, str] = field(default_factory=dict)
    variant_prefixes: dict[str, str] = field(default_factory=dict)
    references: PersonaReferences = PersonaReferences()


@dataclass(frozen=True)
class HintText:
    speech: str
    display: str


IKEMEN_STYLE_PROMPT = (
    "中学生の数学学習を支える独自の架空の先輩。落ち着いたタメ口と余裕に、"
    "少しキザな言い回しと短いドラマチックなユーモアを添える。"
    "数学的な分析、focusとactionは人格と切り離して先に決め、人格で変更しない。"
    "口調以外の情報を変えず、答え・決定的な途中式・計算結果・別の指摘を加えない。"
    "生徒の正誤を断定せず、ヒントでは褒めない。からかい・煽り・命令を避ける。"
    "特定の決めぜりふを繰り返さず、参考セリフを朗読・ランダム再生しない。"
    "実在人物を名乗らず、固有の出来事や人物の口調・声を模倣しない。"
    "名前や愛称を呼ばず、恋愛的・性的・独占的な表現は使わない。"
)


# Customize voice in one place. Templates may change register and humor only;
# keep the action's meaning and exactly one {focus}. References remain inactive.
PERSONAS: dict[str, PersonaConfig] = {
    "teacher": PersonaConfig(
        persona_id="teacher",
        display_name="家庭教師",
        description="落ち着いた丁寧語で、自分で考える手助けをする家庭教師。",
        h2_template="{focus}を見直してみましょう。",
        style_instruction=(
            "中学生の数学学習を穏やかな丁寧語で支援する家庭教師。"
            "数学的な分析、focusとactionは人格と切り離して先に決め、人格で変更しない。"
            "口調以外の情報を変えず、答え・決定的な途中式・別の指摘を加えず、"
            "提案形で促す。正誤を断定せずヒントでは褒めず、名前を呼ばない。"
        ),
        end_message="今日もよく頑張りました。できるようになったことを記録で振り返ってみましょう。",
        action_templates={
            "read": "{focus}を声に出して読んでみましょう。",
            "compare": "{focus}を見比べてみましょう。",
            "next_step": "{focus}を、一緒に考えてみませんか？",
        },
        variant_prefixes={"plain": "", "warm": "焦らず、", "playful": "さて、"},
    ),
    "ikemen": PersonaConfig(
        persona_id="ikemen",
        display_name="イケメン",
        description="落ち着いたタメ口に、少しキザなユーモアを添える独自の先輩。",
        h2_template="{focus}を見直してみよう。",
        style_instruction=IKEMEN_STYLE_PROMPT,
        end_message="今日はここまで。よくやったじゃん。頑張った証拠、記録で確かめてみな。",
        fallback_prefix="一息つこう。",
        action_templates={
            "read": "{focus}を声に出して読んでみよう。",
            "compare": "{focus}を見比べてみよう。",
            "next_step": "{focus}を、一緒に考えてみない？",
        },
        variant_prefixes={"plain": "", "warm": "一息つこう。", "playful": "ここはスマートに。"},
        references=PersonaReferences(
            normal=(
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
            ),
            special=(
                "「今回は先日の騒動でみなさんにつらい思いをさせてしまって、本当に申し訳ない気持ちでいっぱいです……。って、おっと、待った！ 今は数学の話だろ？」",
                "「あれこれ言うつもりはないさ。自分で気づいたことって、意外と忘れないもんだろ？ ヒントは出す。あとは自分で考えてみな。」",
                "「点数ばっか気にすんなよ。答案に書いてある自分の名前、胸張って言えるくらい頑張れたなら、それって結構カッコいいことだろ？」",
                "「点数より大事なもんもあるだろ？ ……おっと、待った！ 名前書き忘れて0点とか、そういう話じゃないからな？」",
            ),
        ),
    ),
}


def get_persona(persona: str = "teacher") -> PersonaConfig:
    if not isinstance(persona, str) or persona not in PERSONAS:
        raise ValueError("未定義の人格です")
    config = PERSONAS[persona]
    if not isinstance(config, PersonaConfig) or config.persona_id != persona:
        raise ValueError("人格IDと設定が一致しません")
    return config


def persona_options() -> list[dict[str, str]]:
    return [
        {"id": config.persona_id, "display_name": config.display_name, "end_message": end_message(config.persona_id).display}
        for config in PERSONAS.values()
    ]


def _text(text: str) -> HintText:
    if not text.strip() or len(text) > SPEECH_MAX_CHARS or len(text) > DISPLAY_MAX_CHARS:
        raise ValueError("speechは40文字以内、displayは60文字以内にしてください")
    return HintText(speech=text, display=text)


def end_message(persona: str = "teacher") -> HintText:
    return _text(get_persona(persona).end_message)


def fallback_message(text: str, persona: str = "teacher") -> HintText:
    prefix = get_persona(persona).fallback_prefix
    return _text(prefix + text if len(prefix + text) <= SPEECH_MAX_CHARS else text)


def render_h2(focus: str, persona: str = "teacher", action: str = "review", variant: str = "plain") -> HintText:
    """Keep focus verbatim; only bounded register and non-mathematical prefixes vary."""
    if not isinstance(focus, str) or not focus.strip():
        raise ValueError("focusには空でない文字列が必要です")
    config = get_persona(persona)
    if action not in HINT_ACTIONS or variant not in HINT_VARIANTS:
        raise ValueError("未定義のヒント操作または表現です")
    template = config.h2_template if action == "review" else config.action_templates.get(action)
    prefix = config.variant_prefixes.get(variant)
    if not isinstance(template, str) or template.count("{focus}") != 1:
        raise ValueError("H2テンプレートには{focus}が1回だけ必要です")
    before, after = template.split("{focus}")
    if not isinstance(prefix, str) or any(char in prefix + before + after for char in "{}"):
        raise ValueError("H2テンプレートは{focus}以外の波括弧を使えません")
    text = prefix + before + focus + after
    if any(unicodedata.category(char) == "Sm" or char in "×✕÷²³-−－*/／＊^＾%％" for char in text):
        raise ValueError("speechには数式記号を使わず、言葉で表してください")
    if any(char in text for char in "\r\n"):
        raise ValueError("ヒントは1行の文章にしてください")
    return _text(text)
