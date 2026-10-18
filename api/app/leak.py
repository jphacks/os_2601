import re
import unicodedata

MIN_LEAK_CHARS = 3
MIN_ANSWER_VALUE_CHARS = 2
SHORT_ANSWER_PHRASES = (
    r"(答え|こたえ)[はがを]?{v}(?!\d)",
    r"(?<![\d.])={v}(?!\d)",
    r"(?<![\d.]){v}(だよ|だね|です|になる|になります|かな|にして|にする|が答え|で合って)",
)
READINGS = {"=": "イコール", "*": "かける", "÷": "わる", "-": "マイナス", "+": "プラス", "x": "エックス"}
SPOKEN_SYMBOLS = {reading: symbol for symbol, reading in READINGS.items()}


def normalize(text: str) -> str:
    text = text.replace("²", "^2").replace("³", "^3")
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"\s+", "", text)
    for spoken, symbol in SPOKEN_SYMBOLS.items():
        text = text.replace(spoken, symbol)
    text = text.replace("×", "*").replace("✕", "*")
    text = re.sub(r"[−ー](?=\d)", "-", text)
    return text.replace("＝", "=")


def leak_strings(final_answer: str, key_values: list[str]) -> list[str]:
    answers = [part for part in re.split(r"[,、;]", normalize(final_answer)) if part]
    values = {answer.rsplit("=", 1)[-1] for answer in answers}
    candidates = {*answers, *(normalize(key_value) for key_value in key_values)}
    return sorted(
        {candidate for candidate in candidates if len(candidate) >= MIN_LEAK_CHARS}
        | {value for value in values if len(value) >= MIN_ANSWER_VALUE_CHARS or value.isdigit()}
    )


def without_written(strings: list[str], written_lines: list[str]) -> list[str]:
    written = {part for line in written_lines for part in (normalize(line), normalize(line).rsplit("=", 1)[-1])}
    return [string for string in strings if string not in written]


def _mentions(normalized: str, string: str) -> bool:
    if len(string) == 1:
        return any(re.search(phrase.format(v=string), normalized) for phrase in SHORT_ANSWER_PHRASES)
    return string in normalized


def contains_leak(text: str, strings: list[str]) -> bool:
    normalized = normalize(text)
    return any(_mentions(normalized, string) for string in strings)
