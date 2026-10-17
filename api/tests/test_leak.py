import pytest

from app.leak import contains_leak, leak_strings, normalize


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


def test_short_answer_values_are_kept_but_single_digits_and_short_key_values_are_not() -> None:
    assert leak_strings("x = -5", ["2x"]) == ["-5", "x=-5"]
    assert leak_strings("x = 5", []) == ["x=5"]


def test_each_part_of_a_multi_part_answer_is_checked() -> None:
    assert leak_strings("x = 2, y = 3", []) == ["x=2", "y=3"]


def test_contains_leak_matches_after_normalization() -> None:
    strings = leak_strings("x = -5", [])
    assert contains_leak("答えは x = −5 だね", strings)
    assert contains_leak("マイナス 5 になるよ", strings)
    assert contains_leak("エックスイコールマイナス5", strings)
    assert not contains_leak("右辺に移したときの符号を見てみて", strings)
