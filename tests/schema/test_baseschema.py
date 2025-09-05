import logging
import pytest

import os.path

from pathlib import Path
from unittest.mock import patch

from siliconcompiler.schema import BaseSchema
from siliconcompiler.schema import EditableSchema
from siliconcompiler.schema import Parameter, PerNode
from siliconcompiler.schema import Journal


@pytest.fixture
def sphinx_doc():
    class Document:
        def note_explicit_target(*args):
            pass

    class Env:
        docname = "blah"

    class State:
        document = Document()

    class Doc:
        state = State()
        env = Env()

    return Doc()


def test_copy():
    schema = BaseSchema()
    check_copy = schema.copy()

    assert schema is not check_copy
    assert schema._parent() is schema
    assert check_copy._parent() is check_copy


def test_copy_with_child():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "test1", "test2", Parameter("str"))

    check_copy = schema.copy()

    assert schema is not check_copy
    assert schema._parent() is schema
    assert schema.get("test0", field="schema")._parent() is schema
    assert schema.get("test0", "test1", field="schema")._parent() is \
        schema.get("test0", field="schema")
    assert check_copy._parent() is check_copy
    assert check_copy.get("test0", field="schema")._parent() is check_copy
    assert check_copy.get("test0", "test1", field="schema")._parent() is \
        check_copy.get("test0", field="schema")


def test_copy_with_child_default():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "default", "test2", Parameter("str"))

    assert schema.set("test0", "testthis", "test2", "thisset")

    check_copy = schema.copy()

    assert schema is not check_copy
    assert schema._parent() is schema
    assert schema.get("test0", field="schema")._parent() is schema
    assert schema.get("test0", "default", field="schema")._parent() is \
        schema.get("test0", field="schema")
    assert schema.get("test0", "testthis", field="schema")._parent() is \
        schema.get("test0", field="schema")
    assert check_copy._parent() is check_copy
    assert check_copy.get("test0", field="schema")._parent() is check_copy
    assert check_copy.get("test0", "default", field="schema")._parent() is \
        check_copy.get("test0", field="schema")
    assert check_copy.get("test0", "testthis", field="schema")._parent() is \
        check_copy.get("test0", field="schema")


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


def test_get_invalid_key_from_child():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "test1", Parameter("str"))

    with pytest.raises(KeyError, match=r"\[test0,test2\] is not a valid keypath"):
        schema.get("test0", field="schema").get("test2")


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


def test_set_invalid_key_from_child():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "test1", Parameter("str"))

    with pytest.raises(KeyError, match=r"\[test0,test2\] is not a valid keypath"):
        schema.get("test0", field="schema").set("test2", "hello")


def test_add_invalid_key():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "test1", Parameter("str"))

    with pytest.raises(KeyError, match=r"\[test0,test2\] is not a valid keypath"):
        schema.add("test0", "test2", "hello")


def test_add_invalid_key_from_child():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "test1", Parameter("str"))

    with pytest.raises(KeyError, match=r"\[test0,test2\] is not a valid keypath"):
        schema.get("test0", field="schema").add("test2", "hello")


def test_set_partial_key():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "test1", Parameter("str"))

    with pytest.raises(KeyError, match=r"\[test0\] is not a valid keypath"):
        schema.set("test0", "hello")


def test_set_partial_key_from_child():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "test1", "test2", Parameter("str"))

    with pytest.raises(KeyError, match=r"\[test0,test1\] is not a valid keypath"):
        schema.get("test0", field="schema").set("test1", "hello")


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


def test_add_partial_key_form_child():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "test1", "test2", Parameter("str"))

    with pytest.raises(KeyError, match=r"\[test0,test1\] is not a valid keypath"):
        schema.get("test0", field="schema").add("test1", "hello")


def test_unset_invalid_key():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "test1", Parameter("str"))

    with pytest.raises(KeyError, match=r"\[test0,test3\] is not a valid keypath"):
        schema.unset("test0", "test3")


def test_unset_invalid_key_from_child():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "test1", "test2", Parameter("str"))

    with pytest.raises(KeyError, match=r"\[test0,test3\] is not a valid keypath"):
        schema.get("test0", field="schema").unset("test3")


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


def test_remove_invalid_key_from_child():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "test1", "default", Parameter("str"))

    with pytest.raises(KeyError, match=r"\[test0,test0,test1\] is not a valid keypath"):
        schema.get("test0", field="schema").remove("test0", "test1")


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


def test_getdict():
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
                    'scope': 'global',
                    'shorthelp': None,
                    'switch': [],
                    'type': 'str',
                },
            },
        },
    }


def test_getdict_meta():
    class MetaClass(BaseSchema):
        @classmethod
        def _getdict_type(cls):
            return "testmeta"

    schema = MetaClass()
    edit = EditableSchema(schema)
    edit.insert("test0", "default", "test1", Parameter("str"))

    assert schema.getdict() == {
        '__meta__': {
            'class': 'test_baseschema/MetaClass',
            'sctype': 'testmeta'
        },
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
                    'scope': 'global',
                    'shorthelp': None,
                    'switch': [],
                    'type': 'str',
                },
            },
        },
    }


def test_getdict_meta_imncomplete():
    class MetaClass(BaseSchema):
        @classmethod
        def _getdict_type(cls):
            raise NotImplementedError

    schema = MetaClass()
    edit = EditableSchema(schema)
    edit.insert("test0", "default", "test1", Parameter("str"))

    assert schema.getdict() == {
        '__meta__': {
            'class': 'test_baseschema/MetaClass'
        },
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
                    'scope': 'global',
                    'shorthelp': None,
                    'switch': [],
                    'type': 'str',
                },
            },
        },
    }


def test_getdict_with_set():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "default", "test1", Parameter("{str}"))

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
                                'signature': [],
                                'value': [],
                            },
                        },
                    },
                    'notes': None,
                    'pernode': 'never',
                    'require': False,
                    'scope': 'global',
                    'shorthelp': None,
                    'switch': [],
                    'type': '{str}',
                },
            },
        },
    }


def test_getdict_values_only():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "default", "test1", Parameter("str"))

    assert schema.getdict(values_only=True) == {}


def test_getdict_values_only_with_value():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "default", "test1", Parameter("str"))
    schema.set("test0", "level1", "test1", "this value")

    assert schema.getdict(values_only=True) == {
        'test0': {
            'level1': {
                'test1': {
                    None: {
                        None: 'this value',
                    },
                },
            },
        },
    }


def test_getdict_values_keypath_only_with_value():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "default", "test1", Parameter("str"))
    schema.set("test0", "level1", "test1", "this value")

    assert schema.getdict("test0", "level1", values_only=True) == {
        'test1': {
            None: {
                None: 'this value',
            },
        },
    }


def test_getdict_keypath():
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
                'scope': 'global',
                'shorthelp': None,
                'switch': [],
                'type': 'str',
            },
        },
    }


def test_getdict_keypath_unmatched():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "default", "test1", Parameter("str"))

    assert schema.getdict("test0", "test1") == dict()


def test_getdict_from_dict():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "default", "test1", Parameter("str"))

    check_schema = schema.copy()

    assert schema.getdict() == check_schema.getdict()
    assert schema._parent() is not check_schema._parent()
    assert check_schema.get("test0", field="schema")._parent() is check_schema

    assert schema.set("test0", "testdefault", "test1", "4")

    assert check_schema.get("test0", "testdefault", "test1") is None

    schemamissing, inmissing = check_schema._from_dict(schema.getdict(), [], None)
    assert not inmissing
    assert not schemamissing

    assert schema.getdict() == check_schema.getdict()
    assert schema._parent() is not check_schema._parent()
    assert check_schema.get("test0", field="schema")._parent() is check_schema
    assert check_schema.get("test0", "default", field="schema")._parent() is \
        check_schema.get("test0", field="schema")
    assert check_schema.get("test0", "testdefault", field="schema")._parent() is \
        check_schema.get("test0", field="schema")
    assert check_schema.get("test0", "default", field="schema")._keypath == \
        ('test0', 'default')
    assert check_schema.get("test0", "testdefault", field="schema")._keypath == \
        ('test0', 'testdefault')


def test_getdict_from_dict_unmatched():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "default", "test1", Parameter("str"))

    check_schema = schema.copy()

    edit.remove("test0")

    print(check_schema.getdict())

    schemamissing, inmissing = schema._from_dict({
        'test0': {
            'default': {
                'test1': {
                    'type': 'str',
                    'require': False,
                    'scope': 'global',
                    'lock': False,
                    'switch': [],
                    'shorthelp': None,
                    'example': [],
                    'help': None,
                    'notes': None,
                    'pernode': 'never',
                    'node': {'default': {'default': {'value': None, 'signature': None}}}
                },
            },
        },
    }, [], None)
    assert not inmissing
    assert schemamissing == set(["test0"])


def test_getkeys():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "test1", Parameter("str"))

    assert schema.getkeys() == tuple(["test0"])
    assert schema.getkeys("test0") == tuple(["test1"])


