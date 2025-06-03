import pickle
import pytest
import json

from siliconcompiler.schema import BaseSchema
from siliconcompiler.schema import EditableSchema
from siliconcompiler.schema import Parameter
from siliconcompiler.schema import JournalingSchema


def test_init_type():
    with pytest.raises(TypeError,
                       match="schema must be of BaseSchema type, not: "
                             "<class 'siliconcompiler.schema.parameter.Parameter'>"):
        JournalingSchema(Parameter("str"))


def test_init_type_journal():
    with pytest.raises(TypeError,
                       match="schema must be of cannot be a JournalingSchema"):
        JournalingSchema(JournalingSchema(BaseSchema()))


def test_from_manifest():
    with pytest.raises(RuntimeError,
                       match="Journal cannot be generated from manifest"):
        JournalingSchema.from_manifest()


def test_start_stop():
    schema = JournalingSchema(BaseSchema())
    assert schema.get_journal() is None
    assert schema.get_journaling_types() == set()
    assert not schema.is_journaling()
    schema.start_journal()
    assert schema.get_journal() == []
    assert schema.get_journaling_types() == {"set", "add", "remove", "unset"}
    assert schema.is_journaling()
    schema.stop_journal()
    assert schema.get_journal() is None
    assert schema.get_journaling_types() == set()
    assert not schema.is_journaling()


def test_get_no_journal():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "test1", Parameter("str"))
    schema = JournalingSchema(schema)

    schema.set("test0", "test1", "hello")
    assert schema.get("test0", "test1") == "hello"
    assert schema.get_journal() is None


def test_get():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "test1", Parameter("str"))
    schema = JournalingSchema(schema)
    schema.set("test0", "test1", "hello")

    schema.start_journal()
    schema.add_journaling_type("get")
    assert "get" in schema.get_journaling_types()

    assert schema.get_journal() == []
    assert schema.get("test0", "test1") == "hello"
    assert schema.get_journal() == [{
        "type": "get",
        "key": ("test0", "test1"),
        "value": None,
        "field": "value",
        "step": None,
        "index": None
    }]


def test_set_no_journal():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "test1", Parameter("str"))
    schema = JournalingSchema(schema)

    schema.set("test0", "test1", "hello")
    assert schema.get("test0", "test1") == "hello"


def test_set():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "test1", Parameter("str"))
    schema = JournalingSchema(schema)
    schema.start_journal()

    schema.set("test0", "test1", "hello")
    assert schema.get_journal() == [{
        "type": "set",
        "key": ("test0", "test1"),
        "value": "hello",
        "field": "value",
        "step": None,
        "index": None
    }]
    assert schema.get("test0", "test1") == "hello"


def test_set_key_prefix():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "test1", Parameter("str"))
    schema = JournalingSchema(schema, keyprefix=["this", "prefix"])
    schema.start_journal()

    schema.set("test0", "test1", "hello")
    assert schema.get_journal() == [{
        "type": "set",
        "key": ("this", "prefix", "test0", "test1"),
        "value": "hello",
        "field": "value",
        "step": None,
        "index": None
    }]
    assert schema.get("test0", "test1") == "hello"


def test_set_key_prefix_with_child():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "test1", Parameter("str"))
    schema = JournalingSchema(schema, keyprefix=["this", "prefix"])
    schema.start_journal()
    chip_schema = schema.get("test0", field="schema")

    chip_schema.set("test1", "hello")
    assert schema.get_journal() == [{
        "type": "set",
        "key": ("this", "prefix", "test0", "test1"),
        "value": "hello",
        "field": "value",
        "step": None,
        "index": None
    }]
    assert schema.get("test0", "test1") == "hello"


def test_set_multiple():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "test1", Parameter("str"))
    schema = JournalingSchema(schema)
    schema.start_journal()

    schema.set("test0", "test1", "hello0")
    schema.set("test0", "test1", "hello1")
    assert schema.get_journal() == [{
        "type": "set",
        "key": ("test0", "test1"),
        "value": "hello0",
        "field": "value",
        "step": None,
        "index": None
    }, {
        "type": "set",
        "key": ("test0", "test1"),
        "value": "hello1",
        "field": "value",
        "step": None,
        "index": None
    }]
    assert schema.get("test0", "test1") == "hello1"


