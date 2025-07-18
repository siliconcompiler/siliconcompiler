import pytest

from pathlib import Path

from siliconcompiler.schema.parametertype import \
    NodeType, NodeEnumType

enum1 = NodeEnumType("one", "two", "three")
enum2 = NodeEnumType("one", "two", "three", "four")


def test_node_enum_type_eq():
    assert enum1 != enum2
    assert enum1 == NodeEnumType("one", "two", "three")
    assert enum2 == NodeEnumType("one", "two", "three", "four")
    assert enum1 != 1


def test_node_enum_type_empty():
    with pytest.raises(ValueError, match="enum cannot be empty set"):
        NodeEnumType()


def test_node_enum_type_str():
    assert str(enum1) == "<one,three,two>"


def test_node_enum_type_repr():
    assert repr(enum1) == "<one,three,two>"


def test_node_enum_type_values():
    assert enum1.values == set(["one", "two", "three"])


def test_init_with_str():
    assert NodeType("str").type == "str"
    assert NodeType("(str,int)").type == ("str", "int")


def test_init_with_obj():
    assert NodeType(NodeType("str")).type == "str"
    assert NodeType(NodeType("(str,int)")).type == ("str", "int")
    assert NodeType(NodeType(NodeType("str"))).type == "str"


@pytest.mark.parametrize(
    "type,expect", [
        ("str", "str"),
        ("{str}", set(["str"])),
        ("int", "int"),
        ("{int}", set(["int"])),
        ("float", "float"),
        ("{float}", set(["float"])),
        ("bool", "bool"),
        ("<one,two,three>", enum1),
        ("{<one,two,three>}", set([enum1])),
        ("[str]", ["str"]),
        ("[file]", ["file"]),
        ("[dir]", ["dir"]),
        ("file", "file"),
        ("dir", "dir"),
        ("[[str]]", [["str"]]),
        ("[(str,str)]", [("str", "str")]),
        ("(str,str)", ("str", "str")),
        ("(str,int)", ("str", "int")),
        ("(str,float)", ("str", "float")),
        ("(str,<one,two,three,four>)", ("str", enum2)),
        ("(<one,two,three>,<one,two,three,four>)", (enum1, enum2)),
        ("[(<one,two,three>,<one,two,three,four>)]", [(enum1, enum2)])
    ])
def test_parse(type, expect):
    assert NodeType.parse(type) == expect


@pytest.mark.parametrize(
    "type,expect", [
        ("str", "str"),
        ("int", "int"),
        ("float", "float"),
        ("bool", "bool"),
        (enum1, "<one,three,two>"),
        (["str"], "[str]"),
        (["file"], "[file]"),
        (["dir"], "[dir]"),
        ("file", "file"),
        ("dir", "dir"),
        ([["str"]], "[[str]]"),
        ([("str", "str")], "[(str,str)]"),
        (("str", "str"), "(str,str)"),
        (("str", "int"), "(str,int)"),
        (("str", "float"), "(str,float)"),
        (("str", enum2), "(str,<four,one,three,two>)"),
        ((enum1, enum2), "(<one,three,two>,<four,one,three,two>)"),
        ([(enum1, enum2)], "[(<one,three,two>,<four,one,three,two>)]"),
        (NodeType([(enum1, enum2)]), "[(<one,three,two>,<four,one,three,two>)]")
    ])
def test_encode(type, expect):
    assert NodeType.encode(type) == expect


def test_encode_invalid():
    with pytest.raises(ValueError, match="1 not a recognized type"):
        NodeType.encode(1)


