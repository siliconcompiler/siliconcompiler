# Copyright 2026 Silicon Compiler Authors. All Rights Reserved.
from siliconcompiler.tools._common import distinct


def test_distinct_empty():
    assert distinct([]) == []


def test_distinct_no_duplicates():
    # Order preserved, nothing removed.
    assert distinct(["a", "b", "c"]) == ["a", "b", "c"]


def test_distinct_removes_duplicates():
    assert distinct(["a", "b", "a", "c", "b"]) == ["a", "b", "c"]


def test_distinct_preserves_first_seen_order():
    # 'c' first appears before 'a', so it must come first in the result.
    assert distinct(["c", "a", "c", "a", "b"]) == ["c", "a", "b"]


def test_distinct_all_duplicates():
    assert distinct(["x", "x", "x"]) == ["x"]


def test_distinct_does_not_mutate_input():
    values = ["a", "a", "b"]
    result = distinct(values)
    assert values == ["a", "a", "b"]
    assert result == ["a", "b"]
    assert result is not values


def test_distinct_returns_new_list_when_unique():
    values = ["a", "b"]
    result = distinct(values)
    assert result == values
    assert result is not values


def test_distinct_paths():
    # Typical frontend use case: the same include dir contributed by two filesets.
    idirs = ["/proj/rtl/include", "/proj/common/include", "/proj/rtl/include"]
    assert distinct(idirs) == ["/proj/rtl/include", "/proj/common/include"]
