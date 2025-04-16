import logging
import pytest

from siliconcompiler.schema.utils import translate_loglevel, trim


@pytest.mark.parametrize("level,check", [
    ("debug", logging.DEBUG),
    ("info", logging.INFO),
    ("warning", logging.WARNING),
    ("error", logging.ERROR),
    ("quiet", logging.ERROR)
])
def test_translate_loglevel(level, check):
    assert translate_loglevel(level) == logging.getLevelName(check)


def test_trim_none():
    assert trim(None) == ""


def test_trim_empty():
    assert trim("") == ""
    assert trim(" ") == ""


def test_trim_docstring_no_first_line_indent():
    assert trim("""this
                has indents""") == "this\nhas indents"


def test_trim_docstring_first_line_indent():
    assert trim("""
                this
                has indents
                """) == "this\nhas indents"


def test_trim_docstring_variable_indent():
    assert trim("""
                this
                has indents
                  * this is a list
                  * this is too
                """) == "this\nhas indents\n  * this is a list\n  * this is too"


def test_trim_docstring_empty_front():
    assert trim("""

                this
                has indents
                """) == "this\nhas indents"


def test_trim_docstring_empty_last():
    assert trim("""
                this
                has indents

                """) == "this\nhas indents"
