import pytest

from siliconcompiler.schema.new.baseschema import BaseSchema
from siliconcompiler.schema.new.editableschema import EditableSchema
from siliconcompiler.schema.new.parameter import Parameter


def test_get_value():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.add("test0", "test1", Parameter("str"))

    schema.set("test0", "test1", "hello")
    assert schema.get("test0", "test1") == "hello"


def test_get_invalid_key():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.add("test0", "test1", Parameter("str"))

    with pytest.raises(KeyError, match=r"\[test0,test2\] is not a valid keypath"):
        schema.get("test0", "test2")


def test_get_field():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.add("test0", "test1", Parameter("str"))

    schema.set("test0", "test1", "hello")
    assert schema.get("test0", "test1", field="type") == "str"


def test_get_parameter():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.add("test0", "test1", Parameter("str"))

    schema.set("test0", "test1", "hello")
    assert isinstance(schema.get("test0", "test1", field=None), Parameter)


def test_set():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.add("test0", "test1", Parameter("str"))
    edit.add("test2", "default", Parameter("str"))

    schema.set("test0", "test1", "hello")
    assert schema.get("test0", "test1") == "hello"


def test_add():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.add("test0", "test1", Parameter("[str]"))

    schema.add("test0", "test1", "hello")
    assert schema.get("test0", "test1") == ["hello"]


def test_set_invalid_key():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.add("test0", "test1", Parameter("str"))

    with pytest.raises(KeyError, match=r"\[test0,test2\] is not a valid keypath"):
        schema.set("test0", "test2", "hello")


def test_add_invalid_key():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.add("test0", "test1", Parameter("str"))

    with pytest.raises(KeyError, match=r"\[test0,test2\] is not a valid keypath"):
        schema.add("test0", "test2", "hello")


def test_set_partial_key():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.add("test0", "test1", Parameter("str"))

    with pytest.raises(KeyError, match=r"\[test0\] is not a valid keypath"):
        schema.set("test0", "hello")


def test_get_empty_key():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.add("test0", "test1", Parameter("str"))

    with pytest.raises(KeyError, match=r"\[\] is not a valid keypath"):
        schema.get()


def test_get_default_key():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.add("test0", "default", "test1", Parameter("str"))

    assert schema.get("test0", "test_default", "test1") is None


def test_set_empty_key_no_value():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.add("test0", "test1", Parameter("str"))

    with pytest.raises(KeyError, match=r"keypath and value is required"):
        schema.set()


def test_set_empty_key_with_value():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.add("test0", "test1", Parameter("str"))

    with pytest.raises(KeyError, match=r"keypath and value is required"):
        schema.set("hello")


def test_add_empty_key_no_value():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.add("test0", "test1", Parameter("str"))

    with pytest.raises(KeyError, match=r"keypath and value is required"):
        schema.add()


def test_add_empty_key_with_value():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.add("test0", "test1", Parameter("str"))

    with pytest.raises(KeyError, match=r"keypath and value is required"):
        schema.add("hello")


def test_add_partial_key():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.add("test0", "test1", Parameter("str"))

    with pytest.raises(KeyError, match=r"\[test0\] is not a valid keypath"):
        schema.add("test0", "hello")


def test_unset_invalid_key():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.add("test0", "test1", Parameter("str"))

    with pytest.raises(KeyError, match=r"\[test0,test3\] is not a valid keypath"):
        schema.unset("test0", "test3")


def test_unset():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.add("test0", "test1", Parameter("str"))

    assert schema.set("test0", "test1", "hello")
    assert schema.get("test0", "test1") == "hello"

    schema.unset("test0", "test1")
    assert schema.get("test0", "test1") is None


def test_remove_not_parameter():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.add("test0", "test1", Parameter("str"))

    schema.remove("test0", "test1")
    assert schema.getkeys("test0") == tuple(["test1"])


def test_remove_not_schema():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.add("test0", "test1", Parameter("str"))

    schema.remove("test0")
    assert schema.getkeys() == tuple(["test0"])
    assert schema.getkeys("test0") == tuple(["test1"])


def test_remove_not_default():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.add("test0", "default", Parameter("str"))

    schema.remove("test0", "default")
    assert schema.getkeys() == tuple(["test0"])
    assert schema.getkeys("test0") == tuple()


def test_remove_invalid_key():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.add("test0", "default", Parameter("str"))

    with pytest.raises(KeyError, match=r"\[test1,test1\] is not a valid keypath"):
        schema.remove("test1", "test1")


def test_remove_parameter():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.add("test0", "default", Parameter("str"))

    assert schema.set("test0", "test1", "hello")
    assert schema.getkeys("test0") == tuple(["test1"])

    schema.remove("test0", "test1")
    assert schema.getkeys("test0") == tuple()


def test_remove_schema():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.add("test0", "default", "test1", Parameter("str"))

    assert schema.set("test0", "test2", "test1", "hello")
    assert schema.getkeys("test0") == tuple(["test2"])
    assert schema.getkeys("test0", "test2") == tuple(["test1"])

    schema.remove("test0", "test2")
    assert schema.getkeys("test0") == tuple()


def test_remove_missing_final_key():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.add("test0", "default", "test1", Parameter("str"))

    assert schema.set("test0", "test2", "test1", "hello")
    assert schema.getkeys("test0") == tuple(["test2"])
    assert schema.getkeys("test0", "test2") == tuple(["test1"])

    schema.remove("test0", "test3")
    assert schema.getkeys("test0") == tuple(["test2"])


def test_remove_locked():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.add("test0", "default", "test1", Parameter("str"))

    assert schema.set("test0", "test2", "test1", "hello")
    assert schema.set("test0", "test2", "test1", True, field="lock")
    assert schema.getkeys("test0") == tuple(["test2"])
    assert schema.getkeys("test0", "test2") == tuple(["test1"])

    schema.remove("test0", "test2")
    assert schema.getkeys("test0") == tuple(["test2"])


def test_get_dict():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.add("test0", "default", "test1", Parameter("str"))

    assert schema.getdict() == {
        'test0': {
            'default': {
                'test1': {
                    'example': [],
                    'help': None,
                    'lock': False,
                    'node': {
                        'default': {
                            'default': {
                                'signature': None,
                                'value': None,
                            },
                        },
                    },
                    'notes': None,
                    'pernode': 'never',
                    'require': False,
                    'scope': 'job',
                    'shorthelp': None,
                    'switch': [],
                    'type': 'str',
                },
            },
        },
    }


def test_get_dict_from_dict():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.add("test0", "default", "test1", Parameter("str"))

    check_schema = schema.copy()

    schema.set("test0", "testdefault", "test1", "4")

    assert check_schema.get("test0", "testdefault", "test1") is None

    check_schema._from_dict(schema.getdict(), [], None)

    assert schema.getdict() == check_schema.getdict()
