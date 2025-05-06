import pytest

import os.path

from siliconcompiler.schema import BaseSchema
from siliconcompiler.schema import EditableSchema
from siliconcompiler.schema import Parameter


def test_get_value():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "test1", Parameter("str"))

    schema.set("test0", "test1", "hello")
    assert schema.get("test0", "test1") == "hello"


def test_get_invalid_key():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "test1", Parameter("str"))

    with pytest.raises(KeyError, match=r"\[test0,test2\] is not a valid keypath"):
        schema.get("test0", "test2")


def test_get_field():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "test1", Parameter("str"))

    schema.set("test0", "test1", "hello")
    assert schema.get("test0", "test1", field="type") == "str"


def test_get_parameter():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "test1", Parameter("str"))

    schema.set("test0", "test1", "hello")
    assert isinstance(schema.get("test0", "test1", field=None), Parameter)


def test_set():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "test1", Parameter("str"))
    edit.insert("test2", "default", Parameter("str"))

    schema.set("test0", "test1", "hello")
    assert schema.get("test0", "test1") == "hello"


def test_add():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "test1", Parameter("[str]"))

    schema.add("test0", "test1", "hello")
    assert schema.get("test0", "test1") == ["hello"]


def test_set_invalid_key():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "test1", Parameter("str"))

    with pytest.raises(KeyError, match=r"\[test0,test2\] is not a valid keypath"):
        schema.set("test0", "test2", "hello")


def test_add_invalid_key():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "test1", Parameter("str"))

    with pytest.raises(KeyError, match=r"\[test0,test2\] is not a valid keypath"):
        schema.add("test0", "test2", "hello")


def test_set_partial_key():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "test1", Parameter("str"))

    with pytest.raises(KeyError, match=r"\[test0\] is not a valid keypath"):
        schema.set("test0", "hello")


def test_get_empty_key():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "test1", Parameter("str"))

    with pytest.raises(KeyError, match=r"\[\] is not a valid keypath"):
        schema.get()


def test_get_default_key():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "default", "test1", Parameter("str"))

    assert schema.get("test0", "test_default", "test1") is None


def test_set_empty_key_no_value():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "test1", Parameter("str"))

    with pytest.raises(KeyError, match=r"keypath and value is required"):
        schema.set()


def test_set_empty_key_with_value():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "test1", Parameter("str"))

    with pytest.raises(KeyError, match=r"keypath and value is required"):
        schema.set("hello")


def test_add_empty_key_no_value():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "test1", Parameter("str"))

    with pytest.raises(KeyError, match=r"keypath and value is required"):
        schema.add()


def test_add_empty_key_with_value():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "test1", Parameter("str"))

    with pytest.raises(KeyError, match=r"keypath and value is required"):
        schema.add("hello")


def test_add_partial_key():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "test1", Parameter("str"))

    with pytest.raises(KeyError, match=r"\[test0\] is not a valid keypath"):
        schema.add("test0", "hello")


def test_unset_invalid_key():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "test1", Parameter("str"))

    with pytest.raises(KeyError, match=r"\[test0,test3\] is not a valid keypath"):
        schema.unset("test0", "test3")


def test_unset():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "test1", Parameter("str"))

    assert schema.set("test0", "test1", "hello")
    assert schema.get("test0", "test1") == "hello"

    schema.unset("test0", "test1")
    assert schema.get("test0", "test1") is None


def test_remove_not_parameter():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "test1", Parameter("str"))

    schema.remove("test0", "test1")
    assert schema.getkeys("test0") == tuple(["test1"])


def test_remove_not_schema():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "test1", Parameter("str"))

    schema.remove("test0")
    assert schema.getkeys() == tuple(["test0"])
    assert schema.getkeys("test0") == tuple(["test1"])


def test_remove_not_default():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "default", Parameter("str"))

    schema.remove("test0", "default")
    assert schema.getkeys() == tuple(["test0"])
    assert schema.getkeys("test0") == tuple()


def test_remove_invalid_key():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "default", Parameter("str"))

    with pytest.raises(KeyError, match=r"\[test1,test1\] is not a valid keypath"):
        schema.remove("test1", "test1")


def test_remove_parameter():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "default", Parameter("str"))

    assert schema.set("test0", "test1", "hello")
    assert schema.getkeys("test0") == tuple(["test1"])

    schema.remove("test0", "test1")
    assert schema.getkeys("test0") == tuple()


def test_remove_schema():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "default", "test1", Parameter("str"))

    assert schema.set("test0", "test2", "test1", "hello")
    assert schema.getkeys("test0") == tuple(["test2"])
    assert schema.getkeys("test0", "test2") == tuple(["test1"])

    schema.remove("test0", "test2")
    assert schema.getkeys("test0") == tuple()


