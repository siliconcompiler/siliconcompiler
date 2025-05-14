from siliconcompiler.schema import NamedSchema
from siliconcompiler.schema import EditableSchema, Parameter


def test_no_name():
    assert NamedSchema().name() is None


def test_name():
    assert NamedSchema("myname").name() == "myname"


def test_copy_name():
    schema = NamedSchema("myname")
    assert schema.name() == "myname"

    assert schema.copy().name() == "myname"


def test_from_dict():
    schema = NamedSchema("myname")
    edit = EditableSchema(schema)
    edit.insert("test0", "test1", Parameter("str"))

    check_schema = schema.copy()

    assert schema.set("test0", "test1", "paramvalue")
    assert schema.get("test0", "test1") == "paramvalue"

    check_schema._from_dict(schema.getdict(), [], version=None)

    assert check_schema.name() == "myname"
    assert check_schema.get("test0", "test1") == "paramvalue"


def test_from_dict_with_name():
    schema = NamedSchema("myname")
    edit = EditableSchema(schema)
    edit.insert("test0", "test1", Parameter("str"))

    check_schema = schema.copy()

    assert schema.set("test0", "test1", "paramvalue")
    assert schema.get("test0", "test1") == "paramvalue"

    check_schema._from_dict(schema.getdict(), ["notaname", "newname"], version=None)

    assert check_schema.name() == "newname"
    assert check_schema.get("test0", "test1") == "paramvalue"


def test_copy_named():
    schema = NamedSchema("myname")
    new_schema = schema.copy()

    assert new_schema.name() == "myname"


def test_copy_named_key():
    schema = NamedSchema("myname")
    new_schema = schema.copy(key=["ignoredname"])

    assert new_schema.name() == "myname"


def test_copy_no_name():
    schema = NamedSchema()
    new_schema = schema.copy()

    assert new_schema.name() is None


def test_copy_no_name_default():
    schema = NamedSchema()
    new_schema = schema.copy(key=["default"])

    assert new_schema.name() is None


def test_copy_no_name_renamed():
    schema = NamedSchema()
    new_schema = schema.copy(key=["newname"])

    assert new_schema.name() == "newname"


def test_inserting_name():
    lower_schema = NamedSchema()
    edit = EditableSchema(lower_schema)
    edit.insert("test2", Parameter("str"))
    schema = NamedSchema("myname")
    edit = EditableSchema(schema)
    edit.insert("test0", "default", lower_schema)

    assert schema.get("test0", "default", field="schema").name() is None

    assert schema.set("test0", "checkname", "test2", "this")
    assert schema.get("test0", "checkname", field="schema").name() == "checkname"
