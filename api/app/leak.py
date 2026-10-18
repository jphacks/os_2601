import re
import unicodedata
from fractions import Fraction

MIN_LEAK_CHARS = 3
MIN_ANSWER_VALUE_CHARS = 2
SHORT_ANSWER_PHRASES = (
    r"(答え|こたえ)[はがを]?[、,]?{v}(?![\d.])",
    r"(?<![\d.])={v}(?![\d.])",
    r"(?<![\d.]){v}(だよ|だね|です|になる|になります|かな|にして|にする|が答え|で合って|が正しい|が正解)",
    r"(?<![\d.]){v}(を|と)(書|かい|入れ|いれ|置|おい)",
    r"(?<![\d.a-z])[xy](は|が)?{v}(?![\d.])",
    r"(?<![\d.]){v}[。.!！]*$",
)
KANJI_DIGITS = {"〇": "0", "一": "1", "二": "2", "三": "3", "四": "4", "五": "5", "六": "6", "七": "7", "八": "8", "九": "9", "十": "10"}
READINGS = {"=": "イコール", "*": "かける", "÷": "わる", "-": "マイナス", "+": "プラス", "x": "エックス"}
SPOKEN_SYMBOLS = {reading: symbol for symbol, reading in READINGS.items()}


def _fraction_words(text: str) -> str:
    def to_digits(word: str) -> str:
        return "".join(KANJI_DIGITS.get(char, char) for char in word)

    return re.sub(
        r"([\d〇一二三四五六七八九十]+)分の([\d〇一二三四五六七八九十]+)",
        lambda match: f"{to_digits(match.group(2))}/{to_digits(match.group(1))}",
        text,
    )


def _same_value_spellings(value: str) -> set[str]:
    if re.fullmatch(r"-?\d+/\d+", value):
        fraction = Fraction(value)
        decimal = str(fraction.numerator / fraction.denominator)
        return {decimal} if len(decimal) <= 6 else set()
    if re.fullmatch(r"-?\d*\.\d+", value):
        fraction = Fraction(value).limit_denominator(100)
        return {f"{fraction.numerator}/{fraction.denominator}"} if fraction.denominator > 1 else set()
    return set()


def normalize(text: str) -> str:
    text = text.replace("²", "^2").replace("³", "^3")
    text = unicodedata.normalize("NFKC", text)
    text = _fraction_words(text)
    text = re.sub(r"\s+", "", text)
    for spoken, symbol in SPOKEN_SYMBOLS.items():
        text = text.replace(spoken, symbol)
    text = re.sub(r"の(\d)乗", r"^\1", text)
    text = text.replace("×", "*").replace("✕", "*")
    text = re.sub(r"[−ー](?=\d)", "-", text)
    return text.replace("＝", "=")


def leak_strings(final_answer: str, key_values: list[str]) -> list[str]:
    answers = [part for part in re.split(r"[,、;]", normalize(final_answer)) if part]
    values = {answer.rsplit("=", 1)[-1] for answer in answers}
    values |= {spelling for value in list(values) for spelling in _same_value_spellings(value)}
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