def test_remove_missing_final_key():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "default", "test1", Parameter("str"))

    assert schema.set("test0", "test2", "test1", "hello")
    assert schema.getkeys("test0") == tuple(["test2"])
    assert schema.getkeys("test0", "test2") == tuple(["test1"])

    schema.remove("test0", "test3")
    assert schema.getkeys("test0") == tuple(["test2"])


def test_remove_locked():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "default", "test1", Parameter("str"))

    assert schema.set("test0", "test2", "test1", "hello")
    assert schema.set("test0", "test2", "test1", True, field="lock")
    assert schema.getkeys("test0") == tuple(["test2"])
    assert schema.getkeys("test0", "test2") == tuple(["test1"])

    schema.remove("test0", "test2")
    assert schema.getkeys("test0") == tuple(["test2"])


def test_insert_locked_default():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "default", "default", Parameter("str"))

    assert schema.set("test0", "test1", "test2", "hello")
    assert schema.set("test0", "test1", "default", True, field="lock")
    with pytest.raises(KeyError, match=r"\[test0,test1,test3\] is not a valid keypath"):
        assert schema.set("test0", "test1", "test3", "hello")
    assert schema.set("test0", "test1", "default", False, field="lock")
    assert schema.set("test0", "test1", "test3", "hello")


def test_allkeys():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "default", "test1", Parameter("str"))

    assert schema.set("test0", "test2", "test1", "hello")

    assert schema.allkeys() == {
        ('test0', 'default', 'test1'),
        ('test0', 'test2', 'test1')
    }

    assert schema.allkeys(include_default=False) == {
        ('test0', 'test2', 'test1')
    }

    assert schema.allkeys('test0') == {
        ('default', 'test1'),
        ('test2', 'test1')
    }


def test_allkeys_end_parameter():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "default", "test1", Parameter("str"))
    edit.insert("test1", "default", Parameter("str"))

    assert schema.set("test0", "test2", "test1", "hello")
    assert schema.set("test1", "test3", "world")

    assert schema.allkeys('test0', 'default', 'test1') == set()
    assert schema.allkeys('test0', 'test2', 'test1') == set()

    assert schema.allkeys("test1", "test3") == set()


def test_get_dict():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "default", "test1", Parameter("str"))

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


def test_get_dict_keypath():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "default", "test1", Parameter("str"))

    assert schema.getdict("test0") == {
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
    }


def test_get_dict_keypath_unmatched():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "default", "test1", Parameter("str"))

    assert schema.getdict("test0", "test1") == dict()


def test_get_dict_from_dict():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "default", "test1", Parameter("str"))

    check_schema = schema.copy()

    schema.set("test0", "testdefault", "test1", "4")

    assert check_schema.get("test0", "testdefault", "test1") is None

    schemamissing, inmissing = check_schema._from_dict(schema.getdict(), [], None)
    assert not inmissing
    assert not schemamissing

    assert schema.getdict() == check_schema.getdict()


def test_get_dict_from_dict_unmatched():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "default", "test1", Parameter("str"))

    check_schema = schema.copy()

    edit.remove("test0")

    schemamissing, inmissing = schema._from_dict(check_schema.getdict(), [], None)
    assert not inmissing
    assert schemamissing == set(["test0"])


def test_getkeys():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "test1", Parameter("str"))

    assert schema.getkeys() == tuple(["test0"])
    assert schema.getkeys("test0") == tuple(["test1"])


def test_getkeys_unmatched():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "test1", Parameter("str"))

    with pytest.raises(KeyError, match=r"\[test1\] is not a valid keypath"):
        schema.getkeys("test1")
    with pytest.raises(KeyError, match=r"\[test0,test0\] is not a valid keypath"):
        schema.getkeys("test0", "test0")
    assert schema.getkeys("test0", "test1") == tuple()


def test_from_manifest_no_args():
    with pytest.raises(RuntimeError, match="filepath or dictionary is required"):
        BaseSchema.from_manifest()


def test_write_manifest():
    from siliconcompiler.schema.baseschema import _has_orjson
    assert _has_orjson

    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "test1", Parameter("str"))

    assert not os.path.isfile("test.json")
    schema.write_manifest("test.json")
    assert os.path.isfile("test.json")


def test_write_manifest_stdjson(monkeypatch):
    import json
    from siliconcompiler.schema import baseschema
    monkeypatch.setattr(baseschema, 'json', json)
    monkeypatch.setattr(baseschema, '_has_orjson', False)
    assert not baseschema._has_orjson

    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "test1", Parameter("str"))

    assert not os.path.isfile("test.json")
    schema.write_manifest("test.json")
    assert os.path.isfile("test.json")