def test_add_no_journal():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "test1", Parameter("[str]"))
    schema = JournalingSchema(schema)

    schema.add("test0", "test1", "hello")
    assert schema.get("test0", "test1") == ["hello"]


def test_add():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "test1", Parameter("[str]"))
    schema = JournalingSchema(schema)
    schema.start_journal()

    schema.add("test0", "test1", "hello")
    assert schema.get_journal() == [{
        "type": "add",
        "key": ("test0", "test1"),
        "value": "hello",
        "field": "value",
        "step": None,
        "index": None
    }]
    assert schema.get("test0", "test1") == ["hello"]


def test_unset_no_journal():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "test1", Parameter("str"))
    schema = JournalingSchema(schema)

    assert schema.set("test0", "test1", "hello")
    assert schema.get("test0", "test1") == "hello"

    schema.unset("test0", "test1")
    assert schema.get("test0", "test1") is None


def test_unset():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "test1", Parameter("str"))
    schema = JournalingSchema(schema)

    assert schema.set("test0", "test1", "hello")
    assert schema.get("test0", "test1") == "hello"

    schema.start_journal()
    schema.unset("test0", "test1")
    assert schema.get_journal() == [{
        "type": "unset",
        "key": ("test0", "test1"),
        "value": None,
        "field": None,
        "step": None,
        "index": None
    }]

    assert schema.get("test0", "test1") is None


def test_remove_no_journal():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "default", Parameter("str"))
    schema = JournalingSchema(schema)

    assert schema.set("test0", "test1", "hello")
    assert schema.getkeys("test0") == tuple(["test1"])

    schema.start_journal()
    schema.remove("test0", "test1")
    assert schema.get_journal() == [{
        "type": "remove",
        "key": ("test0", "test1"),
        "value": None,
        "field": None,
        "step": None,
        "index": None
    }]
    assert schema.getkeys("test0") == tuple()


def test_remove():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "default", Parameter("str"))
    schema = JournalingSchema(schema)

    assert schema.set("test0", "test1", "hello")
    assert schema.getkeys("test0") == tuple(["test1"])

    schema.remove("test0", "test1")
    assert schema.getkeys("test0") == tuple()


def test_getdict():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "default", Parameter("str"))
    schema = JournalingSchema(schema)
    schema.start_journal()

    assert "__journal__" not in schema.getdict()

    assert schema.set("test0", "test1", "hello")

    schema_dict = schema.getdict()
    assert "__journal__" in schema_dict
    assert schema_dict["__journal__"] == [{
        "type": "set",
        "key": ("test0", "test1"),
        "value": "hello",
        "field": "value",
        "step": None,
        "index": None
    }]


def test_from_dict():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "default", Parameter("str"))
    schema = JournalingSchema(schema)

    schema._from_dict({
        "__journal__": [{
            "type": "set",
            "key": ("test0", "test1"),
            "value": "hello",
            "field": "value",
            "step": None,
            "index": None
        }]
    }, [], None)
    assert schema.get("test0", "test1") != "hello"
    assert schema.get_journal() == [{
            "type": "set",
            "key": ("test0", "test1"),
            "value": "hello",
            "field": "value",
            "step": None,
            "index": None
        }]


def test_import_journal_too_many():
    with pytest.raises(ValueError, match="only one argument is supported"):
        JournalingSchema(BaseSchema()).import_journal(
            schema=JournalingSchema(BaseSchema()), cfg={"__journal__": []})


def test_import_journal_invalid_schema_type():
    with pytest.raises(TypeError, match="schema must be a JournalingSchema, not "
                                        "<class 'siliconcompiler.schema.baseschema.BaseSchema'"):
        JournalingSchema(BaseSchema()).import_journal(
            schema=BaseSchema())