def test_getkeys_ensure_ordering():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test2", "test1", Parameter("str"))
    edit.insert("test0", "test1", Parameter("str"))

    assert schema.getkeys() == ("test0", "test2")
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

        @classmethod
        def _getdict_type(cls):
            return "NewSchema"

    schema = NewSchema()
    schema.set("test0", "test1", "testthis")

    assert not os.path.isfile("test.json.gz")
    schema.write_manifest("test.json.gz")
    assert os.path.isfile("test.json.gz")

    with patch("siliconcompiler.schema.BaseSchema._BaseSchema__get_child_classes") as children:
        children.return_value = {
            "BaseSchema": BaseSchema,
            "NewSchema": NewSchema
        }
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

        @classmethod
        def _getdict_type(cls):
            return "NewSchema"

    schema = NewSchema()
    schema.set("test0", "test1", "testthis")

    assert not os.path.isfile("test.json.gz")
    schema.write_manifest("test.json.gz")
    assert os.path.isfile("test.json.gz")

    with patch("siliconcompiler.schema.BaseSchema._BaseSchema__get_child_classes") as children:
        children.return_value = {
            "BaseSchema": BaseSchema,
            "NewSchema": NewSchema
        }
        new_schema = NewSchema.from_manifest(filepath="test.json.gz")

    assert new_schema.getdict() == schema.getdict()


def test_from_manifest_cfg():
    class NewSchema(BaseSchema):
        def __init__(self):
            super().__init__()
            edit = EditableSchema(self)
            edit.insert("test0", "test1", Parameter("str"))

        @classmethod
        def _getdict_type(cls):
            return "NewSchema"

    schema = NewSchema()
    schema.set("test0", "test1", "testthis")

    with patch("siliconcompiler.schema.BaseSchema._BaseSchema__get_child_classes") as children:
        children.return_value = {
            "BaseSchema": BaseSchema,
            "NewSchema": NewSchema
        }
        new_schema = NewSchema.from_manifest(cfg=schema.getdict())

    assert new_schema.getdict() == schema.getdict()


def test_from_manifest_cfg_no_meta():
    class NewSchema(BaseSchema):
        def __init__(self):
            super().__init__()
            edit = EditableSchema(self)
            edit.insert("test0", "test1", Parameter("str"))

    schema = NewSchema()
    schema.set("test0", "test1", "testthis")

    new_schema = NewSchema.from_manifest(cfg={
        'test0': {
            'test1': {
                'type': 'str',
                'require': False,
                'scope': 'global',
                'lock': False,
                'switch': [],
                'shorthelp': None,
                'example': [],
                'help': None,
                'notes': None,
                'pernode': 'never',
                'node': {'global': {'global': {'value': 'testthis', 'signature': None}},
                         'default': {'default': {'value': None, 'signature': None}}}
            }
        }
    })

    assert new_schema.__class__ is NewSchema
    assert new_schema.getdict() == schema.getdict()


def test_from_manifest_cfg_different_base_correct_base_class():
    class NewSchema(BaseSchema):
        def __init__(self):
            super().__init__()
            edit = EditableSchema(self)
            edit.insert("test0", "test1", Parameter("str"))

        @classmethod
        def _getdict_type(cls):
            return "NewSchema"

    schema = NewSchema()
    schema.set("test0", "test1", "testthis")

    with patch("siliconcompiler.schema.BaseSchema._BaseSchema__get_child_classes") as children:
        children.return_value = {
            "BaseSchema": BaseSchema,
            "NewSchema": NewSchema
        }
        new_schema = BaseSchema.from_manifest(cfg={
            'test0': {
                'test1': {
                    'type': 'str',
                    'require': False,
                    'scope': 'global',
                    'lock': False,
                    'switch': [],
                    'shorthelp': None,
                    'example': [],
                    'help': None,
                    'notes': None,
                    'pernode': 'never',
                    'node': {'global': {'global': {'value': 'testthis', 'signature': None}},
                             'default': {'default': {'value': None, 'signature': None}}}
                }
            },
            '__meta__': {
                'class': 'test_baseschema/NewSchema',
                'sctype': 'NewSchema'
            }
        })

    assert new_schema.__class__ is NewSchema
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

    child = schema.get("test0", field='schema')

    child.set("test1", "newvalue")
    assert child.get("test1") == "newvalue"
    assert schema.get("test0", "test1") == "newvalue"


def test_getschema_invalid():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "test1", Parameter("str"))

    with pytest.raises(KeyError, match=r"\[test\] is not a valid keypath"):
        schema.get("test", field='schema')


def test_getschema_parameter():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "test1", Parameter("str"))

    with pytest.raises(ValueError, match=r"\[test0,test1\] is a complete keypath"):
        schema.get("test0", "test1", field='schema')


@pytest.mark.parametrize("error", (ValueError, RuntimeError, KeyError))
def test_forward_exception_with_key_get(error, monkeypatch):
    schema = BaseSchema()
    edit = EditableSchema(schema)
    param = Parameter("str")
    edit.insert("test0", "test1", param)

    def dummy_get(*args, **kwargs):
        raise error("this is an error from the param")
    monkeypatch.setattr(param, 'get', dummy_get)

    with pytest.raises(error,
                       match=r"error while accessing \[test0,test1\]: "
                             r"this is an error from the param"):
        schema.get("test0", "test1")


@pytest.mark.parametrize("error", (ValueError, RuntimeError, KeyError))
def test_forward_exception_with_key_set(error, monkeypatch):
    schema = BaseSchema()
    edit = EditableSchema(schema)
    param = Parameter("str")
    edit.insert("test0", "test1", param)

    def dummy_set(*args, **kwargs):
        raise error("this is an error from the param")
    monkeypatch.setattr(param, 'set', dummy_set)

    with pytest.raises(error,
                       match=r"error while setting \[test0,test1\]: "
                             r"this is an error from the param"):
        schema.set("test0", "test1", "value")


@pytest.mark.parametrize("error", (ValueError, RuntimeError, KeyError))
def test_forward_exception_with_key_add(error, monkeypatch):
    schema = BaseSchema()
    edit = EditableSchema(schema)
    param = Parameter("[str]")
    edit.insert("test0", "test1", param)

    def dummy_add(*args, **kwargs):
        raise error("this is an error from the param")
    monkeypatch.setattr(param, 'add', dummy_add)

    with pytest.raises(error,
                       match=r"error while adding to \[test0,test1\]: "
                             r"this is an error from the param"):
        schema.add("test0", "test1", "value")


@pytest.mark.parametrize("error", (ValueError, RuntimeError, KeyError))
def test_forward_exception_with_key_unset(error, monkeypatch):
    schema = BaseSchema()
    edit = EditableSchema(schema)
    param = Parameter("str")
    edit.insert("test0", "test1", param)

    def dummy_unset(*args, **kwargs):
        raise error("this is an error from the param")
    monkeypatch.setattr(param, 'unset', dummy_unset)

    with pytest.raises(error,
                       match=r"error while unsetting \[test0,test1\]: "
                             r"this is an error from the param"):
        schema.unset("test0", "test1")


def test_find_files_non_path():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    param = Parameter("str")
    edit.insert("var", param)

    with pytest.raises(TypeError, match=r"Cannot find files on \[var\], must be a path type"):
        schema.find_files("var")


def test_find_files_scalar_file():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    param = Parameter("file")
    edit.insert("file", param)

    with open("test.txt", "w") as f:
        f.write("test")

    assert schema.set("file", "test.txt")

    assert schema.find_files("file") == os.path.abspath("test.txt")


def test_find_files_scalar_dir():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    param = Parameter("dir")
    edit.insert("directory", param)

    os.makedirs("test", exist_ok=True)

    assert schema.set("directory", "test")

    assert schema.find_files("directory") == os.path.abspath("test")


def test_find_files_scalar_file_not_found():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    param = Parameter("file")
    edit.insert("file", param)

    assert schema.set("file", "test.txt")

    with pytest.raises(FileNotFoundError, match=r"Could not find \"test.txt\" \[file\]"):
        schema.find_files("file")


def test_find_files_scalar_dir_not_found():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    param = Parameter("dir")
    edit.insert("directory", param)

    assert schema.set("directory", "test")

    with pytest.raises(FileNotFoundError, match=r"Could not find \"test\" \[directory\]"):
        schema.find_files("directory")


def test_find_files_scalar_file_not_found_missing_ok():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    param = Parameter("file")
    edit.insert("file", param)

    assert schema.set("file", "test.txt")

    assert schema.find_files("file", missing_ok=True) is None


def test_find_files_scalar_dir_not_found_missing_ok():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    param = Parameter("dir")
    edit.insert("directory", param)

    assert schema.set("directory", "test")

    assert schema.find_files("directory", missing_ok=True) is None


def test_find_files_list_file():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    param = Parameter("[file]")
    edit.insert("file", param)

    with open("test0.txt", "w") as f:
        f.write("test")

    with open("test1.txt", "w") as f:
        f.write("test")

    assert schema.set("file", ["test0.txt", "test1.txt"])

    assert schema.find_files("file") == [
        os.path.abspath("test0.txt"),
        os.path.abspath("test1.txt")
    ]


