import re
import unicodedata

MIN_LEAK_CHARS = 3
MIN_ANSWER_VALUE_CHARS = 2
SPOKEN_SYMBOLS = {"エックス": "x", "イコール": "=", "マイナス": "-"}


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
        | {value for value in values if len(value) >= MIN_ANSWER_VALUE_CHARS}
    )


def contains_leak(text: str, strings: list[str]) -> bool:
    normalized = normalize(text)
    return any(string in normalized for string in strings)
