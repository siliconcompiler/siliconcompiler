import pytest

from siliconcompiler.schema import Parameter
from siliconcompiler.schema import BaseSchema
from siliconcompiler.schema import EditableSchema
from siliconcompiler.schema import SafeSchema


@pytest.fixture
def schema():
    manifest = BaseSchema()
    EditableSchema(manifest).insert("test0", Parameter("str"))
    EditableSchema(manifest).insert("test1", "test2", Parameter("[str]"))
    EditableSchema(manifest).insert("test3", "default", Parameter("int"))
    EditableSchema(manifest).insert("test4", "test5", "test6", Parameter("str"))
    return manifest


def test_readin(schema):
    safe = SafeSchema.from_manifest(cfg=schema.getdict())

    assert schema.getdict() == safe.getdict()


def test_set(schema):
    safe = SafeSchema.from_manifest(cfg=schema.getdict())

    safe.set("test0", "testing")
    assert safe.get("test0") == "testing"

    safe.set("test4", "test5", "test6", "testing")
    assert safe.get("test4", "test5", "test6") == "testing"


def test_add(schema):
    safe = SafeSchema.from_manifest(cfg=schema.getdict())

    safe.add("test1", "test2", "testing")
    assert safe.get("test1", "test2") == ["testing"]


def test_from_dict_with_list():
    safe = SafeSchema()
    assert safe.getdict() == {}
    safe._from_dict([], [], [])
    assert safe.getdict() == {}
