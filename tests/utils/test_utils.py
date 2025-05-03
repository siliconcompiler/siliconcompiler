import pytest
import pathlib
import sys
from siliconcompiler import Chip
from siliconcompiler.utils import \
    truncate_text, get_hashed_filename, safecompare, _resolve_env_vars, get_cores, \
    get_plugins


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


@pytest.mark.parametrize("path,expect", [
    (pathlib.PureWindowsPath("one/one.txt"), "one_fe05bcdcdc4928012781a5f1a2a77cbb5398e106.txt"),
    (pathlib.PurePosixPath("one/one.txt"), "one_fe05bcdcdc4928012781a5f1a2a77cbb5398e106.txt"),
    ("one.txt", "one_3a52ce780950d4d969792a2559cd519d7ee8c727.txt"),
    ("two", "two_3a52ce780950d4d969792a2559cd519d7ee8c727"),
    ("two.txt", "two_3a52ce780950d4d969792a2559cd519d7ee8c727.txt"),
    ("two.txt.gz", "two_3a52ce780950d4d969792a2559cd519d7ee8c727.txt.gz")
])
def test_hashed_filename(path, expect):
    assert get_hashed_filename(path) == expect


def test_hashed_filename_package():
    assert get_hashed_filename('filename.txt', package="test0") == \
        "filename_765ed134f3871334dbd46603ff7f7db306036020.txt"
    assert get_hashed_filename('filename.txt', package="test1") == \
        "filename_5d4ed2691c7b8ad46c00ce78043d4cc11c1744fc.txt"

    assert get_hashed_filename('filename', package="test0") != \
        get_hashed_filename('filename', package="test1")


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
    assert safecompare(Chip(''), a, op, b) is expect


def test_safecompare_invalid_operator():
    with pytest.raises(ValueError, match="Illegal comparison operation !"):
        safecompare(Chip(''), 1, "!", 2)


def test_resolve_env_vars(monkeypatch):
    monkeypatch.setenv("TEST_VAR", "1234")
    assert "1234/1" == _resolve_env_vars(Chip(''), "${TEST_VAR}/1", "test", "0")
    assert "1234/1" == _resolve_env_vars(Chip(''), "$TEST_VAR/1", "test", "0")


def test_resolve_env_vars_user(monkeypatch):
    if sys.platform == "win32":
        monkeypatch.delenv("USERPROFILE", raising=False)
        monkeypatch.setenv("USERNAME", "testuser")
        monkeypatch.setenv("HOMEDRIVE", "C:/")
        monkeypatch.setenv("HOMEPATH", "home")

        expect = pathlib.Path("C:/home/1")
    else:
        expect = pathlib.Path.home() / "1"

    assert expect == pathlib.Path(_resolve_env_vars(Chip(''), "~/1", "test", "0"))


def test_resolve_env_vars_missing(caplogger):
    chip = Chip('')
    log = caplogger(chip)
    assert "${TEST_VAR}/1" == _resolve_env_vars(chip, "${TEST_VAR}/1", "test", "0")

    assert "Variable TEST_VAR in ${TEST_VAR}/1 not defined in environment" in log()


def test_get_cores_logical(monkeypatch):
    import psutil

    def cpu_count(logical):
        assert logical
        return 2

    monkeypatch.setattr(psutil, 'cpu_count', cpu_count)
    assert get_cores(Chip('')) == 2


def test_get_cores_physical(monkeypatch):
    import psutil

    def cpu_count(logical):
        assert not logical
        return 2

    monkeypatch.setattr(psutil, 'cpu_count', cpu_count)
    assert get_cores(Chip(''), physical=True) == 2


def test_get_cores_use_os(monkeypatch):
    import psutil
    import os

    def psutil_cpu_count(logical):
        return None

    def os_cpu_count():
        return 6

    monkeypatch.setattr(psutil, 'cpu_count', psutil_cpu_count)
    monkeypatch.setattr(os, 'cpu_count', os_cpu_count)
    assert get_cores(Chip('')) == 6
    assert get_cores(Chip(''), physical=True) == 3


def test_get_cores_use_os_one_core(monkeypatch):
    import psutil
    import os

    def psutil_cpu_count(logical):
        return None

    def os_cpu_count():
        return 1

    monkeypatch.setattr(psutil, 'cpu_count', psutil_cpu_count)
    monkeypatch.setattr(os, 'cpu_count', os_cpu_count)
    assert get_cores(Chip('')) == 1
    assert get_cores(Chip(''), physical=True) == 1


def test_get_cores_fallback(monkeypatch):
    import psutil
    import os

    def psutil_cpu_count(logical):
        return None

    def os_cpu_count():
        return None

    monkeypatch.setattr(psutil, 'cpu_count', psutil_cpu_count)
    monkeypatch.setattr(os, 'cpu_count', os_cpu_count)
    assert get_cores(Chip('')) == 1
    assert get_cores(Chip(''), physical=True) == 1


def test_get_plugin():
    assert [] == get_plugins("nothingtofind")
    assert len(get_plugins("show")) > 0
    assert len(get_plugins("path_resolver")) > 0
    assert len(get_plugins("docs")) > 0
    assert len(get_plugins("target")) > 0

    assert len(get_plugins("path_resolver", "https")) == 1