def test_write_manifest_gz():
    from siliconcompiler.schema.baseschema import _has_orjson
    assert _has_orjson

    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "test1", Parameter("str"))

    assert not os.path.isfile("test.json.gz")
    schema.write_manifest("test.json.gz")
    assert os.path.isfile("test.json.gz")


def test_write_manifest_gz_no_gzip(monkeypatch):
    from siliconcompiler.schema import baseschema
    monkeypatch.setattr(baseschema, '_has_gzip', False)
    from siliconcompiler.schema.baseschema import _has_gzip
    assert not _has_gzip

    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "test1", Parameter("str"))

    assert not os.path.isfile("test.json.gz")
    with pytest.raises(RuntimeError, match="gzip is not available"):
        schema.write_manifest("test.json.gz")
    assert not os.path.isfile("test.json.gz")


def test_write_manifest_gz_stdjson(monkeypatch):
    import json
    from siliconcompiler.schema import baseschema
    monkeypatch.setattr(baseschema, 'json', json)
    monkeypatch.setattr(baseschema, '_has_orjson', False)
    assert not baseschema._has_orjson

    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "test1", Parameter("str"))

    assert not os.path.isfile("test.json.gz")
    schema.write_manifest("test.json.gz")
    assert os.path.isfile("test.json.gz")


def test_from_manifest_file():
    from siliconcompiler.schema.baseschema import _has_orjson
    assert _has_orjson

    class NewSchema(BaseSchema):
        def __init__(self):
            super().__init__()
            edit = EditableSchema(self)
            edit.insert("test0", "test1", Parameter("str"))
    schema = NewSchema()
    schema.set("test0", "test1", "testthis")

    assert not os.path.isfile("test.json.gz")
    schema.write_manifest("test.json.gz")
    assert os.path.isfile("test.json.gz")

    new_schema = NewSchema.from_manifest(filepath="test.json.gz")

    assert new_schema.getdict() == schema.getdict()


def test_from_manifest_file_stdjson(monkeypatch):
    import json
    from siliconcompiler.schema import baseschema
    monkeypatch.setattr(baseschema, 'json', json)
    monkeypatch.setattr(baseschema, '_has_orjson', False)
    assert not baseschema._has_orjson

    class NewSchema(BaseSchema):
        def __init__(self):
            super().__init__()
            edit = EditableSchema(self)
            edit.insert("test0", "test1", Parameter("str"))
    schema = NewSchema()
    schema.set("test0", "test1", "testthis")

    assert not os.path.isfile("test.json.gz")
    schema.write_manifest("test.json.gz")
    assert os.path.isfile("test.json.gz")

    new_schema = NewSchema.from_manifest(filepath="test.json.gz")

    assert new_schema.getdict() == schema.getdict()


def test_from_manifest_cfg():
    class NewSchema(BaseSchema):
        def __init__(self):
            super().__init__()
            edit = EditableSchema(self)
            edit.insert("test0", "test1", Parameter("str"))
    schema = NewSchema()
    schema.set("test0", "test1", "testthis")

    new_schema = NewSchema.from_manifest(cfg=schema.getdict())

    assert new_schema.getdict() == schema.getdict()


def test_valid():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "test1", Parameter("str"))

    assert schema.valid("test0")
    assert schema.valid("test0", "test1")


def test_valid_check_complete():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "test1", Parameter("str"))

    assert not schema.valid("test0", check_complete=True)
    assert schema.valid("test0", "test1", check_complete=True)


def test_valid_default():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "default", "test1", Parameter("str"))

    assert schema.valid("test0", "default", "test1")
    assert not schema.valid("test0", "thisisdefault", "test1")
    assert schema.valid("test0", "thisisdefault", "test1", default_valid=True)


def test_valid_incomplete():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "test1", Parameter("str"))

    assert not schema.valid("test1")
    assert not schema.valid("test0", "test2")
    assert not schema.valid("test1", "test2")


def test_defvalue():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "test1", Parameter("str", defvalue="defaultvalue"))

    assert schema.get("test0", "test1") == "defaultvalue"
    schema.set("test0", "test1", "newvalue")
    assert schema.get("test0", "test1") == "newvalue"
    schema.unset("test0", "test1")
    assert schema.get("test0", "test1") == "defaultvalue"


def test_getschema():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "test1", Parameter("str"))

    child = schema._getschema("test0")

    child.set("test1", "newvalue")
    assert child.get("test1") == "newvalue"
    assert schema.get("test0", "test1") == "newvalue"


def test_getschema_invalid():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "test1", Parameter("str"))

    with pytest.raises(KeyError, match=r"\[test\] is not a valid keypath"):
        schema._getschema("test")


def test_getschema_parameter():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "test1", Parameter("str"))

    with pytest.raises(ValueError, match=r"\[test0,test1\] is a complete keypath"):
        schema._getschema("test0", "test1")