def test_find_files_list_dir():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    param = Parameter("[dir]")
    edit.insert("directory", param)

    os.makedirs("test0", exist_ok=True)
    os.makedirs("test1", exist_ok=True)

    assert schema.set("directory", ["test0", "test1"])

    assert schema.find_files("directory") == [
        os.path.abspath("test0"),
        os.path.abspath("test1")
    ]


def test_find_files_list_file_not_found():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    param = Parameter("[file]")
    edit.insert("file", param)

    with open("test0.txt", "w") as f:
        f.write("test")

    assert schema.set("file", ["test0.txt", "test1.txt"])

    with pytest.raises(FileNotFoundError, match=r"Could not find \"test1.txt\" \[file\]"):
        schema.find_files("file")


def test_find_files_list_dir_not_found():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    param = Parameter("[dir]")
    edit.insert("directory", param)

    os.makedirs("test0", exist_ok=True)

    assert schema.set("directory", ["test0", "test1"])

    with pytest.raises(FileNotFoundError, match=r"Could not find \"test1\" \[directory\]"):
        schema.find_files("directory")


def test_find_files_list_file_not_found_missing_ok():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    param = Parameter("[file]")
    edit.insert("file", param)

    with open("test0.txt", "w") as f:
        f.write("test")

    assert schema.set("file", ["test0.txt", "test1.txt"])

    assert schema.find_files("file", missing_ok=True) == [
        os.path.abspath("test0.txt"),
        None
    ]


def test_find_files_list_dir_not_found_missing_ok():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    param = Parameter("[dir]")
    edit.insert("directory", param)

    os.makedirs("test0", exist_ok=True)

    assert schema.set("directory", ["test0", "test1"])

    assert schema.find_files("directory", missing_ok=True) == [
        os.path.abspath("test0"),
        None
    ]


def test_find_files_with_cwd():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    param = Parameter("[dir]")
    edit.insert("directory", param)

    os.makedirs("cwd/test0", exist_ok=True)
    os.makedirs("cwd/test1", exist_ok=True)

    assert schema.set("directory", ["test0", "test1"])

    assert schema.find_files("directory", cwd="./cwd") == [
        os.path.abspath("cwd/test0"),
        os.path.abspath("cwd/test1")
    ]


def test_find_files_with_package():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    param = Parameter("[file]")
    edit.insert("package", "file", param)

    os.makedirs("package_path", exist_ok=True)
    with open("package_path/test0.txt", "w") as f:
        f.write("test")

    with open("package_path/test1.txt", "w") as f:
        f.write("test")

    assert schema.set("package", "file", ["test0.txt", "test1.txt"])
    assert schema.set("package", "file", ["this_package", "this_package"], field="package")

    class Resolver:
        called = 0

        def resolve(self):
            self.called += 1
            return os.path.abspath("package_path")

    resolve0 = Resolver()
    resolve1 = Resolver()
    package_map = {
        "this_package": resolve0.resolve,
        "that_package": resolve1.resolve,
    }

    assert schema.find_files("package", "file", packages=package_map) == [
        os.path.abspath("package_path/test0.txt"),
        os.path.abspath("package_path/test1.txt"),
    ]

    assert resolve0.called == 2
    assert resolve1.called == 0


def test_find_files_with_package_not_found():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    param = Parameter("[file]")
    edit.insert("package", "file", param)

    os.makedirs("package_path", exist_ok=True)
    with open("package_path/test0.txt", "w") as f:
        f.write("test")

    assert schema.set("package", "file", ["test0.txt", "test1.txt"])
    assert schema.set("package", "file", ["this_package", "this_package"], field="package")

    class Resolver:
        called = 0

        def resolve(self):
            self.called += 1
            return os.path.abspath("package_path")

    resolve0 = Resolver()
    resolve1 = Resolver()
    package_map = {
        "this_package": resolve0.resolve,
        "that_package": resolve1.resolve,
    }

    with pytest.raises(FileNotFoundError,
                       match=r"Could not find \"test1.txt\" in this_package \[package,file\]"):
        schema.find_files("package", "file", packages=package_map)

    assert resolve0.called == 2
    assert resolve1.called == 0


def test_find_files_with_package_missing():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    param = Parameter("[file]")
    edit.insert("package", "file", param)

    os.makedirs("package_path", exist_ok=True)
    with open("package_path/test0.txt", "w") as f:
        f.write("test")

    assert schema.set("package", "file", ["test0.txt", "test1.txt"])
    assert schema.set("package", "file", ["this_package", "this_package"], field="package")

    with pytest.raises(ValueError, match=r"Resolver for this_package not provided"):
        schema.find_files("package", "file", packages={})


def test_find_files_with_package_as_string():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    param = Parameter("[file]")
    edit.insert("package", "file", param)

    os.makedirs("package_path", exist_ok=True)
    with open("package_path/test0.txt", "w") as f:
        f.write("test")

    with open("package_path/test1.txt", "w") as f:
        f.write("test")

    assert schema.set("package", "file", ["test0.txt", "test1.txt"])
    assert schema.set("package", "file", ["this_package", "that_package"], field="package")

    class Resolver:
        called = 0

        def resolve(self):
            self.called += 1
            return os.path.abspath("package_path")

    resolve = Resolver()
    package_map = {
        "this_package": "package_path",
        "that_package": resolve.resolve,
    }

    assert schema.find_files("package", "file", packages=package_map) == [
        os.path.abspath("package_path/test0.txt"),
        os.path.abspath("package_path/test1.txt"),
    ]

    assert resolve.called == 1


def test_find_files_with_package_as_invalid():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    param = Parameter("[file]")
    edit.insert("package", "file", param)

    os.makedirs("package_path", exist_ok=True)
    with open("package_path/test0.txt", "w") as f:
        f.write("test")

    assert schema.set("package", "file", "test0.txt")
    assert schema.set("package", "file", "this_package", field="package")

    package_map = {
        "this_package": 1
    }

    with pytest.raises(TypeError, match="Resolver for this_package is not a recognized type"):
        schema.find_files("package", "file", packages=package_map)


def test_find_files_with_collection_dir_not_found():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    param = Parameter("[file]")
    edit.insert("package", "file", param)

    with open("test.txt", "w") as f:
        f.write("test")

    assert schema.set("package", "file", "test.txt")

    assert schema.find_files("package", "file", collection_dir="nodirfound") == [
        os.path.abspath("test.txt")
    ]


def test_find_files_with_collection_dir():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    param = Parameter("[file]")
    edit.insert("package", "file", param)

    os.makedirs("collections_dir", exist_ok=True)

    with open("collections_dir/test_3a52ce780950d4d969792a2559cd519d7ee8c727.txt", "w") as f:
        f.write("test")

    assert schema.set("package", "file", "test.txt")

    assert schema.find_files("package", "file", collection_dir="collections_dir") == [
        os.path.abspath("collections_dir/test_3a52ce780950d4d969792a2559cd519d7ee8c727.txt")
    ]


def test_find_files_scalar_file_empty():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    param = Parameter("file")
    edit.insert("file", param)

    assert schema.find_files("file") is None


def test_find_files_scalar_dir_empty():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    param = Parameter("dir")
    edit.insert("directory", param)

    assert schema.find_files("directory") is None


def test_find_files_list_file_empty():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    param = Parameter("[file]")
    edit.insert("file", param)

    assert schema.find_files("file") == []


def test_find_files_list_dir_empty():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    param = Parameter("[dir]")
    edit.insert("directory", param)

    assert schema.find_files("directory") == []


def test_check_filepaths_empty():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    param = Parameter("[dir]")
    edit.insert("directory", param)

    assert schema.check_filepaths() is True


def test_check_filepaths_found():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    param = Parameter("[dir]")
    edit.insert("directory", param)

    os.makedirs("test0", exist_ok=True)

    assert schema.set("directory", "test0")

    assert schema.check_filepaths() is True


def test_check_filepaths_found_file():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    param = Parameter("[file]")
    edit.insert("file", param)

    with open("test0.txt", "w") as f:
        f.write("test")

    assert schema.set("file", "test0.txt")

    assert schema.check_filepaths() is True


def test_check_filepaths_scalar_found():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    param = Parameter("dir")
    edit.insert("directory", param)

    os.makedirs("test0", exist_ok=True)

    assert schema.set("directory", "test0")

    assert schema.check_filepaths() is True


def test_check_filepaths_with_non_path():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    param = Parameter("dir")
    edit.insert("directory", param)
    edit.insert("other", Parameter("str"))

    os.makedirs("test0", exist_ok=True)

    assert schema.set("directory", "test0")

    assert schema.check_filepaths() is True


def test_check_filepaths_not_found_no_logger():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    param = Parameter("[dir]")
    edit.insert("directory", param)

    assert schema.set("directory", "test0")

    assert schema.check_filepaths() is False


def test_check_filepaths_not_found_logger(caplog):
    schema = BaseSchema()
    edit = EditableSchema(schema)
    param = Parameter("[dir]")
    edit.insert("directory", param)

    assert schema.set("directory", "test0")

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    assert schema.check_filepaths(logger=logger) is False
    assert "Parameter [directory] path test0 is invalid" in caplog.text


