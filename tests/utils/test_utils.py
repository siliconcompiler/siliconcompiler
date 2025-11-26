import logging
import pytest

import os.path

from unittest.mock import patch

from siliconcompiler.utils import \
    truncate_text, safecompare, get_cores, grep, \
    get_plugins, \
    default_sc_dir, default_credentials_file, default_cache_dir, \
    default_email_credentials_file, default_sc_path


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

    assert truncate_text("test", 1) == "test"
    assert truncate_text("testing-without-numbers", 1) == "te..."
    assert truncate_text("testing-without-numbers0", 1) == "t...0"
    assert truncate_text("testing-without-numbers9123", 1) == "...23"


@pytest.mark.parametrize("a,op,b,expect", [
    (1, ">", 2, False),
    (1, ">", 1, False),
    (2, ">", 1, True),
    (1, ">=", 2, False),
    (1, ">=", 1, True),
    (2, ">=", 1, True),
    (1, "<", 2, True),
    (1, "<", 1, False),
    (2, "<", 1, False),
    (1, "<=", 2, True),
    (1, "<=", 1, True),
    (2, "<=", 1, False),
    (1, "==", 2, False),
    (1, "==", 1, True),
    (2, "==", 1, False),
    (1, "!=", 2, True),
    (1, "!=", 1, False),
    (2, "!=", 1, True)
])
def test_safecompare(a, op, b, expect):
    assert safecompare(a, op, b) is expect


def test_safecompare_invalid_operator():
    with pytest.raises(ValueError, match="^Illegal comparison operation !$"):
        safecompare(1, "!", 2)


def test_get_cores_logical(monkeypatch):
    import psutil

    def cpu_count(logical):
        assert logical
        return 2

    monkeypatch.setattr(psutil, 'cpu_count', cpu_count)
    assert get_cores() == 2


def test_get_cores_physical(monkeypatch):
    import psutil

    def cpu_count(logical):
        assert not logical
        return 2

    monkeypatch.setattr(psutil, 'cpu_count', cpu_count)
    assert get_cores(physical=True) == 2


def test_get_cores_use_os(monkeypatch):
    import psutil
    import os

    def psutil_cpu_count(logical):
        return None

    def os_cpu_count():
        return 6

    monkeypatch.setattr(psutil, 'cpu_count', psutil_cpu_count)
    monkeypatch.setattr(os, 'cpu_count', os_cpu_count)
    assert get_cores() == 6
    assert get_cores(physical=True) == 3


def test_get_cores_use_os_one_core(monkeypatch):
    import psutil
    import os

    def psutil_cpu_count(logical):
        return None

    def os_cpu_count():
        return 1

    monkeypatch.setattr(psutil, 'cpu_count', psutil_cpu_count)
    monkeypatch.setattr(os, 'cpu_count', os_cpu_count)
    assert get_cores() == 1
    assert get_cores(physical=True) == 1


def test_get_cores_fallback(monkeypatch):
    import psutil
    import os

    def psutil_cpu_count(logical):
        return None

    def os_cpu_count():
        return None

    monkeypatch.setattr(psutil, 'cpu_count', psutil_cpu_count)
    monkeypatch.setattr(os, 'cpu_count', os_cpu_count)
    assert get_cores() == 1
    assert get_cores(physical=True) == 1


def test_get_plugin():
    assert [] == get_plugins("nothingtofind")
    assert len(get_plugins("showtask")) > 0
    assert len(get_plugins("path_resolver")) > 0

    assert len(get_plugins("path_resolver", "https")) == 1


def test_default_sc_dir():
    with patch("pathlib.Path.home") as home:
        home.return_value = "this"
        assert default_sc_dir() == os.path.join("this", ".sc")


def test_default_credentials_file():
    with patch("pathlib.Path.home") as home:
        home.return_value = "this"
        assert default_credentials_file() == os.path.join("this", ".sc", "credentials")


def test_default_cache_dir():
    with patch("pathlib.Path.home") as home:
        home.return_value = "this"
        assert default_cache_dir() == os.path.join("this", ".sc", "cache")


def test_default_email_credentials_file():
    with patch("pathlib.Path.home") as home:
        home.return_value = "this"
        assert default_email_credentials_file() == os.path.join("this", ".sc", "email.json")


@pytest.mark.parametrize("path", ["test0", "that", "this", "works"])
def test_default_sc_path(path):
    with patch("pathlib.Path.home") as home:
        home.return_value = "this"
        assert default_sc_path(path) == os.path.join("this", ".sc", path)


@pytest.mark.parametrize("args,line,expected", [
    # T1: Basic Match
    ("hello", "this is a hello world", "this is a hello world"),
    # T2: Basic No Match
    ("goodbye", "this is a hello world", None),
    # T3: Input Line None
    ("hello", None, None),
    # T4: Empty Pattern
    ("", "line", None),
    # T5: Invert Match (-v, Match found -> returns None)
    ("-v hello", "contains hello", None),
    # T6: Invert No Match (-v, No match -> returns Line)
    ("-v goodbye", "contains hello", "contains hello"),
    # T7: Ignore Case (-i, No Match without flag)
    ("hello", "HELLO world", None),
    # T8: Ignore Case (-i, Match with flag)
    ("-i hello", "HELLO world", "HELLO world"),
    # T9: Whole Word (-w, Substring match -> fail)
    ("-w cat", "The catalog is big.", None),
    # T10: Whole Word (-w, Word match -> success)
    ("-w cat", "The cat sat.", "The cat sat."),
    # T11: Exact Line (-x, Partial match -> fail)
    ("-x hello", "hello world", None),
    # T12: Exact Line (-x, Exact match -> success)
    ("-x hello", "hello", "hello"),
    # T13: Only Match (-o)
    ("-o hello", "Hello hello world", "hello"),
    # T14: Combined (-vi, Invert + Ignore Case)
    ("-vi HELLO", "This is hello world", None),
    # T15: Combined (-o -i)
    ("-o -i world", "Hello WORLD", "WORLD"),
    # T16: Combined (-xw, Exact + Word)
    ("-xw test", "test", "test"),
    # T17: Combined (-xw, Partial Fail)
    ("-xw testing", "testing is hard", None),
    # T20: Pattern with -e (Treats -hello as pattern)
    ("-e -hello world", "-hello world is great", "-hello world is great"),
])
def test_grep_logic(args, line, expected):
    """Tests the core logic and return values of the grep function."""
    assert grep(logging.getLogger(), args, line) == expected


def test_unknown_switch_error(caplog):
    # T18: Unknown Switch Error
    grep(logging.getLogger(), "-q hello", "test")
    assert "Unknown switch: -q" in caplog.text


def test_concatenated_unknown_switch_error(caplog):
    # T19: Concatenated Unknown Switch
    grep(logging.getLogger(), "-vq hello", "test")
    assert "Unknown switch: -q" in caplog.text


def test_invalid_regex_error(caplog):
    # T21: Invalid Regex Pattern
    grep(logging.getLogger(), "*", "test")
    # Check that we logged an error starting with our specific message
    assert "Invalid regex pattern" in caplog.text
