# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

from siliconcompiler.tools._common import PlusArgs


def test_plusargs_add_plusargs():
    task = PlusArgs()
    task.add_plusargs(("key1", "val1"))
    task.add_plusargs(("key2", "val2"))
    assert task.get("var", "plusargs") == [("key1", "val1"), ("key2", "val2")]
    task.add_plusargs(("key3", "val3"), clobber=True)
    assert task.get("var", "plusargs") == [("key3", "val3")]


def test_plusargs_get_plusargs():
    task = PlusArgs()
    task.set("var", "plusargs", [("define", "FOO"), ("incdir", "/path")])
    assert task.get_plusargs() == [("define", "FOO"), ("incdir", "/path")]
    task.set("var", "plusargs", [("key3", "val3")], step='test', index='1')
    assert task.get_plusargs(step='test', index='1') == [("key3", "val3")]
    assert task.get_plusargs() == [("define", "FOO"), ("incdir", "/path")]


def test_plusargs_get_plusargs_empty():
    task = PlusArgs()
    assert task.get_plusargs() == []