def test_check_filepaths_not_found_logger_step_only(caplog):
    schema = BaseSchema()
    edit = EditableSchema(schema)
    param = Parameter("[dir]", pernode=PerNode.OPTIONAL)
    edit.insert("directory", param)

    assert schema.set("directory", "test0", step="thisstep")

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    assert schema.check_filepaths(logger=logger) is False
    assert "Parameter [directory] (thisstep) path test0 is invalid" in caplog.text


def test_check_filepaths_not_found_logger_step_index(caplog):
    schema = BaseSchema()
    edit = EditableSchema(schema)
    param = Parameter("[dir]", pernode=PerNode.OPTIONAL)
    edit.insert("directory", param)

    assert schema.set("directory", "test0", step="thisstep", index="0")

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    assert schema.check_filepaths(logger=logger) is False
    assert "Parameter [directory] (thisstep/0) path test0 is invalid" in caplog.text


def test_check_filepaths_not_found_ignored():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    param = Parameter("[dir]", pernode=PerNode.OPTIONAL)
    edit.insert("directory", param)

    assert schema.set("directory", "test0")

    assert schema.check_filepaths(ignore_keys=[("directory",)]) is True


def test_check_filepaths_not_found_ignored_list():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    param = Parameter("[dir]", pernode=PerNode.OPTIONAL)
    edit.insert("directory", param)

    assert schema.set("directory", "test0")

    assert schema.check_filepaths(ignore_keys=[["directory"]]) is True


def test_get_no_with_journal():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "test1", Parameter("str"))
    journal = Journal.access(schema)

    schema.set("test0", "test1", "hello")
    assert schema.get("test0", "test1") == "hello"
    assert journal.get() is None


def test_get_with_journal():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "test1", Parameter("str"))
    journal = Journal.access(schema)
    schema.set("test0", "test1", "hello")

    journal.start()
    journal.add_type("get")
    assert "get" in journal.get_types()

    assert journal.get() == []
    assert schema.get("test0", "test1") == "hello"
    assert journal.get() == [{
        "type": "get",
        "key": ("test0", "test1"),
        "value": None,
        "field": "value",
        "step": None,
        "index": None
    }]


def test_get_with_journal_schema():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "test1", Parameter("str"))
    journal = Journal.access(schema)
    schema.set("test0", "test1", "hello")

    journal.start()
    journal.add_type("get")
    assert "get" in journal.get_types()

    assert journal.get() == []
    child_schema = schema.get("test0", field="schema")
    assert Journal.access(child_schema).keypath == ("test0",)
    assert journal.get() == [{
        "type": "get",
        "key": ("test0",),
        "value": None,
        "field": "schema",
        "step": None,
        "index": None
    }]


def test_set_with_journal():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "test1", Parameter("str"))
    journal = Journal.access(schema)
    journal.start()

    schema.set("test0", "test1", "hello")
    assert journal.get() == [{
        "type": "set",
        "key": ("test0", "test1"),
        "value": "hello",
        "field": "value",
        "step": None,
        "index": None
    }]
    assert schema.get("test0", "test1") == "hello"


def test_getdict_with_journal():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "test1", Parameter("str"))
    journal = Journal.access(schema)
    journal.start()

    schema.set("test0", "test1", "hello")
    assert schema.getdict() == {
        '__journal__': [
            {
                'field': 'value',
                'index': None,
                'key': (
                    'test0',
                    'test1',
                ),
                'step': None,
                'type': 'set',
                'value': 'hello',
            },
        ],
        'test0': {
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
                    'global': {
                        'global': {
                            'signature': None,
                            'value': 'hello',
                        },
                    },
                },
                'notes': None,
                'pernode': 'never',
                'require': False,
                'scope': 'global',
                'shorthelp': None,
                'switch': [],
                'type': 'str',
            },
        },
    }


def test_getdict_with_journal_values_only():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "test1", Parameter("str"))
    journal = Journal.access(schema)
    journal.start()

    schema.set("test0", "test1", "hello")
    assert schema.getdict(values_only=True) == {
        'test0': {
            'test1': {
                None: {
                    None: 'hello',
                },
            },
        },
    }


def test_fromdict_with_journal():
    schema = BaseSchema()
    journal = Journal.access(schema)
    assert journal.get() is None

    assert schema._from_dict({
        '__journal__': [
            {
                'field': 'value',
                'index': None,
                'key': (
                    'test0',
                    'test1',
                ),
                'step': None,
                'type': 'set',
                'value': 'hello',
            },
        ]
    }, [], None)

    assert journal.get() == [
        {
            'field': 'value',
            'index': None,
            'key': (
                'test0',
                'test1',
            ),
            'step': None,
            'type': 'set',
            'value': 'hello',
        }
    ]


def test_parent():
    schema = BaseSchema()
    assert schema._parent() is schema


def test_parent_with_child():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "test1", "test2", Parameter("str"))

    assert schema._parent() is schema
    assert schema._parent(root=True) is schema
    assert schema.get("test0", field="schema")._parent(root=True) is schema
    assert schema.get("test0", "test1", field="schema")._parent(root=True) is schema


def test_active_empty():
    schema = BaseSchema()

    assert schema._get_active(None) is None
    with schema._active():
        assert schema._get_active(None) == {}
    assert schema._get_active(None) is None


def test_active_defvalue():
    schema = BaseSchema()

    assert schema._get_active(None, 1) == 1
    with schema._active(fileset="rtl"):
        assert schema._get_active("fileset") == "rtl"
        assert schema._get_active("notvalid", "testbench") == "testbench"
    assert schema._get_active(None) is None


def test_active_package():
    schema = BaseSchema()

    assert schema._get_active(None) is None
    with schema._active(package="testpack"):
        assert schema._get_active(None) == {
            "package": "testpack"
        }
        assert schema._get_active("package") == "testpack"
    assert schema._get_active(None) is None


def test_active_invalid_active():
    schema = BaseSchema()

    assert schema._get_active(None) is None
    with schema._active(package="testpack"):
        assert schema._get_active("package0") is None
    assert schema._get_active(None) is None


def test_active_compounded():
    schema = BaseSchema()

    assert schema._get_active(None) is None
    with schema._active(package="testpack"):
        assert schema._get_active(None) == {
            "package": "testpack"
        }

        with schema._active(lock=True):
            assert schema._get_active(None) == {
                "package": "testpack",
                "lock": True
            }
            with schema._active(lock=False):
                assert schema._get_active(None) == {
                    "package": "testpack",
                    "lock": False
                }
            assert schema._get_active(None) == {
                "package": "testpack",
                "lock": True
            }
        assert schema._get_active(None) == {
            "package": "testpack"
        }

    assert schema._get_active(None) is None


def test_active_compounded_set():
    schema = BaseSchema()
    EditableSchema(schema).insert("teststr", Parameter("str"))
    EditableSchema(schema).insert("testfile", Parameter("file"))
    EditableSchema(schema).insert("testdir", Parameter("[dir]"))

    with schema._active(package="testpack"):
        assert schema.set("teststr", "thisstring")
        assert schema.get("teststr") == "thisstring"

        assert schema.set("testfile", "thisfile")
        assert schema.get("testfile") == "thisfile"
        assert schema.get("testfile", field="package") == "testpack"

        assert schema.set("testdir", "thisdir")
        assert schema.get("testdir") == ["thisdir"]
        assert schema.get("testdir", field="package") == ["testpack"]

        with schema._active(lock=True):
            assert schema.set("teststr", "thisnewstring")
            assert schema.get("teststr") == "thisnewstring"
            assert schema.get("teststr", field="lock") is True


def test_active_add():
    schema = BaseSchema()
    EditableSchema(schema).insert("teststr", Parameter("[str]"))
    EditableSchema(schema).insert("testdir", Parameter("[dir]"))

    with schema._active(package="testpack"):
        assert schema.add("teststr", "thisstring0")
        assert schema.get("teststr") == ["thisstring0"]

        assert schema.add("teststr", "thisstring1")
        assert schema.get("teststr") == ["thisstring0", "thisstring1"]

        assert schema.add("testdir", "thisdir0")
        assert schema.get("testdir") == ["thisdir0"]
        assert schema.get("testdir", field="package") == ["testpack"]

        with schema._active(package="anotherpack"):
            assert schema.add("testdir", "thisdir1")
            assert schema.get("testdir") == ["thisdir0", "thisdir1"]
            assert schema.get("testdir", field="package") == [
                "testpack",
                "anotherpack"]


def test_active_set_field():
    schema = BaseSchema()
    EditableSchema(schema).insert("teststr", Parameter("[str]"))
    EditableSchema(schema).insert("testdir", Parameter("[dir]"))

    with schema._active(package="testpack"):
        assert schema.add("teststr", "thisstring0")
        assert schema.set("teststr", True, field="lock")


