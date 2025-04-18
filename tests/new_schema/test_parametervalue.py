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


def test_normalize_value_enum():
    enum = ["test0", "test1", "test2"]
    assert NodeValue.normalize("test0", "enum", enum=enum) == "test0"
    assert NodeValue.normalize("test1", "enum", enum=enum) == "test1"
    assert NodeValue.normalize("test2", "enum", enum=enum) == "test2"

    with pytest.raises(ValueError, match="test3 is not a member of: test0, test1, test2"):
        NodeValue.normalize("test3", "enum", enum=enum)

    with pytest.raises(TypeError, match="enum must be a string, not a <class 'int'>"):
        NodeValue.normalize(1, "enum", enum=enum)


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
