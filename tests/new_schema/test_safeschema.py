import pytest

from siliconcompiler.schema.new.parameter import Parameter
from siliconcompiler.schema.new.baseschema import BaseSchema
from siliconcompiler.schema.new.editableschema import EditableSchema
from siliconcompiler.schema.new.safeschema import SafeSchema


@pytest.fixture
def schema():
    manifest = BaseSchema()
    EditableSchema(manifest).add("test0", Parameter("str"))
    EditableSchema(manifest).add("test1", "test2", Parameter("[str]"))
    EditableSchema(manifest).add("test3", "default", Parameter("int"))
    EditableSchema(manifest).add("test4", "test5", "test6", Parameter("str"))
    return manifest


def test_init():
    schema = SafeSchema()
    assert schema.locked is True


def test_unlock_lock():
    schema = SafeSchema()
    assert schema.locked is True
    schema.unlock()
    assert schema.locked is False
    schema.lock()
    assert schema.locked is True


def test_readin(schema):
    safe = SafeSchema.from_manifest(cfg=schema.getdict())

    assert schema.getdict() == safe.getdict()


def test_set_locked(schema):
    safe = SafeSchema.from_manifest(cfg=schema.getdict())

    with pytest.raises(RuntimeError, match="schema is locked"):
        safe.set("test0", "testing")


def test_add_locked(schema):
    safe = SafeSchema.from_manifest(cfg=schema.getdict())

    with pytest.raises(RuntimeError, match="schema is locked"):
        safe.add("test1", "test2", "testing")


def test_set_unlocked(schema):
    safe = SafeSchema.from_manifest(cfg=schema.getdict())
    safe.unlock()

    safe.set("test0", "testing")
    assert safe.get("test0") == "testing"

    safe.set("test4", "test5", "test6", "testing")
    assert safe.get("test4", "test5", "test6") == "testing"


def test_add_unlocked(schema):
    safe = SafeSchema.from_manifest(cfg=schema.getdict())
    safe.unlock()

    safe.add("test1", "test2", "testing")
    assert safe.get("test1", "test2") == ["testing"]