def test_find_files_custom_class_search_paths():
    class CustomFiles(BaseSchema):
        def __init__(self):
            super().__init__()
            EditableSchema(self).insert("rootedfile", Parameter("file"))
            EditableSchema(self).insert("unrootedfile", Parameter("file"))

        def _find_files_search_paths(self, keypath, step, index):
            paths = super()._find_files_search_paths(keypath, step, index)
            if keypath == "rootedfile":
                paths.append(os.path.abspath("thisroot"))
            return paths

    os.makedirs("thisroot", exist_ok=True)
    with open("thisroot/thisfile.txt", "w") as f:
        f.write("test")
    with open("thatfile.txt", "w") as f:
        f.write("test")

    schema = CustomFiles()
    schema.set("rootedfile", "thisfile.txt")
    schema.set("unrootedfile", "thatfile.txt")

    assert schema.find_files("rootedfile") == os.path.abspath("thisroot/thisfile.txt")
    assert schema.find_files("unrootedfile") == os.path.abspath("thatfile.txt")


def test_find_files_custom_class_package_resolution():
    class CustomFiles(BaseSchema):
        def __init__(self):
            super().__init__()
            EditableSchema(self).insert("level0", "rootedfile", Parameter("file"))
            EditableSchema(self).insert("level0", "level1", "unrootedfile", Parameter("file"))
            self.calls = 0

        def _find_files_dataroot_resolvers(self):
            self.calls += 1
            return {
                "thispackage": os.path.abspath("thisroot")
            }

    os.makedirs("thisroot", exist_ok=True)
    with open("thisroot/thisfile.txt", "w") as f:
        f.write("test")
    with open("thisroot/thatfile.txt", "w") as f:
        f.write("test")

    custom = CustomFiles()
    schema = BaseSchema()
    EditableSchema(schema).insert("level-1", custom)
    with schema._active(package="thispackage"):
        assert schema.set("level-1", "level0", "rootedfile", "thisfile.txt")
        assert schema.set("level-1", "level0", "level1", "unrootedfile", "thatfile.txt")

    assert custom.calls == 0

    assert schema.find_files("level-1", "level0", "rootedfile") == \
        os.path.abspath("thisroot/thisfile.txt")
    assert custom.calls == 1

    assert schema.find_files("level-1", "level0", "level1", "unrootedfile") == \
        os.path.abspath("thisroot/thatfile.txt")
    assert custom.calls == 2


def test_keypath_root():
    assert BaseSchema()._keypath == tuple()


def test_keypath_with_levels():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "test1", "test2", Parameter("str"))
    assert schema._keypath == tuple()
    assert schema.get("test0", field="schema")._keypath == ("test0",)
    assert schema.get("test0", "test1", field="schema")._keypath == ("test0", "test1")


def test_keypath_with_default_unset():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("default", "test1", "test2", Parameter("str"))
    assert schema._keypath == tuple()
    assert schema.get("default", field="schema")._keypath == ("default",)
    assert schema.get("test0", field="schema")._keypath == ("test0",)
    assert schema.get("test0", "test1", field="schema")._keypath == ("test0", "test1")

    assert schema.set("test0", "test1", "test2", "test")
    assert schema.get("test0", field="schema")._keypath == ("test0",)
    assert schema.get("test0", "test1", field="schema")._keypath == ("test0", "test1")


def test_keypath_with_default_set():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("default", "test1", "test2", Parameter("str"))
    assert schema.set("test0", "test1", "test2", "test")
    assert schema.set("test3", "test1", "test2", "test")

    assert schema._keypath == tuple()
    assert schema.get("test0", field="schema")._keypath == ("test0",)
    assert schema.get("test0", "test1", field="schema")._keypath == ("test0", "test1")
    assert schema.get("test3", field="schema")._keypath == ("test3",)
    assert schema.get("test3", "test1", field="schema")._keypath == ("test3", "test1")


def test_keypath_with_default_schema_access():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "default", "test1", "test2", Parameter("str"))

    assert schema._keypath == tuple()
    assert schema.get("test0", field="schema")._keypath == ("test0",)
    assert schema.get("test0", "default", field="schema")._keypath == ("test0", "default")
    assert schema.get("test0", "test1", field="schema")._keypath == ("test0", "test1")
    assert schema.get("test0", "test1", "test1", field="schema")._keypath == \
        ("test0", "test1", "test1")


def test_getdict_type():
    assert BaseSchema._getdict_type() == "BaseSchema"


def test_from_dict_composite_type_names():
    class DummySchema(BaseSchema):
        def __init__(self):
            super().__init__()

            EditableSchema(self).insert("string", Parameter("str"))

        @classmethod
        def _getdict_type(cls):
            return "dummy_schema"

    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("dummy", "default", BaseSchema())
    edit.insert("base", "default", Parameter("str"))

    with patch("siliconcompiler.schema.BaseSchema._BaseSchema__get_child_classes") as children, \
            patch("siliconcompiler.schema.BaseSchema._BaseSchema__load_schema_class") as \
            load_schema_class:
        children.return_value = {
            "BaseSchema": BaseSchema,
            "dummy_schema": DummySchema
        }
        schema._from_dict({
            'dummy': {
                'default': {},
                'newdummy': {  # this has a different type than the default
                    'string': {
                        'type': 'str',
                        'require': False,
                        'scope': 'global',
                        'lock': False,
                        'switch': [],
                        'shorthelp': None,
                        'example': [],
                        'help': None,
                        'notes': None,
                        'pernode': 'never',
                        'node': {'global': {'global': {'value': 'teststring', 'signature': None}},
                                 'default': {'default': {'value': None, 'signature': None}}}
                    },
                    '__meta__': {
                        'sctype': 'dummy_schema'
                    }
                }
            },
            'base': {
                'default': {
                    'type': 'str',
                    'require': False,
                    'scope': 'global',
                    'lock': False,
                    'switch': [],
                    'shorthelp': None,
                    'example': [],
                    'help': None,
                    'notes': None,
                    'pernode': 'never',
                    'node': {'default': {'default': {'value': None, 'signature': None}}}
                },
                'newbase': {
                    'type': 'str',
                    'require': False,
                    'scope': 'global',
                    'lock': False,
                    'switch': [],
                    'shorthelp': None,
                    'example': [],
                    'help': None,
                    'notes': None,
                    'pernode': 'never',
                    'node': {'global': {'global': {'value': 'teststring', 'signature': None}},
                             'default': {'default': {'value': None, 'signature': None}}}
                }
            }
        }, [])
        children.assert_called_once()
        load_schema_class.assert_not_called()

    assert schema.get("dummy", "default", field="schema").__class__ is BaseSchema
    assert schema.get("dummy", "newdummy", field="schema").__class__ is DummySchema
    assert schema.get("base", "default", field=None).__class__ is Parameter
    assert schema.get("base", "newbase", field=None).__class__ is Parameter

    assert schema.get("dummy", "newdummy", field="schema")._keypath == \
        ("dummy", "newdummy")
    assert schema.get("dummy", "default", field="schema")._keypath == \
        ("dummy", "default")

    assert schema.get("dummy", "newdummy", "string") == "teststring"
    assert schema.get("base", "newbase", "string") == "teststring"


def test_from_dict_composite_nested():
    class LowSchema(BaseSchema):
        def __init__(self):
            super().__init__()

            EditableSchema(self).insert("string", Parameter("str"))

        @classmethod
        def _getdict_type(cls):
            return "low_schema"

    class ImplLowSchema(LowSchema):
        @classmethod
        def _getdict_type(cls):
            return "impl_low_schema"

    class DummySchema(BaseSchema):
        def __init__(self):
            super().__init__()

            EditableSchema(self).insert("test0", "default", LowSchema())

        @classmethod
        def _getdict_type(cls):
            return "dummy_schema"

    class ImplDummySchema(DummySchema):
        @classmethod
        def _getdict_type(cls):
            return "impl_dummy_schema"

    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("dummy", "default", DummySchema())

    with patch("siliconcompiler.schema.BaseSchema._BaseSchema__get_child_classes") as children, \
            patch("siliconcompiler.schema.BaseSchema._BaseSchema__load_schema_class") as \
            load_schema_class:
        children.return_value = {
            "BaseSchema": BaseSchema,
            "dummy_schema": DummySchema,
            "impl_dummy_schema": ImplDummySchema,
            "low_schema": LowSchema,
            "impl_low_schema": ImplLowSchema
        }
        schema._from_dict({
            'dummy': {
                'newdummy': {
                    'test0': {
                        'newlow': {
                            'string': {
                                'type': 'str',
                                'require': False,
                                'scope': 'global',
                                'lock': False,
                                'switch': [],
                                'shorthelp': None,
                                'example': [],
                                'help': None,
                                'notes': None,
                                'pernode': 'never',
                                'node': {'global': {'global': {'value': 'teststring',
                                                               'signature': None}},
                                         'default': {'default': {'value': None, 'signature': None}}}
                            },
                            '__meta__': {
                                'sctype': 'impl_low_schema'
                            }
                        }
                    },
                    '__meta__': {
                        'sctype': 'impl_dummy_schema'
                    }
                }
            }
        }, [])
        assert children.call_count == 2
        load_schema_class.assert_not_called()

    assert schema.get("dummy", "default", field="schema").__class__ is DummySchema
    assert schema.get("dummy", "newdummy", field="schema").__class__ is ImplDummySchema
    assert schema.get("dummy", "newdummy", "test0", field="schema").__class__ is BaseSchema
    assert schema.get("dummy", "newdummy", "test0", "newlow", field="schema").__class__ is \
        ImplLowSchema
    assert schema.get("dummy", "newdummy", "test0", "newlow", "string", field=None).__class__ is \
        Parameter

    assert schema.get("dummy", "newdummy", "test0", "newlow", field="schema")._keypath == \
        ("dummy", "newdummy", "test0", "newlow")

    assert schema.get("dummy", "newdummy", "test0", "newlow", "string") == "teststring"


