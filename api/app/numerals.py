KANJI_DIGITS = {"〇": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}


def _digit(char: str) -> int:
    return int(char) if char.isdigit() else KANJI_DIGITS[char]


def kanji_number(word: str) -> str:
    if "十" not in word:
        return "".join(str(_digit(char)) for char in word)
    tens, ones = word.split("十", 1)
    if len(tens) > 1 or len(ones) > 1 or "十" in ones:
        return word
    return str((_digit(tens) if tens else 1) * 10 + (_digit(ones) if ones else 0))
