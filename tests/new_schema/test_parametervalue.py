import pytest

from pathlib import Path

from siliconcompiler.schema.new.parametervalue import NodeValue


@pytest.mark.parametrize(
    "type,value,expect", [
        ("str", "test", "test"),
        ("str", 1, "1"),
        ("str", 1.0, "1.0"),
        ("str", True, "true"),
        ("str", False, "false"),
        ("str", None, None),
        ("int", 1, 1),
        ("int", "2", 2),
        ("int", 1.0, 1),
        ("int", None, None),
        ("float", 1e5, 1e5),
        ("float", "2e4", 2e4),
        ("float", 1.01, 1.01),
        ("float", None, None),
        ("bool", True, True),
        ("bool", False, False),
        ("bool", "True", True),
        ("bool", "False", False),
        ("bool", "TRUE", True),
        ("bool", "FALSE", False),
        ("bool", "true", True),
        ("bool", "false", False),
        ("bool", "t", True),
        ("bool", "f", False),
        ("bool", 1, True),
        ("bool", 0, False),
        ("[str]", "test", ["test"]),
        ("[str]", 1, ["1"]),
        ("[str]", 1.0, ["1.0"]),
        ("[str]", True, ["true"]),
        ("[str]", False, ["false"]),
        ("[str]", None, [None]),
        ("[str]", set([1, 2]), ["1", "2"]),
        ("[str]", (1, 2), ["1", "2"]),
        ("(str,str)", "(test0,test1)", ("test0", "test1")),
        ("(str,str)", (1, 2), ("1", "2")),
        ("(str,int)", "(test0,1)", ("test0", 1)),
        ("(str,int)", (1, 2), ("1", 2)),
        ("(str,float)", (1, 2.5), ("1", 2.5)),
    ])
def test_normalize_value(type, value, expect):
    norm = NodeValue.normalize(value, type)
    if expect in (True, False, None):
        assert norm is expect
    else:
        assert norm == expect


def test_make_enum():
    assert NodeValue._make_enum(["hello", "world"]) == "enum<hello,world>"
    assert NodeValue._make_enum(["hello"]) == "enum<hello>"
    assert NodeValue._make_enum(["hello", "world", "here"]) == "enum<hello,here,world>"


def test_normalize_value_enum():
    enum = NodeValue._make_enum(["test0", "test1", "test2"])
    assert NodeValue.normalize("test0", enum) == "test0"
    assert NodeValue.normalize("test1", enum) == "test1"
    assert NodeValue.normalize("test2", enum) == "test2"

    with pytest.raises(ValueError, match="test3 is not a member of: test0, test1, test2"):
        NodeValue.normalize("test3", enum)

    with pytest.raises(TypeError, match="enum must be a string, not a <class 'int'>"):
        NodeValue.normalize(1, enum)


def test_normalize_value_file():
    assert NodeValue.normalize("test0", "file") == "test0"
    assert NodeValue.normalize("./test1", "file") == "./test1"
    assert NodeValue.normalize(Path("./test2"), "file") == "test2"

    with pytest.raises(TypeError, match="file must be a string or Path, not <class 'int'>"):
        NodeValue.normalize(1, "file")


def test_normalize_value_dir():
    assert NodeValue.normalize("test0", "dir") == "test0"
    assert NodeValue.normalize("./test1", "dir") == "./test1"
    assert NodeValue.normalize(Path("./test2"), "dir") == "test2"

    with pytest.raises(TypeError, match="dir must be a string or Path, not <class 'int'>"):
        NodeValue.normalize(1, "dir")


def test_normalize_invalid_type():
    with pytest.raises(ValueError, match="Invalid type specifier: invalid"):
        NodeValue.normalize('1235', 'invalid')


def test_normalize_invalid_int():
    with pytest.raises(ValueError, match="\"a\" unable to convert to int"):
        NodeValue.normalize('a', 'int')


def test_normalize_invalid_float():
    with pytest.raises(ValueError, match="\"a\" unable to convert to float"):
        NodeValue.normalize('a', 'float')


def test_normalize_invalid_bool():
    with pytest.raises(ValueError, match="\"a\" unable to convert to boolean"):
        NodeValue.normalize('a', 'bool')


def test_normalize_invalid_str():
    with pytest.raises(ValueError, match=r'"<class \'list\'>" unable to convert to str'):
        NodeValue.normalize(list(['a']), 'str')
    with pytest.raises(ValueError, match=r'"<class \'set\'>" unable to convert to str'):
        NodeValue.normalize(set(['a']), 'str')
    with pytest.raises(ValueError, match=r'"<class \'tuple\'>" unable to convert to str'):
        NodeValue.normalize(tuple(['a']), 'str')


def test_normalize_invalid_enum():
    with pytest.raises(RuntimeError, match=r'enum cannot be empty set'):
        NodeValue.normalize('a', 'enum<>')


def test_set_type():
    value = NodeValue("str")
    assert value.type == "str"
    value._set_type("int")
    assert value.type == "int"


def test_copy():
    value = NodeValue("str")

    new_value = value.copy()

    assert value is not new_value