def test_from_dict_composite_type_names_use_default():
    class DummySchema(BaseSchema):
        def __init__(self):
            super().__init__()

            EditableSchema(self).insert("string", Parameter("str"))

        @classmethod
        def _getdict_type(cls):
            return "dummy_schema"

    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("dummy", "default", DummySchema())
    edit.insert("base", "default", Parameter("str"))

    with patch("siliconcompiler.schema.BaseSchema._BaseSchema__get_child_classes") as children, \
            patch("siliconcompiler.schema.BaseSchema._BaseSchema__load_schema_class") as \
            load_schema_class:
        children.return_value = {
            "BaseSchema": BaseSchema,
            "dummy_schema": DummySchema
        }
        schema._from_dict({
            'dummy': {
                'newdummy': {  # this has a different type than the default
                    'string': {
                        'type': 'str',
                        'require': False,
                        'scope': 'global',
                        'lock': False,
                        'switch': [],
                        'shorthelp': None,
                        'example': [],
                        'help': None,
                        'notes': None,
                        'pernode': 'never',
                        'node': {'global': {'global': {'value': 'teststring', 'signature': None}},
                                 'default': {'default': {'value': None, 'signature': None}}}
                    },
                    '__meta__': {
                        'sctype': 'BaseSchema'
                    }
                }
            },
            'base': {
                'default': {
                    'type': 'str',
                    'require': False,
                    'scope': 'global',
                    'lock': False,
                    'switch': [],
                    'shorthelp': None,
                    'example': [],
                    'help': None,
                    'notes': None,
                    'pernode': 'never',
                    'node': {'default': {'default': {'value': None, 'signature': None}}}
                },
                'newbase': {
                    'type': 'str',
                    'require': False,
                    'scope': 'global',
                    'lock': False,
                    'switch': [],
                    'shorthelp': None,
                    'example': [],
                    'help': None,
                    'notes': None,
                    'pernode': 'never',
                    'node': {'global': {'global': {'value': 'teststring', 'signature': None}},
                             'default': {'default': {'value': None, 'signature': None}}}
                }
            }
        }, [])
        children.assert_called_once()
        load_schema_class.assert_not_called()

    assert schema.get("dummy", "default", field="schema").__class__ is DummySchema
    assert schema.get("dummy", "newdummy", field="schema").__class__ is DummySchema
    assert schema.get("base", "default", field=None).__class__ is Parameter
    assert schema.get("base", "newbase", field=None).__class__ is Parameter

    assert schema.get("dummy", "newdummy", field="schema")._keypath == \
        ("dummy", "newdummy")
    assert schema.get("dummy", "default", field="schema")._keypath == \
        ("dummy", "default")

    assert schema.get("dummy", "newdummy", "string") == "teststring"
    assert schema.get("base", "newbase", "string") == "teststring"


def test_from_dict_composite_type_load_via_class_name():
    class DummySchema(BaseSchema):
        def __init__(self):
            super().__init__()

            EditableSchema(self).insert("string", Parameter("str"))

        @classmethod
        def _getdict_type(cls):
            return "dummy_schema"

    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("dummy", "default", BaseSchema())
    edit.insert("base", "default", Parameter("str"))

    with patch("siliconcompiler.schema.BaseSchema._BaseSchema__get_child_classes") as children, \
            patch("siliconcompiler.schema.BaseSchema._BaseSchema__load_schema_class") as \
            load_schema_class:
        children.return_value = {
            "BaseSchema": BaseSchema,
            "dummy_schema": DummySchema
        }
        load_schema_class.return_value = DummySchema
        schema._from_dict({
            'dummy': {
                'default': {},
                'newdummy': {  # this has a different type than the default
                    'string': {
                        'type': 'str',
                        'require': False,
                        'scope': 'global',
                        'lock': False,
                        'switch': [],
                        'shorthelp': None,
                        'example': [],
                        'help': None,
                        'notes': None,
                        'pernode': 'never',
                        'node': {'global': {'global': {'value': 'teststring', 'signature': None}},
                                 'default': {'default': {'value': None, 'signature': None}}}
                    },
                    '__meta__': {
                        'class': 'test/DummySchema', 'sctype': 'dummy_schema'
                    }
                }
            },
            'base': {
                'default': {
                    'type': 'str',
                    'require': False,
                    'scope': 'global',
                    'lock': False,
                    'switch': [],
                    'shorthelp': None,
                    'example': [],
                    'help': None,
                    'notes': None,
                    'pernode': 'never',
                    'node': {'default': {'default': {'value': None, 'signature': None}}}
                },
                'newbase': {
                    'type': 'str',
                    'require': False,
                    'scope': 'global',
                    'lock': False,
                    'switch': [],
                    'shorthelp': None,
                    'example': [],
                    'help': None,
                    'notes': None,
                    'pernode': 'never',
                    'node': {'global': {'global': {'value': 'teststring', 'signature': None}},
                             'default': {'default': {'value': None, 'signature': None}}}
                }
            }
        }, [])
        children.assert_called_once()
        load_schema_class.assert_called_once_with("test/DummySchema")

    assert schema.get("dummy", "default", field="schema").__class__ is BaseSchema
    assert schema.get("dummy", "newdummy", field="schema").__class__ is DummySchema
    assert schema.get("base", "default", field=None).__class__ is Parameter
    assert schema.get("base", "newbase", field=None).__class__ is Parameter

    assert schema.get("dummy", "newdummy", field="schema")._keypath == \
        ("dummy", "newdummy")
    assert schema.get("dummy", "default", field="schema")._keypath == \
        ("dummy", "default")

    assert schema.get("dummy", "newdummy", "string") == "teststring"
    assert schema.get("base", "newbase", "string") == "teststring"


def test_from_dict_composite_using_cls_name():
    class DummySchema(BaseSchema):
        def __init__(self):
            super().__init__()

            EditableSchema(self).insert("string", Parameter("str"))

        @classmethod
        def _getdict_type(cls):
            return "dummy_schema"

    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("dummy", "default", BaseSchema())
    edit.insert("base", "default", Parameter("str"))

    with patch("siliconcompiler.schema.BaseSchema._BaseSchema__get_child_classes") as children, \
            patch("siliconcompiler.schema.BaseSchema._BaseSchema__load_schema_class") as \
            load_schema_class:
        children.return_value = {
            "siliconcompiler.schema.baseschema/BaseSchema": BaseSchema,
            "test/DummySchema": DummySchema
        }
        schema._from_dict({
            'dummy': {
                'default': {},
                'newdummy': {  # this has a different type than the default
                    'string': {
                        'type': 'str',
                        'require': False,
                        'scope': 'global',
                        'lock': False,
                        'switch': [],
                        'shorthelp': None,
                        'example': [],
                        'help': None,
                        'notes': None,
                        'pernode': 'never',
                        'node': {'global': {'global': {'value': 'teststring', 'signature': None}},
                                 'default': {'default': {'value': None, 'signature': None}}}
                    },
                    '__meta__': {
                        'class': 'test/DummySchema', 'sctype': 'dummy_schema'
                    }
                }
            },
            'base': {
                'default': {
                    'type': 'str',
                    'require': False,
                    'scope': 'global',
                    'lock': False,
                    'switch': [],
                    'shorthelp': None,
                    'example': [],
                    'help': None,
                    'notes': None,
                    'pernode': 'never',
                    'node': {'default': {'default': {'value': None, 'signature': None}}}
                },
                'newbase': {
                    'type': 'str',
                    'require': False,
                    'scope': 'global',
                    'lock': False,
                    'switch': [],
                    'shorthelp': None,
                    'example': [],
                    'help': None,
                    'notes': None,
                    'pernode': 'never',
                    'node': {'global': {'global': {'value': 'teststring', 'signature': None}},
                             'default': {'default': {'value': None, 'signature': None}}}
                }
            }
        }, [])
        children.assert_called_once()
        load_schema_class.assert_not_called()

    assert schema.get("dummy", "default", field="schema").__class__ is BaseSchema
    assert schema.get("dummy", "newdummy", field="schema").__class__ is DummySchema
    assert schema.get("base", "default", field=None).__class__ is Parameter
    assert schema.get("base", "newbase", field=None).__class__ is Parameter

    assert schema.get("dummy", "newdummy", field="schema")._keypath == \
        ("dummy", "newdummy")
    assert schema.get("dummy", "default", field="schema")._keypath == \
        ("dummy", "default")

    assert schema.get("dummy", "newdummy", "string") == "teststring"
    assert schema.get("base", "newbase", "string") == "teststring"


