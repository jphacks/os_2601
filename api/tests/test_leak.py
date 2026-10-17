import pytest

from app.leak import contains_leak, leak_strings, normalize


@pytest.mark.parametrize(
    ("raw", "normalized"),
    [
        ("x = −5", "x=-5"),
        ("ｘ＝５", "x=5"),
        ("x²＋1", "x^2+1"),
        ("3 × 4", "3*4"),
        ("マイナス 5", "マイナス5"),
    ],
)
def test_normalize(raw: str, normalized: str) -> None:
    assert normalize(raw) == normalized


def test_leak_strings_cover_the_answer_its_value_and_key_values() -> None:
    assert leak_strings("x = -15", ["-2x = 30", "x/3"]) == sorted({"x=-15", "-15", "マイナス15", "-2x=30", "x/3"})


def test_leak_strings_drop_strings_shorter_than_three_chars() -> None:
    assert leak_strings("x = 5", ["2x"]) == ["x=5"]


def test_contains_leak_matches_after_normalization() -> None:
    strings = leak_strings("x = -5", [])
    assert contains_leak("答えは x = −5 だね", strings)
    assert contains_leak("マイナス 5 になるよ", strings)
    assert not contains_leak("右辺に移したときの符号を見てみて", strings)
