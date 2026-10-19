import re

CHECK_WORDS = re.compile(r"(?<![しけちせりみび])(合って|あって)(る|ます|いる|います)|できてる")
CHECK_QUESTION = re.compile(
    r"(正解|正しい)(ですか|でしょう|だよね|よね|かな|か?[？?]|か?$|か(どうか)?(わからない|わかんない|分からない|教えて|おしえて))"
)
ASKS_WHAT = re.compile(r"何が|何を|なにが|なにを|どこ|どうすれば|どうやって|どうしたら")
HELP_WORDS = (
    "わからない",
    "わかんない",
    "分からない",
    "分かんない",
    "わかりません",
    "分かりません",
    "ヒント",
    "どうすれば",
    "何をすれば",
    "なにをすれば",
    "教えて",
    "おしえて",
)


def asks_for_help(utterance: str) -> bool:
    return any(word in utterance for word in HELP_WORDS)


def asks_if_correct(utterance: str) -> bool:
    if CHECK_WORDS.search(utterance):
        return True
    return CHECK_QUESTION.search(utterance.strip().rstrip("。.")) is not None and ASKS_WHAT.search(utterance) is None