def test_import_journal_schema_none():
    JournalingSchema(BaseSchema()).import_journal(cfg={"__journal__": None})


def test_import_journal_schema():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "default", Parameter("str"))

    check_schema = schema.copy()

    schema = JournalingSchema(schema)
    schema.start_journal()
    schema.add_journaling_type("get")

    assert schema.set("test0", "test1", "hello")
    assert schema.get("test0", "test1") == "hello"
    assert check_schema.get("test0", "test1") != "hello"

    assert len(schema.get_journal()) == 2

    journal_check = JournalingSchema(check_schema)
    journal_check.import_journal(schema=schema)
    assert journal_check.get("test0", "test1") == "hello"
    assert check_schema.get("test0", "test1") == "hello"


def test_write_journal():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "default", Parameter("str"))

    schema = JournalingSchema(schema)
    schema.start_journal()

    assert schema.set("test0", "test1", "hello")

    schema.write_manifest("test.json")
    with open("test.json") as f:
        cfg = json.load(f)
    assert cfg["__journal__"] == [{
        "type": "set",
        "key": ["test0", "test1"],
        "value": "hello",
        "field": "value",
        "step": None,
        "index": None
    }]


def test_read_journal():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "default", Parameter("str"))

    check_schema = schema.copy()

    schema = JournalingSchema(schema)
    schema.start_journal()

    assert schema.set("test0", "test1", "hello")

    schema.write_manifest("test.json")

    assert check_schema.get("test0", "test1") != "hello"
    journal_check = JournalingSchema(check_schema)
    journal_check.read_journal("test.json")

    assert journal_check.get("test0", "test1") == "hello"
    assert check_schema.get("test0", "test1") == "hello"


def test_import_journal_cfg():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "default", Parameter("str"))

    check_schema = schema.copy()

    schema = JournalingSchema(schema)
    schema.start_journal()

    assert schema.set("test0", "test1", "hello")
    assert schema.get("test0", "test1") == "hello"
    assert check_schema.get("test0", "test1") != "hello"

    journal_check = JournalingSchema(check_schema)
    journal_check.import_journal(cfg=schema.getdict())
    assert journal_check.get("test0", "test1") == "hello"
    assert check_schema.get("test0", "test1") == "hello"


def test_import_journal_all_types():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "default", Parameter("str"))
    edit.insert("test1", "default", Parameter("[str]"))

    check_schema = schema.copy()

    schema = JournalingSchema(schema)
    schema.start_journal()

    assert schema.set("test0", "test1", "hello0")
    assert schema.add("test1", "test1", "hello1")
    assert schema.add("test1", "test2", "hello2")
    schema.remove("test1", "test2")
    schema.unset("test1", "test1")

    journal_check = JournalingSchema(check_schema)
    journal_check.import_journal(cfg=schema.getdict())
    assert journal_check.get("test0", "test1") == "hello0"
    assert journal_check.get("test1", "test1") == []
    assert journal_check.allkeys() == set([
        ('test0', 'test1'),
        ('test0', 'default'),
        ('test1', 'test1'),
        ('test1', 'default')
    ])


def test_import_journal_invalid_type():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "default", Parameter("str"))

    with pytest.raises(ValueError, match="Unknown record type notanoption"):
        JournalingSchema(schema).import_journal(cfg={
            "__journal__": [{
                "type": "notanoption",
                "key": ("test0", "test1"),
                "value": "hello",
                "field": "value",
                "step": None,
                "index": None
            }]
        })


def test_get_base_schema():
    base = BaseSchema()
    schema = JournalingSchema(base)
    assert schema.get_base_schema() is base


def test_add_invalid_type():
    schema = JournalingSchema(BaseSchema())

    with pytest.raises(ValueError, match="invalid is not a valid type"):
        schema.add_journaling_type("invalid")


def test_remove_invalid_type():
    schema = JournalingSchema(BaseSchema())
    schema.remove_journaling_type("invalid")


def test_child_function_access():
    class TestClass(BaseSchema):
        def thisfunction(self):
            pass

    schema = JournalingSchema(TestClass())
    assert hasattr(schema, "thisfunction")


