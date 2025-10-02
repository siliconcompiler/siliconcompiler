import logging
import pytest

from siliconcompiler.schema.utils import trim


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