@pytest.mark.parametrize(
    "type,value,expect", [
        ("str", "test", "test"),
        ("str", list(["test"]), "test"),
        ("str", set(["test"]), "test"),
        ("str", tuple(["test"]), "test"),
        ("str", 1, "1"),
        ("str", 1.0, "1.0"),
        ("str", True, "true"),
        ("str", False, "false"),
        ("str", None, None),
        ("int", 1, 1),
        ("int", "2", 2),
        ("int", 1.0, 1),
        ("int", None, None),
        ("int", list([1]), 1),
        ("int", set(["1"]), 1),
        ("int", tuple(["2"]), 2),
        ("float", 1e5, 1e5),
        ("float", "2e4", 2e4),
        ("float", 1.01, 1.01),
        ("float", None, None),
        ("float", list([1.1]), 1.1),
        ("float", set(["1.2"]), 1.2),
        ("float", tuple(["2.3"]), 2.3),
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
        ("bool", list([True]), True),
        ("bool", set(["f"]), False),
        ("bool", tuple(["t"]), True),
        ("[str]", "test", ["test"]),
        ("[str]", 1, ["1"]),
        ("[str]", 1.0, ["1.0"]),
        ("[str]", True, ["true"]),
        ("[str]", False, ["false"]),
        ("[str]", None, [None]),
        ("[str]", set([1, 2]), ["1", "2"]),
        ("[str]", (1, 2), ["1", "2"]),
        ("{str}", "test", set(["test"])),
        ("{str}", 1, set(["1"])),
        ("{str}", 1.0, set(["1.0"])),
        ("{str}", True, set(["true"])),
        ("{str}", False, set(["false"])),
        ("{str}", None, set([None])),
        ("{str}", set([1, 2]), set(["1", "2"])),
        ("{str}", (1, 2), set(["1", "2"])),
        ("[[str]]", "test", [["test"]]),
        ("[[str]]", ["test"], [["test"]]),
        ("[[str]]", ["test", "hello"], [["test"], ["hello"]]),
        ("[[str]]", [["test"], ["test", "hello"]], [["test"], ["test", "hello"]]),
        ("(str,str)", "(test0,test1)", ("test0", "test1")),
        ("(str,str)", (1, 2), ("1", "2")),
        ("(str,int)", "(test0,1)", ("test0", 1)),
        ("(str,int)", (1, 2), ("1", 2)),
        ("(str,float)", (1, 2.5), ("1", 2.5)),
        ("{(str,float)}", (1, 2.5), set([("1", 2.5)])),
        (NodeType("(str,float)"), (1, 2.5), ("1", 2.5))
    ])
def test_normalize(type, value, expect):
    norm = NodeType.normalize(value, NodeType.parse(type))
    if expect in (True, False, None):
        assert norm is expect
    else:
        assert norm == expect


@pytest.mark.parametrize(
    "type,value,expect", [
        ("str", "test", "\"test\""),
        ("str", None, ""),
        ("str", "\"test\"", "\"\\\"test\\\"\""),
        ("str", "test[0]", "\"test\\[0]\""),
        ("str", "test$next[0]", "\"test\\$next\\[0]\""),
        ("str", "test\\next", "\"test\\\\next\""),
        ("int", 1, "1"),
        ("float", 1e5, "100000"),
        ("float", 10.5e-6, "1.05e-05"),
        ("float", 100.555555555e-12, "1.00555556e-10"),
        ("bool", True, "true"),
        ("<test0,test1,test2>", "test0", "\"test0\""),
        ("bool", False, "false"),
        ("file", "/usr/test.txt", "\"/usr/test.txt\""),
        ("file", "/usr/test 0.txt", "\"/usr/test 0.txt\""),
        ("dir", "/usr", "\"/usr\""),
        ("dir", "/usr[0]", "\"/usr\\[0]\""),
        ("dir", "/usr\"0\"", "\"/usr\\\"0\\\"\""),
        ("dir", "$TEST/usr", "\"$env(TEST)/usr\""),
        ("dir", "${TEST}/usr", "\"$env(TEST)/usr\""),
        ("[str]", ["test"], "[list \"test\"]"),
        ("[str]", None, "[list ]"),
        ("{str}", None, "[list ]"),
        ("[bool]", [False], "[list false]"),
        ("[int]", [12], "[list 12]"),
        ("{int}", set([12]), "[list 12]"),
        ("{int}", set([15, 12]), "[list 12 15]"),
        ("[int]", [None], "[list ]"),
        ("(int,str)", None, "[list ]"),
        ("[[str]]", [["test", "test0"], ["test"]],
            "[list [list \"test\" \"test0\"] [list \"test\"]]"),
        ("(str,str)", ("test0", "test1"), "[list \"test0\" \"test1\"]"),
        (NodeType("(str,float)"), ("1", 2.5), "[list \"1\" 2.5]")
    ])
def test_to_tcl(type, value, expect):
    assert NodeType.to_tcl(value, NodeType.parse(type)) == expect


def test_to_tcl_unsupported():
    with pytest.raises(TypeError, match="invalid is not a supported type"):
        NodeType.to_tcl(12, "invalid")


def test_normalize_value_enum():
    enum = NodeEnumType("test0", "test1", "test2")
    assert NodeType.normalize("test0", enum) == "test0"
    assert NodeType.normalize("test1", enum) == "test1"
    assert NodeType.normalize("test2", enum) == "test2"

    with pytest.raises(ValueError, match="test3 is not a member of: test0, test1, test2"):
        NodeType.normalize("test3", enum)

    with pytest.raises(ValueError, match="enum must be a string, not a <class 'int'>"):
        NodeType.normalize(1, enum)


def test_normalize_value_file():
    assert NodeType.normalize("test0", "file") == "test0"
    assert NodeType.normalize("./test1", "file") == "test1"
    assert NodeType.normalize(Path("./test2"), "file") == "test2"

    with pytest.raises(ValueError, match="file must be a string or Path, not <class 'int'>"):
        NodeType.normalize(1, "file")