def test_getschema():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "test1", Parameter("str"))

    schema = JournalingSchema(schema)
    child = schema.get("test0", field='schema')
    assert isinstance(child, JournalingSchema)
    schema.start_journal()

    child.set("test1", "newvalue")
    assert child.get("test1") == "newvalue"
    assert schema.get("test0", "test1") == "newvalue"

    assert child.get_journal() is None
    assert schema.get_journal() == [{
        "type": "set",
        "key": ("test0", "test1"),
        "value": "newvalue",
        "field": "value",
        "step": None,
        "index": None
    }]


def test_getschema_with_class_methods():
    class MethodClass(BaseSchema):
        def __init__(self):
            super().__init__()
            edit = EditableSchema(self)
            edit.insert("key", Parameter("str"))

        def set_stuff(self):
            self.set("key", "helloworld")

    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", MethodClass())

    schema = JournalingSchema(schema)
    child = schema.get("test0", field='schema')
    assert isinstance(child, JournalingSchema)
    schema.start_journal()

    child.set("key", "newvalue")
    assert child.get("key") == "newvalue"
    assert schema.get("test0", "key") == "newvalue"

    assert child.get_journal() is None
    assert schema.get_journal() == [{
        "type": "set",
        "key": ("test0", "key"),
        "value": "newvalue",
        "field": "value",
        "step": None,
        "index": None
    }]

    child.set_stuff()
    assert schema.get_journal() == [{
        "type": "set",
        "key": ("test0", "key"),
        "value": "newvalue",
        "field": "value",
        "step": None,
        "index": None
    }, {
        "type": "set",
        "key": ("test0", "key"),
        "value": "helloworld",
        "field": "value",
        "step": None,
        "index": None
    }]


def test_getschema_start_early():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "test1", Parameter("str"))

    schema = JournalingSchema(schema)
    schema.start_journal()
    child = schema.get("test0", field='schema')
    assert isinstance(child, JournalingSchema)

    child.set("test1", "newvalue")
    assert child.get("test1") == "newvalue"
    assert schema.get("test0", "test1") == "newvalue"

    assert child.get_journal() is None
    assert schema.get_journal() == [{
        "type": "set",
        "key": ("test0", "test1"),
        "value": "newvalue",
        "field": "value",
        "step": None,
        "index": None
    }]


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
        JournalingSchema(schema).get("test0", "test1")


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
        JournalingSchema(schema).set("test0", "test1", "value")


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
        JournalingSchema(schema).add("test0", "test1", "value")


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
        JournalingSchema(schema).unset("test0", "test1")


@pytest.mark.parametrize("error", (ValueError, RuntimeError, KeyError))
def test_forward_exception_with_key_set_import(error, monkeypatch):
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
        JournalingSchema(schema).import_journal(cfg={
            "__journal__": [
                {
                    "type": "set",
                    "key": ("test0", "test1"),
                    "value": "hello",
                    "field": "value",
                    "step": None,
                    "index": None
                }
            ]
        })


@pytest.mark.parametrize("error", (ValueError, RuntimeError, KeyError))
def test_forward_exception_with_key_add_import(error, monkeypatch):
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
        JournalingSchema(schema).import_journal(cfg={
            "__journal__": [
                {
                    "type": "add",
                    "key": ("test0", "test1"),
                    "value": "hello",
                    "field": "value",
                    "step": None,
                    "index": None
                }
            ]
        })


@pytest.mark.parametrize("error", (ValueError, RuntimeError, KeyError))
def test_forward_exception_with_key_unset_import(error, monkeypatch):
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
        JournalingSchema(schema).import_journal(cfg={
            "__journal__": [
                {
                    "type": "unset",
                    "key": ("test0", "test1"),
                    "value": None,
                    "field": None,
                    "step": None,
                    "index": None
                }
            ]
        })


def test_pickle():
    schema = JournalingSchema(BaseSchema())

    with pytest.raises(RuntimeError, match="pickling is not supported for journal"):
        pickle.dumps(schema)
