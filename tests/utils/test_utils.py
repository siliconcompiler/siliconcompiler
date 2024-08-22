import pytest
from siliconcompiler.utils import truncate_text


@pytest.mark.parametrize("text", (
    "testing-without-numbers", "testing-with-numbers0", "testing-with-numbers00"))
@pytest.mark.parametrize("length", (8, 10, 15))
def test_truncate_text_lengths(text, length):
    expect = min(len(text), length)

    assert len(truncate_text(text, length)) == expect


def test_truncate_text():
    text = "test"
    assert truncate_text(text, 8) == "test"
    assert truncate_text(text, 10) == "test"
    assert truncate_text(text, 15) == "test"

    text = "testing-without-numbers"
    assert truncate_text(text, 8) == "testi..."
    assert truncate_text(text, 10) == "testing..."
    assert truncate_text(text, 15) == "testing-with..."

    text = "testing-without-numbers0"
    assert truncate_text(text, 8) == "test...0"
    assert truncate_text(text, 10) == "testin...0"
    assert truncate_text(text, 15) == "testing-wit...0"

    text = "testing-without-numbers90"
    assert truncate_text(text, 8) == "tes...90"
    assert truncate_text(text, 10) == "testi...90"
    assert truncate_text(text, 15) == "testing-wi...90"

    text = "testing-without-numbers9123"
    assert truncate_text(text, 8) == "tes...23"
    assert truncate_text(text, 10) == "testi...23"
    assert truncate_text(text, 15) == "testing-wi...23"
