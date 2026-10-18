import re
import unicodedata

from app.leak import READINGS
from app.numerals import kanji_number

OPERAND = r"(?=[\dx(]|エックス|かっこ)"
SYMBOL_READINGS = [
    (r"\s*=\s*", f" {READINGS['=']} "),
    (r"\s*[×*]\s*", f" {READINGS['*']} "),
    (r"\s*÷\s*", f" {READINGS['÷']} "),
    (r"\s*[−\-]\s*" + OPERAND, f" {READINGS['-']} "),
    (r"\s*\+\s*" + OPERAND, f" {READINGS['+']} "),
    (r"(?<![A-Za-z])x(?![A-Za-z])", READINGS["x"]),
]


def to_reading(text: str) -> str:
    text = text.replace("²", "の2乗").replace("³", "の3乗")
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"([〇一二ニ三四五六七八九十]+)(?=行目)", lambda match: kanji_number(match.group(1).replace("ニ", "二")), text)
    for pattern, reading in SYMBOL_READINGS:
        text = re.sub(pattern, reading, text)
    return re.sub(r"\s+", " ", text).strip()