def test_normalize_value_dir():
    assert NodeType.normalize("test0", "dir") == "test0"
    assert NodeType.normalize("./test1", "dir") == "test1"
    assert NodeType.normalize(Path("./test2"), "dir") == "test2"

    with pytest.raises(ValueError, match="dir must be a string or Path, not <class 'int'>"):
        NodeType.normalize(1, "dir")


def test_normalize_value_nodetype():
    assert NodeType.normalize("test0", NodeType("dir")) == "test0"
    assert NodeType.normalize("./test1",  NodeType("[str]")) == ["./test1"]


def test_normalize_invalid_type():
    with pytest.raises(ValueError, match="Invalid type specifier: invalid"):
        NodeType.normalize('1235', 'invalid')


def test_normalize_invalid_int():
    with pytest.raises(ValueError, match="\"a\" unable to convert to int"):
        NodeType.normalize('a', 'int')


def test_normalize_invalid_list_entry():
    with pytest.raises(ValueError, match="\"a\" unable to convert to int"):
        NodeType.normalize(['a'], ['int'])


def test_normalize_invalid_float():
    with pytest.raises(ValueError, match="\"a\" unable to convert to float"):
        NodeType.normalize('a', 'float')


def test_normalize_invalid_bool():
    with pytest.raises(ValueError, match="\"a\" unable to convert to boolean"):
        NodeType.normalize('a', 'bool')


def test_normalize_invalid_tuple():
    with pytest.raises(ValueError, match=r"\(a\) does not have 2 entries"):
        NodeType.normalize('(a)', ("int", "str"))
    with pytest.raises(ValueError, match=r"\(a\) does not have 2 entries"):
        NodeType.normalize('a', ("int", "str"))
    with pytest.raises(ValueError, match=r"\(a\) \(<class 'set'>\) cannot be converted to tuple"):
        NodeType.normalize(set(['a']), ("int", "str"))
    with pytest.raises(ValueError, match=r"\(1\) \(<class 'int'>\) cannot be converted to tuple"):
        NodeType.normalize(1, ("int", "str"))


def test_normalize_invalid_str():
    with pytest.raises(ValueError, match=r'"<class \'list\'>" unable to convert to str'):
        NodeType.normalize(list(['a', 'b']), 'str')
    with pytest.raises(ValueError, match=r'"<class \'set\'>" unable to convert to str'):
        NodeType.normalize(set(['a', 'b']), 'str')
    with pytest.raises(ValueError, match=r'"<class \'tuple\'>" unable to convert to str'):
        NodeType.normalize(tuple(['a', 'b']), 'str')


@pytest.mark.parametrize("sctype", [
    "str",
    "bool",
    "[str]",
    "[int]",
    "(str,int)",
    "(str,int,bool,float,<hello,world>)",
    "[(str,int)]",
    "[<hello,world>]",
    "{(str,int,int,str)}"
])
def test_str(sctype):
    assert str(NodeType(sctype)) == sctype


def test_str_invalid():
    with pytest.raises(ValueError, match="<class 'int'> not a recognized type"):
        str(NodeType(int))


@pytest.mark.parametrize("sctype,check,expect", [
    ("str", "str", True),
    ("str", "int", False),
    ("str", list, False),
    ("str", tuple, False),
    ("int", "int", True),
    ("int", "str", False),
    ("int", list, False),
    ("int", tuple, False),
    ("bool", "bool", True),
    ("bool", "str", False),
    ("bool", list, False),
    ("bool", tuple, False),
    ("bool", NodeEnumType, False),
    ("(str,int)", "str", True),
    ("(str,int)", "int", True),
    ("(str,int)", tuple, True),
    ("(str,int)", list, False),
    ("(str,int)", "bool", False),
    ("[(str,int)]", "str", True),
    ("[(str,int)]", "int", True),
    ("[(str,int)]", tuple, True),
    ("[(str,int)]", list, True),
    ("[(str,int)]", "bool", False),
    ("{(str,int)}", set, True),
    ("{(str,int)}", "str", True),
    ("{(str,int)}", "int", True),
    ("{(str,int)}", tuple, True),
    ("{(str,int)}", list, False),
    ("{(str,int)}", set, True),
    ("{(str,int)}", "bool", False),
    ("(str,int,bool,float,<hello,world>)", "str", True),
    ("(str,int,bool,float,<hello,world>)", "int", True),
    ("(str,int,bool,float,<hello,world>)", "bool", True),
    ("(str,int,bool,float,<hello,world>)", "float", True),
    ("(str,int,bool,float,<hello,world>)", NodeEnumType, True),
    ("(str,int,bool,float,<hello,world>)", tuple, True),
    ("(str,int,bool,float,<hello,world>)", list, False)
])
def test_contains(sctype, check, expect):
    assert NodeType.contains(NodeType.parse(sctype), check) is expect
