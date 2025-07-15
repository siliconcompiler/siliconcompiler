import logging

import os.path

from siliconcompiler.schema import BaseSchema, EditableSchema
from siliconcompiler.packageschema import PackageSchema


def test_register():
    schema = PackageSchema()
    assert schema.getkeys("source") == tuple()
    assert schema.register("testpackage", "pathtosource") is True
    assert schema.get("source", "testpackage", "path") == "pathtosource"
    assert schema.get("source", "testpackage", "ref") is None


def test_register_ref():
    schema = PackageSchema()
    assert schema.getkeys("source") == tuple()
    assert schema.register("testpackage", "pathtosource", ref="123456") is True
    assert schema.get("source", "testpackage", "path") == "pathtosource"
    assert schema.get("source", "testpackage", "ref") == "123456"


def test_register_ref_no_clobber():
    schema = PackageSchema()
    assert schema.getkeys("source") == tuple()
    assert schema.register("testpackage", "pathtosource", ref="123456") is True
    assert schema.get("source", "testpackage", "path") == "pathtosource"
    assert schema.get("source", "testpackage", "ref") == "123456"
    assert schema.register("testpackage", "pathtosource", ref="1234567", clobber=False) is False
    assert schema.get("source", "testpackage", "ref") == "123456"


def test_register_ref_with_clobber():
    schema = PackageSchema()
    assert schema.getkeys("source") == tuple()
    assert schema.register("testpackage", "pathtosource", ref="123456") is True
    assert schema.get("source", "testpackage", "path") == "pathtosource"
    assert schema.get("source", "testpackage", "ref") == "123456"
    assert schema.register("testpackage", "pathtosource", ref="1234567", clobber=True) is True
    assert schema.get("source", "testpackage", "ref") == "1234567"


def test_register_ref_file():
    schema = PackageSchema()
    assert schema.getkeys("source") == tuple()
    with open("test.txt", "w") as f:
        f.write("test")

    assert schema.register("testpackage", "test.txt") is True
    assert schema.get("source", "testpackage", "path") == os.path.abspath(".")
    assert schema.get("source", "testpackage", "ref") is None


def test_register_ref_dir():
    schema = PackageSchema()
    assert schema.getkeys("source") == tuple()

    assert schema.register("testpackage", ".") is True
    assert schema.get("source", "testpackage", "path") == os.path.abspath(".")
    assert schema.get("source", "testpackage", "ref") is None


def test_get_resolvers_empty():
    schema = PackageSchema()
    assert schema.get_resolvers() == {}