def test_from_dict_composite_no_meta():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("dummy", "default", Parameter("str"))
    edit.insert("base", "default", Parameter("str"))

    with patch("siliconcompiler.schema.BaseSchema._BaseSchema__get_child_classes") as children, \
            patch("siliconcompiler.schema.BaseSchema._BaseSchema__load_schema_class") as \
            load_schema_class:
        schema._from_dict({
            'dummy': {
                'newdummy': {
                    'type': 'str',
                    'require': False,
                    'scope': 'global',
                    'lock': False,
                    'switch': [],
                    'shorthelp': None,
                    'example': [],
                    'help': None,
                    'notes': None,
                    'pernode': 'never',
                    'node': {'global': {'global': {'value': 'teststring', 'signature': None}},
                             'default': {'default': {'value': None, 'signature': None}}}
                }
            },
            'base': {
                'newbase': {
                    'type': 'str',
                    'require': False,
                    'scope': 'global',
                    'lock': False,
                    'switch': [],
                    'shorthelp': None,
                    'example': [],
                    'help': None,
                    'notes': None,
                    'pernode': 'never',
                    'node': {'global': {'global': {'value': 'teststring', 'signature': None}},
                             'default': {'default': {'value': None, 'signature': None}}}
                }
            }
        }, [])
        children.assert_not_called()
        load_schema_class.assert_not_called()

    assert schema.get("dummy", field="schema").__class__ is BaseSchema
    assert schema.get("dummy", "default", field=None).__class__ is Parameter
    assert schema.get("dummy", "newdummy", field=None).__class__ is Parameter
    assert schema.get("base", field="schema"), BaseSchema
    assert schema.get("base", "default", field=None).__class__ is Parameter
    assert schema.get("base", "newbase", field=None).__class__ is Parameter

    assert schema.get("dummy", "newdummy") == "teststring"
    assert schema.get("base", "newbase") == "teststring"


def test___get_child_classes_invalid_child(monkeypatch):
    class DummySchema0(BaseSchema):
        def __init__(self):
            super().__init__()

        @classmethod
        def _getdict_type(cls):
            return "dummy_schema"

    class DummySchema1(BaseSchema):
        def __init__(self):
            super().__init__()

        @classmethod
        def _getdict_type(cls):
            return "dummy_schema"

    monkeypatch.setattr(DummySchema0, "__subclasses__", lambda: [])
    monkeypatch.setattr(DummySchema1, "__subclasses__", lambda: [])

    with patch("siliconcompiler.schema.BaseSchema.__subclasses__") as subclasses:
        subclasses.return_value = set([DummySchema0, DummySchema1])

        with pytest.raises(RuntimeError, match="fatal error at: dummy_schema"):
            BaseSchema._BaseSchema__get_child_classes.cache_clear()
            BaseSchema._BaseSchema__get_child_classes()
        subclasses.assert_called_once()


def test___get_child_classes_valid(monkeypatch):
    class DummySchema0(BaseSchema):
        def __init__(self):
            super().__init__()

    class DummySchema1(BaseSchema):
        def __init__(self):
            super().__init__()

    monkeypatch.setattr(DummySchema0, "__subclasses__", lambda: [])
    monkeypatch.setattr(DummySchema1, "__subclasses__", lambda: [])

    with patch("siliconcompiler.schema.BaseSchema.__subclasses__") as subclasses:
        subclasses.return_value = set([DummySchema0, DummySchema1])

        BaseSchema._BaseSchema__get_child_classes.cache_clear()
        assert BaseSchema._BaseSchema__get_child_classes() == {
            "BaseSchema": BaseSchema,
            "siliconcompiler.schema.baseschema/BaseSchema": BaseSchema,
            "test_baseschema/DummySchema0": DummySchema0,
            "test_baseschema/DummySchema1": DummySchema1,
        }
        assert BaseSchema._BaseSchema__get_child_classes() == {
            "BaseSchema": BaseSchema,
            "siliconcompiler.schema.baseschema/BaseSchema": BaseSchema,
            "test_baseschema/DummySchema0": DummySchema0,
            "test_baseschema/DummySchema1": DummySchema1,
        }
        subclasses.assert_called_once()


@pytest.mark.parametrize("clsname", ["notvalid", None, 1, 8.5])
def test___load_schema_class_invalid_name(clsname):
    BaseSchema._BaseSchema__load_schema_class.cache_clear()
    assert BaseSchema._BaseSchema__load_schema_class(clsname) is None


@pytest.mark.parametrize("error", [ImportError, ModuleNotFoundError, SyntaxError])
def test___load_schema_class_reject_import_fails(error):
    with patch("importlib.import_module") as import_module:
        def raises(*args, **kwargs):
            raise error
        import_module.side_effect = raises

        BaseSchema._BaseSchema__load_schema_class.cache_clear()
        assert BaseSchema._BaseSchema__load_schema_class("test/Class") is None
        import_module.assert_called_once()


@pytest.mark.parametrize("error", [ZeroDivisionError, NotImplementedError])
def test___load_schema_class_forward_import_fails(error):
    with patch("importlib.import_module") as import_module:
        def raises(*args, **kwargs):
            raise error("match this")
        import_module.side_effect = raises

        BaseSchema._BaseSchema__load_schema_class.cache_clear()
        with pytest.raises(error, match="match this"):
            BaseSchema._BaseSchema__load_schema_class("test/Class")
        import_module.assert_called_once()


def test___load_schema_class_class_not_found():
    class Test:
        pass

    with patch("importlib.import_module") as import_module:
        import_module.return_value = Test

        BaseSchema._BaseSchema__load_schema_class.cache_clear()
        assert BaseSchema._BaseSchema__load_schema_class("test/Class") is None
        import_module.assert_called_once_with("test")


def test___load_schema_class_class_invalid_class_type():
    class Test:
        class Class:
            pass

    with patch("importlib.import_module") as import_module:
        import_module.return_value = Test

        BaseSchema._BaseSchema__load_schema_class.cache_clear()
        with pytest.raises(TypeError, match="Class must be a BaseSchema type"):
            BaseSchema._BaseSchema__load_schema_class("test/Class")
        import_module.assert_called_once_with("test")


def test___load_schema_class():
    class Test:
        class Class(BaseSchema):
            pass

    with patch("importlib.import_module") as import_module:
        import_module.return_value = Test

        BaseSchema._BaseSchema__load_schema_class.cache_clear()
        assert BaseSchema._BaseSchema__load_schema_class("test/Class") is Test.Class
        import_module.assert_called_once_with("test")


def test_read_manifest_file():
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

    new_schema = NewSchema()

    assert new_schema.getdict() != schema.getdict()
    new_schema.read_manifest(filepath="test.json.gz")
    assert new_schema.getdict() == schema.getdict()


def test_hash_files_non_path():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    param = Parameter("str")
    edit.insert("var", param)

    with pytest.raises(TypeError, match=r"Cannot find files on \[var\], must be a path type"):
        schema.hash_files("var")


def test_hash_files_scalar_file():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    param = Parameter("file")
    edit.insert("file", param)

    with open("test.txt", "w") as f:
        f.write("test")

    assert schema.set("file", "test.txt")

    assert schema.hash_files("file") == \
        "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"


def test_hash_files_scalar_dir():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    param = Parameter("dir")
    edit.insert("directory", param)

    os.makedirs("test", exist_ok=True)
    Path("test/file").touch()

    assert schema.set("directory", "test")

    assert schema.hash_files("directory") == \
        "3b9c358f36f0a31b6ad3e14f309c7cf198ac9246e8316f9ce543d5b19ac02b80"


def test_hash_files_scalar_file_not_found():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    param = Parameter("file")
    edit.insert("file", param)

    assert schema.set("file", "test.txt")

    with pytest.raises(FileNotFoundError, match=r"Could not find \"test.txt\" \[file\]"):
        schema.hash_files("file")


def test_hash_files_scalar_dir_not_found():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    param = Parameter("dir")
    edit.insert("directory", param)

    assert schema.set("directory", "test")

    with pytest.raises(FileNotFoundError, match=r"Could not find \"test\" \[directory\]"):
        schema.hash_files("directory")


def test_hash_files_scalar_file_not_found_missing_ok():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    param = Parameter("file")
    edit.insert("file", param)

    assert schema.set("file", "test.txt")

    assert schema.hash_files("file", missing_ok=True) is None


def test_hash_files_scalar_dir_not_found_missing_ok():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    param = Parameter("dir")
    edit.insert("directory", param)

    assert schema.set("directory", "test")

    assert schema.hash_files("directory", missing_ok=True) is None


def test_hash_files_list_file():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    param = Parameter("[file]")
    edit.insert("file", param)

    with open("test0.txt", "w") as f:
        f.write("test")

    with open("test1.txt", "w") as f:
        f.write("test")

    assert schema.set("file", ["test0.txt", "test1.txt"])

    assert schema.hash_files("file") == [
        "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
        "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"
    ]


