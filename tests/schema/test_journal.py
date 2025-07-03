import json
import pytest

from siliconcompiler.schema import BaseSchema
from siliconcompiler.schema import EditableSchema
from siliconcompiler.schema import Parameter
from siliconcompiler.schema import Journal


def test_init():
    assert Journal().keypath == tuple()


def test_init_with_keypath():
    assert Journal(keyprefix=["test0", "test1"]).keypath == ("test0", "test1")


def test_is_journaling_not():
    assert Journal().is_journaling() is False


def test_is_journaling():
    journal = Journal()
    journal.start()
    assert journal.is_journaling() is True
    journal.stop()
    assert journal.is_journaling() is False


def test_has_journaling():
    journal = Journal()
    journal.start()
    assert journal.has_journaling() is False
    journal.record("add", ["test"], "value")
    assert journal.has_journaling() is True
    journal.stop()
    assert journal.is_journaling() is False


def test_has_journaling_child():
    journal = Journal()
    journal.start()
    child = journal.get_child("test0")

    assert journal.has_journaling() is False
    assert child.has_journaling() is False
    journal.record("add", ["test"], "value")
    assert journal.has_journaling() is True
    assert child.has_journaling() is False
    journal.stop()
    assert journal.is_journaling() is False
    assert child.has_journaling() is False


def test_is_journaling_child():
    journal = Journal()
    child = journal.get_child("test0")
    journal.start()
    assert journal.is_journaling() is True
    assert child.is_journaling() is True
    journal.stop()
    assert journal.is_journaling() is False
    assert child.is_journaling() is False


def test_is_journaling_from_child():
    journal = Journal()
    child = journal.get_child("test0")
    child.start()
    assert journal.is_journaling() is True
    assert child.is_journaling() is True
    child.stop()
    assert journal.is_journaling() is False
    assert child.is_journaling() is False


def test_access():
    assert isinstance(Journal.access(BaseSchema()), Journal)


def test_access_invalid():
    with pytest.raises(TypeError, match="schema must be a BaseSchema, not "
                       "<class 'siliconcompiler.schema.parameter.Parameter'>"):
        Journal.access(Parameter("str"))


def test_start_stop():
    journal = Journal()
    assert journal.get() is None
    assert journal.get_types() == set()
    assert not journal.is_journaling()
    journal.start()
    assert journal.get() == []
    assert journal.get_types() == {"set", "add", "remove", "unset"}
    assert journal.is_journaling()
    journal.stop()
    assert journal.get() is None
    assert journal.get_types() == set()
    assert not journal.is_journaling()


def test_get_no_get():
    journal = Journal()
    journal.start()
    assert "get" not in journal.get_types()

    assert journal.get() == []
    journal.record("get", ["test0", "test1"], None, field="value")
    assert journal.get() == []


def test_get_no_journal():
    journal = Journal()
    journal.add_type("get")
    assert "get" in journal.get_types()

    assert journal.get() is None
    journal.record("get", ["test0", "test1"], None, field="value")
    assert journal.get() is None


def test_get():
    journal = Journal()
    journal.start()
    journal.add_type("get")
    assert "get" in journal.get_types()

    assert journal.get() == []
    journal.record("get", ["test0", "test1"], None, field="value")
    assert journal.get() == [{
        "type": "get",
        "key": ("test0", "test1"),
        "value": None,
        "field": "value",
        "step": None,
        "index": None
    }]


def test_set():
    journal = Journal()
    journal.start()
    assert "set" in journal.get_types()

    journal.record("set", ["test0", "test1"], "hello", field="value")
    assert journal.get() == [{
        "type": "set",
        "key": ("test0", "test1"),
        "value": "hello",
        "field": "value",
        "step": None,
        "index": None
    }]


def test_set_key_prefix():
    journal = Journal(keyprefix=["this", "prefix"])
    journal.start()

    journal.record("set", ["test0", "test1"], "hello", field="value")
    assert journal.get() == [{
        "type": "set",
        "key": ("this", "prefix", "test0", "test1"),
        "value": "hello",
        "field": "value",
        "step": None,
        "index": None
    }]


def test_set_key_prefix_with_child():
    journal = Journal(keyprefix=["this", "prefix"])
    journal.start()
    child = journal.get_child("test0")

    child.record("set", ["test1"], "hello", field="value")
    assert journal.get() == [{
        "type": "set",
        "key": ("this", "prefix", "test0", "test1"),
        "value": "hello",
        "field": "value",
        "step": None,
        "index": None
    }]
    assert child.get() == [{
        "type": "set",
        "key": ("this", "prefix", "test0", "test1"),
        "value": "hello",
        "field": "value",
        "step": None,
        "index": None
    }]


