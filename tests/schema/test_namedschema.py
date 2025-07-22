import pytest

import os.path

from siliconcompiler.schema import NamedSchema
from siliconcompiler.schema import EditableSchema, Parameter


def test_name():
    assert NamedSchema("myname").name == "myname"


def test_set_name_empty():
    schema = NamedSchema()
    assert schema.name is None
    schema.set_name("myname")
    assert schema.name == "myname"


def test_set_name_repeat():
    schema = NamedSchema()
    assert schema.name is None
    schema.set_name("myname")
    assert schema.name == "myname"
    with pytest.raises(RuntimeError, match="Cannot call set_name more than once."):
        schema.set_name("myname")


def test_set_name_with_name():
    schema = NamedSchema("myname")
    assert schema.name == "myname"
    with pytest.raises(RuntimeError, match="Cannot call set_name more than once."):
        schema.set_name("myname")


def test_set_name_with_invalid_name():
    with pytest.raises(ValueError, match=r"Named schema object cannot contains: \."):
        NamedSchema("myname.this")


def test_type():
    with pytest.raises(NotImplementedError, match="Must be implemented by the child classes."):
        NamedSchema().type()


def test_name_no_init():
    class Test(NamedSchema):
        def __init__(self):
            # do not init NamedSchema
            pass

    assert Test().name is None


def test_copy_name():
    schema = NamedSchema("myname")
    assert schema.name == "myname"

    assert schema.copy().name == "myname"


def test_from_dict():
    schema = NamedSchema("myname")
    edit = EditableSchema(schema)
    edit.insert("test0", "test1", Parameter("str"))

    check_schema = schema.copy()

    assert schema.set("test0", "test1", "paramvalue")
    assert schema.get("test0", "test1") == "paramvalue"

    check_schema._from_dict(schema.getdict(), [], version=None)

    assert check_schema.name == "myname"
    assert check_schema.get("test0", "test1") == "paramvalue"


def test_from_dict_with_name():
    schema = NamedSchema("myname")
    edit = EditableSchema(schema)
    edit.insert("test0", "test1", Parameter("str"))

    check_schema = schema.copy()

    assert schema.set("test0", "test1", "paramvalue")
    assert schema.get("test0", "test1") == "paramvalue"

    check_schema._from_dict(schema.getdict(), ["notaname", "newname"], version=None)

    assert check_schema.name == "newname"
    assert check_schema.get("test0", "test1") == "paramvalue"


def test_copy_named():
    schema = NamedSchema("myname")
    new_schema = schema.copy()

    assert new_schema.name == "myname"


def test_copy_no_name():
    schema = NamedSchema("name")
    new_schema = schema.copy()

    assert new_schema.name == "name"


def test_copy_no_name_default():
    schema = NamedSchema("name")
    new_schema = schema.copy(key=["default"])

    assert new_schema.name == "name"


def test_copy_no_name_renamed():
    schema = NamedSchema("name")
    new_schema = schema.copy(key=["newname"])

    assert new_schema.name == "newname"


def test_inserting_name():
    lower_schema = NamedSchema("name")
    edit = EditableSchema(lower_schema)
    edit.insert("test2", Parameter("str"))
    schema = NamedSchema("myname")
    edit = EditableSchema(schema)
    edit.insert("test0", "default", lower_schema)

    assert schema.get("test0", "default", field="schema").name == "name"

    assert schema.set("test0", "checkname", "test2", "this")
    assert schema.get("test0", "checkname", field="schema").name == "checkname"


def test_from_manifest_no_args():
    with pytest.raises(RuntimeError, match="filepath or dictionary is required"):
        NamedSchema.from_manifest("name")


def test_from_manifest_file():
    class NewSchema(NamedSchema):
        def __init__(self, name):
            super().__init__(name)
            edit = EditableSchema(self)
            edit.insert("test0", "test1", Parameter("str"))
    schema = NewSchema("myname")
    schema.set("test0", "test1", "testthis")

    assert not os.path.isfile("test.json.gz")
    schema.write_manifest("test.json.gz")
    assert os.path.isfile("test.json.gz")

    new_schema = NewSchema.from_manifest("newname", filepath="test.json.gz")

    assert new_schema.getdict() == schema.getdict()
    assert new_schema.name == "newname"


def test_from_manifest_cfg():
    class NewSchema(NamedSchema):
        def __init__(self, name):
            super().__init__(name)
            edit = EditableSchema(self)
            edit.insert("test0", "test1", Parameter("str"))
    schema = NewSchema("name")
    schema.set("test0", "test1", "testthis")

    new_schema = NewSchema.from_manifest("newname", cfg=schema.getdict())

    assert new_schema.getdict() == schema.getdict()
    assert new_schema.name == "newname"