def test_hash_files_list_dir():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    param = Parameter("[dir]")
    edit.insert("directory", param)

    os.makedirs("test0", exist_ok=True)
    os.makedirs("test1", exist_ok=True)
    Path("test0/test0").touch()
    Path("test1/test1").touch()

    assert schema.set("directory", ["test0", "test1"])

    assert schema.hash_files("directory") == [
        "590c9f8430c7435807df8ba9a476e3f1295d46ef210f6efae2043a4c085a569e",
        "1b4f0e9851971998e732078544c96b36c3d01cedf7caa332359d6f1d83567014"
    ]


def test_hash_files_list_file_not_found():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    param = Parameter("[file]")
    edit.insert("file", param)

    with open("test0.txt", "w") as f:
        f.write("test")

    assert schema.set("file", ["test0.txt", "test1.txt"])

    with pytest.raises(FileNotFoundError, match=r"Could not find \"test1.txt\" \[file\]"):
        schema.hash_files("file")


def test_hash_files_list_dir_not_found():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    param = Parameter("[dir]")
    edit.insert("directory", param)

    os.makedirs("test0", exist_ok=True)

    assert schema.set("directory", ["test0", "test1"])

    with pytest.raises(FileNotFoundError, match=r"Could not find \"test1\" \[directory\]"):
        schema.hash_files("directory")


def test_hash_files_list_file_not_found_missing_ok():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    param = Parameter("[file]")
    edit.insert("file", param)

    with open("test0.txt", "w") as f:
        f.write("test")

    assert schema.set("file", ["test0.txt", "test1.txt"])

    assert schema.hash_files("file", missing_ok=True) == [
        "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
        None
    ]


def test_hash_files_list_dir_not_found_missing_ok():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    param = Parameter("[dir]")
    edit.insert("directory", param)

    os.makedirs("test0", exist_ok=True)
    Path("test0/test").touch()

    assert schema.set("directory", ["test0", "test1"])

    assert schema.hash_files("directory", missing_ok=True) == [
        "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
        None
    ]


def test_hash_files_with_cwd():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    param = Parameter("[dir]")
    edit.insert("directory", param)

    os.makedirs("cwd/test0", exist_ok=True)
    os.makedirs("cwd/test1", exist_ok=True)

    Path("cwd/test0/test").touch()

    assert schema.set("directory", ["test0", "test1"])

    assert schema.hash_files("directory", cwd="./cwd") == [
        "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
        None
    ]


def test_hash_files_with_package():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    param = Parameter("[file]")
    edit.insert("package", "file", param)

    os.makedirs("package_path", exist_ok=True)
    with open("package_path/test0.txt", "w") as f:
        f.write("test")

    with open("package_path/test1.txt", "w") as f:
        f.write("test")

    assert schema.set("package", "file", ["test0.txt", "test1.txt"])
    assert schema.set("package", "file", ["this_package", "this_package"], field="package")

    class Resolver:
        called = 0

        def resolve(self):
            self.called += 1
            return os.path.abspath("package_path")

    resolve0 = Resolver()
    resolve1 = Resolver()
    package_map = {
        "this_package": resolve0.resolve,
        "that_package": resolve1.resolve,
    }

    assert schema.hash_files("package", "file", packages=package_map) == [
        "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
        "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"
    ]

    assert resolve0.called == 2
    assert resolve1.called == 0


def test_hash_files_with_package_not_found():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    param = Parameter("[file]")
    edit.insert("package", "file", param)

    os.makedirs("package_path", exist_ok=True)
    with open("package_path/test0.txt", "w") as f:
        f.write("test")

    assert schema.set("package", "file", ["test0.txt", "test1.txt"])
    assert schema.set("package", "file", ["this_package", "this_package"], field="package")

    class Resolver:
        called = 0

        def resolve(self):
            self.called += 1
            return os.path.abspath("package_path")

    resolve0 = Resolver()
    resolve1 = Resolver()
    package_map = {
        "this_package": resolve0.resolve,
        "that_package": resolve1.resolve,
    }

    with pytest.raises(FileNotFoundError,
                       match=r"Could not find \"test1.txt\" in this_package \[package,file\]"):
        schema.hash_files("package", "file", packages=package_map)

    assert resolve0.called == 2
    assert resolve1.called == 0


def test_hash_files_with_package_missing():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    param = Parameter("[file]")
    edit.insert("package", "file", param)

    os.makedirs("package_path", exist_ok=True)
    with open("package_path/test0.txt", "w") as f:
        f.write("test")

    assert schema.set("package", "file", ["test0.txt", "test1.txt"])
    assert schema.set("package", "file", ["this_package", "this_package"], field="package")

    with pytest.raises(ValueError, match=r"Resolver for this_package not provided"):
        schema.hash_files("package", "file", packages={})


def test_hash_files_with_package_as_string():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    param = Parameter("[file]")
    edit.insert("package", "file", param)

    os.makedirs("package_path", exist_ok=True)
    with open("package_path/test0.txt", "w") as f:
        f.write("test")

    with open("package_path/test1.txt", "w") as f:
        f.write("test")

    assert schema.set("package", "file", ["test0.txt", "test1.txt"])
    assert schema.set("package", "file", ["this_package", "that_package"], field="package")

    class Resolver:
        called = 0

        def resolve(self):
            self.called += 1
            return os.path.abspath("package_path")

    resolve = Resolver()
    package_map = {
        "this_package": "package_path",
        "that_package": resolve.resolve,
    }

    assert schema.hash_files("package", "file", packages=package_map) == [
        "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
        "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
    ]

    assert resolve.called == 1


def test_hash_files_with_package_as_invalid():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    param = Parameter("[file]")
    edit.insert("package", "file", param)

    os.makedirs("package_path", exist_ok=True)
    with open("package_path/test0.txt", "w") as f:
        f.write("test")

    assert schema.set("package", "file", "test0.txt")
    assert schema.set("package", "file", "this_package", field="package")

    package_map = {
        "this_package": 1
    }

    with pytest.raises(TypeError, match="Resolver for this_package is not a recognized type"):
        schema.hash_files("package", "file", packages=package_map)


def test_hash_files_with_collection_dir_not_found():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    param = Parameter("[file]")
    edit.insert("package", "file", param)

    with open("test.txt", "w") as f:
        f.write("test")

    assert schema.set("package", "file", "test.txt")

    assert schema.hash_files("package", "file", collection_dir="nodirfound") == [
        "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"
    ]


def test_hash_files_with_collection_dir():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    param = Parameter("[file]")
    edit.insert("package", "file", param)

    os.makedirs("collections_dir", exist_ok=True)

    with open("collections_dir/test_3a52ce780950d4d969792a2559cd519d7ee8c727.txt", "w") as f:
        f.write("test")

    assert schema.set("package", "file", "test.txt")

    assert schema.hash_files("package", "file", collection_dir="collections_dir") == [
        "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"
    ]


def test_hash_files_scalar_file_empty():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    param = Parameter("file")
    edit.insert("file", param)

    assert schema.hash_files("file") is None


def test_hash_files_scalar_dir_empty():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    param = Parameter("dir")
    edit.insert("directory", param)

    assert schema.hash_files("directory") is None


def test_hash_files_list_file_empty():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    param = Parameter("[file]")
    edit.insert("file", param)

    assert schema.hash_files("file") == []


def test_hash_files_list_dir_empty():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    param = Parameter("[dir]")
    edit.insert("directory", param)

    assert schema.hash_files("directory") == []


def test_generate_doc_detailed():
    pytest.importorskip("sphinx")
    from docutils import nodes

    class Document:
        def note_explicit_target(*args):
            pass

    class State:
        document = Document()

    class Doc:
        state = State()

    schema = BaseSchema()
    edit = EditableSchema(schema)
    param = Parameter("str")
    edit.insert("param", param)

    with patch("sphinx.util.nodes.nested_parse_with_titles") as nested_parse_with_titles:
        doc = schema._generate_doc(Doc())
        assert len(doc) == 1
        assert isinstance(doc[0], nodes.section)
        nested_parse_with_titles.assert_called_once()


def test_generate_doc_not_detailed_empty(sphinx_doc):
    pytest.importorskip("sphinx")

    schema = BaseSchema()
    edit = EditableSchema(schema)
    param = Parameter("str")
    edit.insert("param", param)

    assert schema._generate_doc(sphinx_doc, detailed=False) is None


def test_generate_doc_not_detailed(sphinx_doc):
    pytest.importorskip("sphinx")
    from docutils import nodes
    from sphinx.addnodes import tabular_col_spec

    schema = BaseSchema()
    edit = EditableSchema(schema)
    param = Parameter("str")
    edit.insert("param", param)
    schema.set("param", "something")

    doc = schema._generate_doc(sphinx_doc, detailed=False)
    assert len(doc) == 2
    assert isinstance(doc[0], tabular_col_spec)
    assert isinstance(doc[1], nodes.table)