def test_set_multiple():
    journal = Journal()
    journal.start()

    journal.record("set", ["test0", "test1"], "hello0", field="value")
    journal.record("set", ["test0", "test1"], "hello1", field="value")

    assert journal.get() == [{
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


def test_add():
    journal = Journal()
    journal.start()
    assert "add" in journal.get_types()

    journal.record("add", ["test0", "test1"], "hello", field="value")
    assert journal.get() == [{
        "type": "add",
        "key": ("test0", "test1"),
        "value": "hello",
        "field": "value",
        "step": None,
        "index": None
    }]


def test_unset():
    journal = Journal()
    journal.start()
    assert "unset" in journal.get_types()
    journal.record("unset", ["test0", "test1"])
    assert journal.get() == [{
        "type": "unset",
        "key": ("test0", "test1"),
        "value": None,
        "field": None,
        "step": None,
        "index": None
    }]


def test_remove():
    journal = Journal()
    journal.start()
    assert "remove" in journal.get_types()
    journal.record("remove", ["test0", "test1"])
    assert journal.get() == [{
        "type": "remove",
        "key": ("test0", "test1"),
        "value": None,
        "field": None,
        "step": None,
        "index": None
    }]


def test_from_dict():
    journal = Journal()
    journal.from_dict([{
            "type": "set",
            "key": ("test0", "test1"),
            "value": "hello",
            "field": "value",
            "step": None,
            "index": None
        }])
    assert journal.get() == [{
            "type": "set",
            "key": ("test0", "test1"),
            "value": "hello",
            "field": "value",
            "step": None,
            "index": None
        }]


def test_replay_invalid_schema_type():
    journal = Journal()
    journal.start()
    assert "remove" in journal.get_types()
    journal.record("remove", ["test0", "test1"])

    with pytest.raises(TypeError, match="schema must be a BaseSchema, not "
                       "<class 'siliconcompiler.schema.parameter.Parameter'>"):
        journal.replay(Parameter("str"))


def test_replay_schema():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "default", Parameter("str"))

    check_schema = schema.copy()

    journal = Journal.access(schema)
    journal.start()
    journal.add_type("get")

    assert schema.set("test0", "test1", "hello")
    assert schema.get("test0", "test1") == "hello"
    assert check_schema.get("test0", "test1") is None

    assert len(journal.get()) == 2

    journal.replay(check_schema)
    assert check_schema.get("test0", "test1") == "hello"


def test_replay_all_types():
    schema = BaseSchema()
    edit = EditableSchema(schema)
    edit.insert("test0", "default", Parameter("str"))
    edit.insert("test1", "default", Parameter("[str]"))

    check_schema = schema.copy()

    journal = Journal.access(schema)
    journal.start()

    assert schema.set("test0", "test1", "hello0")
    assert schema.add("test1", "test1", "hello1")
    assert schema.add("test1", "test2", "hello2")
    schema.remove("test1", "test2")
    schema.unset("test1", "test1")

    journal.replay(check_schema)
    assert check_schema.get("test0", "test1") == "hello0"
    assert check_schema.get("test1", "test1") == []
    assert check_schema.allkeys() == set([
        ('test0', 'test1'),
        ('test0', 'default'),
        ('test1', 'test1'),
        ('test1', 'default')
    ])


def test_replay_invalid_type():
    journal = Journal()
    journal._Journal__journal = [{
        "type": "notanoption",
        "key": ("test0", "test1"),
        "value": "hello",
        "field": "value",
        "step": None,
        "index": None
    }]

    with pytest.raises(ValueError, match="Unknown record type notanoption"):
        journal.replay(BaseSchema())


def test_replay_empty():
    Journal().replay(BaseSchema())


def test_add_invalid_type():
    with pytest.raises(ValueError, match="invalid is not a valid type"):
        Journal().add_type("invalid")


def test_remove_invalid_type():
    Journal().remove_type("invalid")


@pytest.mark.parametrize("error", (ValueError, RuntimeError, KeyError))
def test_forward_exception_with_key_set_replay(error, monkeypatch):
    schema = BaseSchema()
    edit = EditableSchema(schema)
    param = Parameter("str")
    edit.insert("test0", "test1", param)

    def dummy_set(*args, **kwargs):
        raise error("this is an error from the param")
    monkeypatch.setattr(param, 'set', dummy_set)

    journal = Journal()
    journal._Journal__journal = [
        {
            "type": "set",
            "key": ("test0", "test1"),
            "value": "hello",
            "field": "value",
            "step": None,
            "index": None
        }
    ]

    with pytest.raises(error,
                       match=r"error while setting \[test0,test1\]: "
                             r"this is an error from the param"):
        journal.replay(schema)


@pytest.mark.parametrize("error", (ValueError, RuntimeError, KeyError))
def test_forward_exception_with_key_add_replay(error, monkeypatch):
    schema = BaseSchema()
    edit = EditableSchema(schema)
    param = Parameter("[str]")
    edit.insert("test0", "test1", param)

    def dummy_add(*args, **kwargs):
        raise error("this is an error from the param")
    monkeypatch.setattr(param, 'add', dummy_add)

    journal = Journal()
    journal._Journal__journal = [
        {
            "type": "add",
            "key": ("test0", "test1"),
            "value": "hello",
            "field": "value",
            "step": None,
            "index": None
        }
    ]

    with pytest.raises(error,
                       match=r"error while adding to \[test0,test1\]: "
                             r"this is an error from the param"):
        journal.replay(schema)


def test_replay_file():
    replay = [
        {
            "type": "add",
            "key": ("test0", "test1"),
            "value": "hello",
            "field": "value",
            "step": None,
            "index": None
        }
    ]
    with open("replay.json", "w") as f:
        json.dump({"__journal__": replay}, f)

    schema = BaseSchema()
    edit = EditableSchema(schema)
    param = Parameter("[str]")
    edit.insert("test0", "test1", param)

    assert schema.get("test0", "test1") == []
    Journal.replay_file(schema, "replay.json")
    assert schema.get("test0", "test1") == ["hello"]


def test_replay_file_empty():
    with open("replay.json", "w") as f:
        json.dump({}, f)

    schema = BaseSchema()
    edit = EditableSchema(schema)
    param = Parameter("[str]")
    edit.insert("test0", "test1", param)

    assert schema.get("test0", "test1") == []
    Journal.replay_file(schema, "replay.json")
    assert schema.get("test0", "test1") == []
