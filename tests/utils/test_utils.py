import pytest
import hashlib
import pathlib
from siliconcompiler.utils import truncate_text, get_hashed_filename


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
