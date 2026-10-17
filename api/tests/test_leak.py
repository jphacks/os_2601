import pytest

from app.leak import contains_leak, leak_strings, normalize
from app.reading import to_reading


@pytest.mark.parametrize(
    ("raw", "normalized"),
    [
        ("x = −5", "x=-5"),
        ("ｘ＝５", "x=5"),
        ("x²＋1", "x^2+1"),
        ("3 × 4", "3*4"),
        ("マイナス 5", "-5"),
        ("エックス イコール 5", "x=5"),
        ("3エックス プラス 6", "3x+6"),
        ("2 かける 3", "2*3"),
    ],
)
def test_normalize(raw: str, normalized: str) -> None:
    assert normalize(raw) == normalized


def test_leak_strings_cover_the_answer_its_value_and_key_values() -> None:
    assert leak_strings("x = -15", ["-2x = 30", "x/3"]) == sorted({"x=-15", "-15", "-2x=30", "x/3"})


def test_short_answer_values_are_kept_and_short_key_values_are_not() -> None:
    assert leak_strings("x = -5", ["2x"]) == ["-5", "x=-5"]
    assert leak_strings("x = 5", []) == ["5", "x=5"]


def test_each_part_of_a_multi_part_answer_is_checked() -> None:
    assert leak_strings("x = 2, y = 3", []) == ["2", "3", "x=2", "y=3"]


def test_single_digit_answer_is_caught_only_in_an_answering_phrase() -> None:
    strings = leak_strings("x = 5", [])
    assert contains_leak("答えは 5 だよ", strings)
    assert contains_leak("5 になるよ", strings)
    assert contains_leak("エックス イコール 5", strings)
    assert not contains_leak("2行目の 5 を見てみて", strings)
    assert not contains_leak("15 を右辺に移してみて", strings)


def test_values_the_learner_already_wrote_are_not_guarded() -> None:
    assert leak_strings("x = -5", ["-2x = 10", "2x - 4x = 3 + 7"], ["2x-7=4x+3", "-2x = 10"]) == ["-5", "2x-4x=3+7", "x=-5"]


def test_contains_leak_matches_after_normalization() -> None:
    strings = leak_strings("x = -5", [])
    assert contains_leak("答えは x = −5 だね", strings)
    assert contains_leak("マイナス 5 になるよ", strings)
    assert contains_leak("エックスイコールマイナス5", strings)
    assert not contains_leak("右辺に移したときの符号を見てみて", strings)


@pytest.mark.parametrize(
    ("raw", "reading"),
    [
        ("2x = -4", "2エックス イコール マイナス 4"),
        ("三行目の x + 5", "3行目の エックス プラス 5"),
        ("ニ行目の４", "2行目の4"),
        ("3 × 4 を計算して", "3 かける 4 を計算して"),
        ("エックスの係数", "エックスの係数"),
        ("box を見て", "box を見て"),
    ],
)
def test_to_reading(raw: str, reading: str) -> None:
    assert to_reading(raw) == reading
