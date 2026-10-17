import re
import unicodedata

from app.leak import READINGS

KANJI_DIGITS = {"〇": "0", "一": "1", "二": "2", "ニ": "2", "三": "3", "四": "4", "五": "5", "六": "6", "七": "7", "八": "8", "九": "9"}
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
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"([〇一二ニ三四五六七八九十])(?=行目)", lambda match: KANJI_DIGITS[match.group(1)], text)
    for pattern, reading in SYMBOL_READINGS:
        text = re.sub(pattern, reading, text)
    return re.sub(r"\s+", " ", text).strip()
