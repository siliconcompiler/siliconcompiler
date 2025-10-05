import pytest

from siliconcompiler.schema import BaseSchema
from siliconcompiler.schema import Parameter
from siliconcompiler.schema import EditableSchema


@pytest.mark.parametrize("child", (BaseSchema(), Parameter("str")))
def test_insert_child_schema(child):
    schema = BaseSchema()

    assert len(schema.getkeys()) == 0

    edit = EditableSchema(schema)
    edit.insert("test", child)

    assert len(schema.getkeys()) == 1
    assert schema.getkeys() == tuple(["test"])


def test_insert_duplicate():
    schema = BaseSchema()

    assert len(schema.getkeys()) == 0

    edit = EditableSchema(schema)
    edit.insert("test", BaseSchema())
    with pytest.raises(KeyError,
                       match=r"^'\[test\] is already defined'$"):
        edit.insert("test", BaseSchema())


def test_insert_duplicate_clobber():
    schema = BaseSchema()

    assert len(schema.getkeys()) == 0

    edit = EditableSchema(schema)
    edit.insert("test", BaseSchema())
    edit.insert("test", BaseSchema(), clobber=True)

    assert len(schema.getkeys()) == 1
    assert schema.getkeys() == tuple(["test"])


def test_insert_child_depth():
    schema = BaseSchema()

    assert len(schema.getkeys()) == 0

    edit = EditableSchema(schema)
    edit.insert("test0", "test1", "test2", BaseSchema())
    edit.insert("test0", "test1", "test3", BaseSchema())

    assert len(schema.getkeys()) == 1
    assert schema.getkeys() == tuple(["test0"])

    assert len(schema.getkeys("test0")) == 1
    assert schema.getkeys("test0") == tuple(["test1"])

    assert len(schema.getkeys("test0", "test1")) == 2
    assert schema.getkeys("test0", "test1") == tuple(["test2", "test3"])


def test_insert_child_depth_default():
    schema = BaseSchema()

    assert len(schema.getkeys()) == 0

    edit = EditableSchema(schema)
    edit.insert("test0", "default", "test2", BaseSchema())
    edit.insert("test0", "default", "test3", BaseSchema())

    assert len(schema.getkeys()) == 1
    assert schema.getkeys() == tuple(["test0"])

    assert len(schema.getkeys("test0")) == 0
    assert schema.getkeys("test0") == tuple()

    assert len(schema.getkeys("test0", "default")) == 2
    assert schema.getkeys("test0", "default") == tuple(["test2", "test3"])


def test_insert_illegal_type():
    schema = BaseSchema()

    assert len(schema.getkeys()) == 0

    edit = EditableSchema(schema)
    with pytest.raises(ValueError,
                       match=r"^Value \(<class 'str'>\) must be schema type: "
                             r"Parameter, BaseSchema$"):
        edit.insert("test", "123456")


def test_remove():
    schema = BaseSchema()

    assert len(schema.getkeys()) == 0

    edit = EditableSchema(schema)
    edit.insert("test", BaseSchema())

    assert len(schema.getkeys()) == 1
    assert schema.getkeys() == tuple(["test"])

    edit.remove("test")

    assert len(schema.getkeys()) == 0


def test_remove_depth_leaf():
    schema = BaseSchema()

    assert len(schema.getkeys()) == 0

    edit = EditableSchema(schema)
    edit.insert("test0", "test1", "test2", BaseSchema())
    edit.insert("test0", "test1", "test3", BaseSchema())

    assert len(schema.getkeys("test0", "test1")) == 2

    edit.remove("test0", "test1", "test2")

    assert len(schema.getkeys("test0", "test1")) == 1
    assert schema.getkeys("test0", "test1") == tuple(["test3"])


def test_remove_depth_middle():
    schema = BaseSchema()

    assert len(schema.getkeys()) == 0

    edit = EditableSchema(schema)
    edit.insert("test0", "test1", "test2", BaseSchema())
    edit.insert("test0", "test1", "test3", BaseSchema())

    assert len(schema.getkeys("test0")) == 1
    assert len(schema.getkeys("test0", "test1")) == 2

    edit.remove("test0", "test1")

    assert len(schema.getkeys("test0")) == 0


def test_remove_depth_middle_default():
    schema = BaseSchema()

    assert len(schema.getkeys()) == 0

    edit = EditableSchema(schema)
    edit.insert("test0", "default", "test2", BaseSchema())
    edit.insert("test0", "default", "test3", BaseSchema())

    assert len(schema.getkeys("test0")) == 0
    assert len(schema.getkeys("test0", "default")) == 2

    edit.remove("test0", "default")

    assert len(schema.getkeys("test0")) == 0


def test_remove_depth_leaf_default():
    schema = BaseSchema()

    assert len(schema.getkeys()) == 0

    edit = EditableSchema(schema)
    edit.insert("test0", "default", BaseSchema())

    assert len(schema.getdict("test0")) == 1

    edit.remove("test0", "default")

    assert len(schema.getdict("test0")) == 0


