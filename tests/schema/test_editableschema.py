import pytest

from siliconcompiler.schema import BaseSchema
from siliconcompiler.schema import Parameter
from siliconcompiler.schema import EditableSchema


@pytest.mark.parametrize("child", (BaseSchema(), Parameter("str")))
def test_add_child_schema(child):
    schema = BaseSchema()

    assert len(schema.getkeys()) == 0

    edit = EditableSchema(schema)
    edit.add("test", child)

    assert len(schema.getkeys()) == 1
    assert schema.getkeys() == tuple(["test"])


def test_add_duplicate():
    schema = BaseSchema()

    assert len(schema.getkeys()) == 0

    edit = EditableSchema(schema)
    edit.add("test", BaseSchema())
    with pytest.raises(KeyError,
                       match=r"\[test\] is already defined"):
        edit.add("test", BaseSchema())


def test_add_duplicate_clobber():
    schema = BaseSchema()

    assert len(schema.getkeys()) == 0

    edit = EditableSchema(schema)
    edit.add("test", BaseSchema())
    edit.add("test", BaseSchema(), clobber=True)

    assert len(schema.getkeys()) == 1
    assert schema.getkeys() == tuple(["test"])


def test_add_child_depth():
    schema = BaseSchema()

    assert len(schema.getkeys()) == 0

    edit = EditableSchema(schema)
    edit.add("test0", "test1", "test2", BaseSchema())
    edit.add("test0", "test1", "test3", BaseSchema())

    assert len(schema.getkeys()) == 1
    assert schema.getkeys() == tuple(["test0"])

    assert len(schema.getkeys("test0")) == 1
    assert schema.getkeys("test0") == tuple(["test1"])

    assert len(schema.getkeys("test0", "test1")) == 2
    assert schema.getkeys("test0", "test1") == tuple(["test2", "test3"])


def test_add_child_depth_default():
    schema = BaseSchema()

    assert len(schema.getkeys()) == 0

    edit = EditableSchema(schema)
    edit.add("test0", "default", "test2", BaseSchema())
    edit.add("test0", "default", "test3", BaseSchema())

    assert len(schema.getkeys()) == 1
    assert schema.getkeys() == tuple(["test0"])

    assert len(schema.getkeys("test0")) == 0
    assert schema.getkeys("test0") == tuple()

    assert len(schema.getkeys("test0", "default")) == 2
    assert schema.getkeys("test0", "default") == tuple(["test2", "test3"])


def test_add_illegal_type():
    schema = BaseSchema()

    assert len(schema.getkeys()) == 0

    edit = EditableSchema(schema)
    with pytest.raises(ValueError,
                       match=r"Value \(<class 'str'>\) must be schema type: Parameter, BaseSchema"):
        edit.add("test", "123456")


def test_remove():
    schema = BaseSchema()

    assert len(schema.getkeys()) == 0

    edit = EditableSchema(schema)
    edit.add("test", BaseSchema())

    assert len(schema.getkeys()) == 1
    assert schema.getkeys() == tuple(["test"])

    edit.remove("test")

    assert len(schema.getkeys()) == 0


def test_remove_depth_leaf():
    schema = BaseSchema()

    assert len(schema.getkeys()) == 0

    edit = EditableSchema(schema)
    edit.add("test0", "test1", "test2", BaseSchema())
    edit.add("test0", "test1", "test3", BaseSchema())

    assert len(schema.getkeys("test0", "test1")) == 2

    edit.remove("test0", "test1", "test2")

    assert len(schema.getkeys("test0", "test1")) == 1
    assert schema.getkeys("test0", "test1") == tuple(["test3"])


def test_remove_depth_middle():
    schema = BaseSchema()

    assert len(schema.getkeys()) == 0

    edit = EditableSchema(schema)
    edit.add("test0", "test1", "test2", BaseSchema())
    edit.add("test0", "test1", "test3", BaseSchema())

    assert len(schema.getkeys("test0")) == 1
    assert len(schema.getkeys("test0", "test1")) == 2

    edit.remove("test0", "test1")

    assert len(schema.getkeys("test0")) == 0


def test_remove_depth_middle_default():
    schema = BaseSchema()

    assert len(schema.getkeys()) == 0

    edit = EditableSchema(schema)
    edit.add("test0", "default", "test2", BaseSchema())
    edit.add("test0", "default", "test3", BaseSchema())

    assert len(schema.getkeys("test0")) == 0
    assert len(schema.getkeys("test0", "default")) == 2

    edit.remove("test0", "default")

    assert len(schema.getkeys("test0")) == 0


def test_remove_depth_leaf_default():
    schema = BaseSchema()

    assert len(schema.getkeys()) == 0

    edit = EditableSchema(schema)
    edit.add("test0", "default", BaseSchema())

    assert len(schema.getdict("test0")) == 1

    edit.remove("test0", "default")

    assert len(schema.getdict("test0")) == 0


def test_remove_unknown():
    schema = BaseSchema()

    assert len(schema.getkeys()) == 0

    edit = EditableSchema(schema)
    with pytest.raises(KeyError,
                       match=r"\[test\] cannot be found"):
        edit.remove("test")


def test_add_no_path():
    schema = BaseSchema()

    assert len(schema.getkeys()) == 0

    edit = EditableSchema(schema)
    with pytest.raises(ValueError,
                       match=r"A keypath is required"):
        edit.add(BaseSchema())


def test_remove_no_path():
    schema = BaseSchema()

    assert len(schema.getkeys()) == 0

    edit = EditableSchema(schema)
    with pytest.raises(ValueError,
                       match=r"A keypath is required"):
        edit.remove()


def test_add_invalid_keypath():
    schema = BaseSchema()

    assert len(schema.getkeys()) == 0

    edit = EditableSchema(schema)
    with pytest.raises(ValueError,
                       match=r"Keypath must only be strings"):
        edit.add("test", 1, BaseSchema())


def test_remove_invalid_keypath():
    schema = BaseSchema()

    assert len(schema.getkeys()) == 0

    edit = EditableSchema(schema)
    with pytest.raises(ValueError,
                       match=r"Keypath must only be strings"):
        edit.remove("test", 1)


def test_search_no_path():
    schema = BaseSchema()

    assert len(schema.getkeys()) == 0

    edit = EditableSchema(schema)
    with pytest.raises(ValueError,
                       match=r"A keypath is required"):
        edit.search()


def test_search_invalid_keypath():
    schema = BaseSchema()

    assert len(schema.getkeys()) == 0

    edit = EditableSchema(schema)
    with pytest.raises(ValueError,
                       match=r"Keypath must only be strings"):
        edit.search("test", 1)


def test_search():
    schema = BaseSchema()

    assert len(schema.getkeys()) == 0

    class TestSchema(BaseSchema):
        pass

    edit = EditableSchema(schema)
    edit.add("test0", "test1", "test2", BaseSchema())
    edit.add("test0", "test1", "test3", TestSchema())

    assert isinstance(edit.search("test0"), BaseSchema)
    assert isinstance(edit.search("test0", "test1"), BaseSchema)
    assert isinstance(edit.search("test0", "test1", "test2"), BaseSchema)
    assert isinstance(edit.search("test0", "test1", "test3"), TestSchema)
