import re
import unicodedata

MIN_LEAK_CHARS = 3


def normalize(text: str) -> str:
    text = text.replace("²", "^2").replace("³", "^3")
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"\s+", "", text)
    text = text.replace("×", "*").replace("✕", "*")
    text = re.sub(r"[−ー](?=\d)", "-", text)
    return text.replace("＝", "=")


def leak_strings(final_answer: str, key_values: list[str]) -> list[str]:
    answer = normalize(final_answer)
    value = answer.rsplit("=", 1)[-1]
    candidates = {answer, value, *(normalize(key_value) for key_value in key_values)}
    if value.startswith("-"):
        candidates.add(f"マイナス{value[1:]}")
    return sorted(candidate for candidate in candidates if len(candidate) >= MIN_LEAK_CHARS)


def contains_leak(text: str, strings: list[str]) -> bool:
    normalized = normalize(text)
    return any(string in normalized for string in strings)
