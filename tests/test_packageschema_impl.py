import logging

import os.path

from siliconcompiler import Chip
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


def test_get_path_cache_empty():
    schema = PackageSchema()
    assert schema.get_path_cache() == {}


def test_get_path_cache_via_set_caches():
    schema = PackageSchema()
    assert schema.get_path_cache() == {}
    schema._set_cache("testpackage", "thispath")
    assert schema.get_path_cache() == {'testpackage': 'thispath'}


def test_get_resolvers_empty():
    schema = PackageSchema()
    assert schema.get_resolvers() == {}


def test_get_resolvers_with_value(caplog):
    chip = Chip('')
    chip.logger = logging.getLogger()
    chip.logger.setLevel(logging.INFO)
    schema = chip.schema.get("package", field="schema")
    assert "testpackage" not in schema.get_resolvers()
    assert schema.get_path_cache() == {}
    assert schema.register("testpackage", ".") is True
    resolvers = schema.get_resolvers()
    assert "testpackage" in resolvers
    assert resolvers["testpackage"]() == os.path.abspath(".")
    assert schema.get_path_cache() == {'testpackage': os.path.abspath(".")}
    assert "Found testpackage data at " in caplog.text