def test_remove_unknown():
    schema = BaseSchema()

    assert len(schema.getkeys()) == 0

    edit = EditableSchema(schema)
    with pytest.raises(KeyError,
                       match=r"^'\[test\] cannot be found'$"):
        edit.remove("test")


def test_insert_no_path():
    schema = BaseSchema()

    assert len(schema.getkeys()) == 0

    edit = EditableSchema(schema)
    with pytest.raises(ValueError,
                       match=r"^A keypath is required$"):
        edit.insert(BaseSchema())


def test_remove_no_path():
    schema = BaseSchema()

    assert len(schema.getkeys()) == 0

    edit = EditableSchema(schema)
    with pytest.raises(ValueError,
                       match=r"^A keypath is required$"):
        edit.remove()


def test_insert_invalid_keypath():
    schema = BaseSchema()

    assert len(schema.getkeys()) == 0

    edit = EditableSchema(schema)
    with pytest.raises(ValueError,
                       match=r"^Keypath must only be strings$"):
        edit.insert("test", 1, BaseSchema())


def test_remove_invalid_keypath():
    schema = BaseSchema()

    assert len(schema.getkeys()) == 0

    edit = EditableSchema(schema)
    with pytest.raises(ValueError,
                       match=r"^Keypath must only be strings$"):
        edit.remove("test", 1)


def test_search_no_path():
    schema = BaseSchema()

    assert len(schema.getkeys()) == 0

    edit = EditableSchema(schema)
    with pytest.raises(ValueError,
                       match=r"^A keypath is required$"):
        edit.search()


def test_search_invalid_keypath():
    schema = BaseSchema()

    assert len(schema.getkeys()) == 0

    edit = EditableSchema(schema)
    with pytest.raises(ValueError,
                       match=r"^Keypath must only be strings$"):
        edit.search("test", 1)


def test_search():
    schema = BaseSchema()

    assert len(schema.getkeys()) == 0

    class TestSchema(BaseSchema):
        pass

    edit = EditableSchema(schema)
    edit.insert("test0", "test1", "test2", BaseSchema())
    edit.insert("test0", "test1", "test3", TestSchema())

    assert isinstance(edit.search("test0"), BaseSchema)
    assert isinstance(edit.search("test0", "test1"), BaseSchema)
    assert isinstance(edit.search("test0", "test1", "test2"), BaseSchema)
    assert isinstance(edit.search("test0", "test1", "test3"), TestSchema)


def test_schema_parent():
    schema = BaseSchema()

    assert len(schema.getkeys()) == 0

    class TestSchema(BaseSchema):
        pass

    edit = EditableSchema(schema)
    edit.insert("test0", "test1", "test2", BaseSchema())
    edit.insert("test0", "test1", "test3", TestSchema())

    assert schema._parent() is schema

    assert schema.get("test0", field="schema")._parent() is schema
    assert schema.get("test0", "test1", field="schema")._parent() is \
        schema.get("test0", field="schema")
    assert schema.get("test0", "test1", "test2", field="schema")._parent() is \
        schema.get("test0", "test1", field="schema")
    assert schema.get("test0", "test1", "test3", field="schema")._parent() is \
        schema.get("test0", "test1", field="schema")


def test_schema_keypath_with_default():
    schema = BaseSchema()

    assert len(schema.getkeys()) == 0

    obj0 = BaseSchema()
    obj1 = BaseSchema()

    edit = EditableSchema(schema)
    edit.insert("test0", "default", "test2", obj0)
    edit.insert("test0", "test1", "test3", obj1)

    assert obj0._keypath == ("test0", "default", "test2")
    assert obj1._keypath == ("test0", "test1", "test3")


def test_schema_keypath_with_insert_at_default():
    schema = BaseSchema()

    assert len(schema.getkeys()) == 0

    obj0 = BaseSchema()
    obj1 = BaseSchema()

    edit = EditableSchema(schema)
    edit.insert("test0", "default", "test2", obj0)
    EditableSchema(schema.get("test0", "test1", field="schema")).insert("test3", obj1)

    assert obj0._keypath == ("test0", "default", "test2")
    assert obj1._keypath == ("test0", "test1", "test3")


def test_schema_keypath_with_insert_after_default():
    schema = BaseSchema()

    assert len(schema.getkeys()) == 0

    obj0 = BaseSchema()
    obj1 = BaseSchema()

    edit = EditableSchema(schema)
    edit.insert("test0", "default", "test2", "test3", obj0)
    EditableSchema(schema.get("test0", "test1", "test2", field="schema")).insert("test4", obj1)

    assert obj0._keypath == ("test0", "default", "test2", "test3")
    assert obj1._keypath == ("test0", "test1", "test2", "test4")
