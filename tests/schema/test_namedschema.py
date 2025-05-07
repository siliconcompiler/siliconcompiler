from siliconcompiler.schema import NamedSchema
from siliconcompiler.schema import EditableSchema, Parameter


def test_no_name():
    assert NamedSchema().name is None


def test_name():
    assert NamedSchema("myname").name == "myname"


def test_set_name():
    schema = NamedSchema("myname")
    assert schema.name == "myname"
    schema.set_name("mynewname")
    assert schema.name == "mynewname"


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
