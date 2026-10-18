import re
import unicodedata
from fractions import Fraction

from app.numerals import kanji_number

MIN_LEAK_CHARS = 3
MIN_ANSWER_VALUE_CHARS = 2
MAX_DECIMAL_DIGITS = 6
MAX_VALUE_CHARS = 30
ENDS_A_CLAIM = r"(?=$|[、。,.!！?？]|だ|です|かな|になる)"
SHORT_ANSWER_PHRASES = (
    r"(答え|こたえ)[はがを]?[、,]?{v}(?![\d.])",
    r"(?<![\d.])={v}(?![\d.])",
    r"(?<![\d.]){v}(だよ|だね|です|になる|になります|かな|にして|にする|が答え|で合って|が正しい|が正解)",
    r"(?<![\d.]){v}を(書いて|書く|書け|かいて|入れて|入れる|いれて|置いて|おいて)",
    r"(?<![\d.a-z])[xy](は|が){v}" + ENDS_A_CLAIM,
)
NUMBER = re.compile(r"-?[\d./]+")
KANJI_NUMBER = r"[\d〇一二三四五六七八九十]+"
READINGS = {"=": "イコール", "*": "かける", "÷": "わる", "-": "マイナス", "+": "プラス", "x": "エックス"}
SPOKEN_SYMBOLS = {reading: symbol for symbol, reading in READINGS.items()}


def _fraction_words(text: str) -> str:
    return re.sub(
        rf"({KANJI_NUMBER})分の({KANJI_NUMBER})",
        lambda match: f"{kanji_number(match.group(2))}/{kanji_number(match.group(1))}",
        text,
    )


def _same_value_spellings(value: str) -> set[str]:
    if len(value) > MAX_VALUE_CHARS:
        return set()
    if re.fullmatch(r"-?\d+/\d+", value):
        numerator, denominator = (int(part) for part in value.split("/"))
        if denominator == 0:
            return set()
        decimal = str(numerator / denominator)
        return {decimal} if len(decimal.lstrip("-")) <= MAX_DECIMAL_DIGITS else set()
    if re.fullmatch(r"-?\d*\.\d+", value):
        fraction = Fraction(value).limit_denominator(100)
        return {f"{fraction.numerator}/{fraction.denominator}"} if fraction.denominator > 1 else set()
    return set()


def normalize(text: str) -> str:
    text = text.replace("²", "^2").replace("³", "^3")
    text = unicodedata.normalize("NFKC", text).replace("⁄", "/")
    text = re.sub(r"\s+", "", text)
    text = _fraction_words(text)
    text = re.sub(r"[〇一二三四五六七八九十]+", lambda match: kanji_number(match.group(0)), text)
    for spoken, symbol in SPOKEN_SYMBOLS.items():
        text = text.replace(spoken, symbol)
    text = re.sub(r"の(\d)乗", r"^\1", text)
    text = text.replace("×", "*").replace("✕", "*")
    text = re.sub(r"[−ー](?=\d)", "-", text)
    return text.replace("＝", "=")


def same_problem(read: str | None, known: str | None) -> bool:
    return bool(read and known) and normalize(read) == normalize(known)


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
    if NUMBER.fullmatch(string):
        return re.search(rf"(?<![\d./]){re.escape(string)}(?![\d./a-z])", normalized) is not None
    return string in normalized


def states_an_answer(text: str) -> bool:
    normalized = normalize(text)
    return any(re.search(phrase.format(v=r"-?\d[\d./]*"), normalized) for phrase in SHORT_ANSWER_PHRASES)


def contains_leak(text: str, strings: list[str]) -> bool:
    normalized = normalize(text)
    return any(_mentions(normalized, string) for string in strings)
