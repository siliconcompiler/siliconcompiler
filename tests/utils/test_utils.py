import pytest
import hashlib
import pathlib
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
    (pathlib.PureWindowsPath("one/one.txt"), "one_4597eedf608e3c071ee547ebc2a5c0f12d35aa7e.txt"),
    (pathlib.PurePosixPath("one/one.txt"), "one_4597eedf608e3c071ee547ebc2a5c0f12d35aa7e.txt"),
    ("one.txt", "one_0dec7b0043de0ab90e645d9c4b445c82e317606c.txt"),
    ("two", "two_ad782ecdac770fc6eb9a62e44f90873fb97fb26b"),
    ("two.txt", "two_aa733fde1b4def7e448cce0a63d387e00b863e07.txt"),
    ("two.txt.gz", "two_200961af32c1d768c05fbd2e7a0402c3a748ebf7.txt.gz")
])
def test_hashed_filename(path, expect):
    assert get_hashed_filename(path) == expect


@pytest.mark.parametrize("hash,expect", [
    (hashlib.md5, "filename_9949a49044257734be0333937d130f8c.txt"),
    (hashlib.sha1, "filename_8349c9e2d3341940dc146d5f2fccb33697e62657.txt"),
    (hashlib.sha256,
     "filename_4fe157558bb127fbaf5b4dd0d4719d67520c753bfaff83c16ada67dd8d1cab2b.txt")
])
def test_hashed_filename_hashtype(hash, expect):
    assert get_hashed_filename('filename.txt', hash=hash) == expect


def test_hashed_filename_package():
    assert get_hashed_filename('filename.txt', package="test0") == \
        "filename_23ea68481eafa08cddb8a432291ed06d2eb20520.txt"
    assert get_hashed_filename('filename.txt', package="test1") == \
        "filename_23e779cf3ce3f704347db249c3c8ecd8dcc51714.txt"

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
    assert str(pathlib.Path.home() / "1") == _resolve_env_vars(Chip(''), "~/1", "test", "0")


def test_resolve_env_vars_missing():
    chip = Chip('')
    log = chip._add_file_logger("log")
    assert "${TEST_VAR}/1" == _resolve_env_vars(chip, "${TEST_VAR}/1", "test", "0")

    log.flush()
    with open('log') as f:
        text = f.read()
        assert "Variable TEST_VAR in ${TEST_VAR}/1 not defined in environment" in text


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
