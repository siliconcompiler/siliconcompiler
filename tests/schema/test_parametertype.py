import pytest

from pathlib import Path

from siliconcompiler.schema.parametertype import \
    NodeType, NodeEnumType, NodeRangeType

enum1 = NodeEnumType("one", "two", "three")
enum2 = NodeEnumType("one", "two", "three", "four")


def test_node_enum_type_eq():
    assert enum1 != enum2
    assert enum1 == NodeEnumType("one", "two", "three")
    assert enum2 == NodeEnumType("one", "two", "three", "four")
    assert enum1 != 1


def test_node_enum_type_empty():
    with pytest.raises(ValueError, match=r"^enum cannot be empty set$"):
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


def test_parse_invalid_int_range():
    with pytest.raises(ValueError, match=r"^invalid literal for int\(\) with base 10: 'a'$"):
        NodeType.parse("int<a,2,5-7>")


def test_parse_invalid_float_range():
    with pytest.raises(ValueError, match=r"^could not convert string to float: 'a'$"):
        NodeType.parse("float<a,2,5-7>")


def test_parse_invalid_base_range():
    with pytest.raises(ValueError, match=r"^bool<a,2,5-7>$"):
        NodeType.parse("bool<a,2,5-7>")


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
    with pytest.raises(ValueError, match=r"^1 not a recognized type$"):
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
        (NodeType("(str,float)"), (1, 2.5), ("1", 2.5)),
        ("str<one,two,three>", "one", "one"),
        ("int<0,2,5>", "2", 2),
        ("int<0..5>", "2", 2),
        ("int<0,2,5..9>", "8", 8),
        ("float<0,2.1,5>", "2.1", 2.1),
        ("float<0..5>", "2.5", 2.5),
        ("float<0,2,5..9>", "8.7", 8.7),
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
        ("int<0..5>", 1, "1"),
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
    with pytest.raises(TypeError, match=r"^invalid is not a supported type$"):
        NodeType.to_tcl(12, "invalid")


def test_normalize_value_enum():
    enum = NodeEnumType("test0", "test1", "test2")
    assert NodeType.normalize("test0", enum) == "test0"
    assert NodeType.normalize("test1", enum) == "test1"
    assert NodeType.normalize("test2", enum) == "test2"

    with pytest.raises(ValueError, match=r"^test3 is not a member of: test0, test1, test2$"):
        NodeType.normalize("test3", enum)

    with pytest.raises(ValueError, match=r"^enum must be a string, not a <class 'int'>$"):
        NodeType.normalize(1, enum)


def test_normalize_value_int_range():
    range = NodeRangeType("int", (0, 0), (2, 2), (5, 7))
    assert NodeType.normalize("0", range) == 0
    assert NodeType.normalize("2", range) == 2
    assert NodeType.normalize("6", range) == 6
    assert NodeType.normalize("7", range) == 7

    with pytest.raises(ValueError, match=r"^8 is not in range: 0, 2, 5\.\.7$"):
        NodeType.normalize("8", range)


@pytest.mark.parametrize("ranges,expect", [
    ([(0, 0), (2, 2), (5, 7)], [(0, 0), (2, 2), (5, 7)]),
    ([(5, 7), (2, 2), (0, 0)], [(0, 0), (2, 2), (5, 7)]),
])
def test_range_value_sorting(ranges, expect):
    range = NodeRangeType("int", *ranges)
    assert range.values == expect


def test_normalize_value_float_range():
    range = NodeRangeType("float", (0, 0), (2.2, 2.2), (5, 7))
    assert NodeType.normalize("0", range) == 0
    assert NodeType.normalize("2.2", range) == 2.2
    assert NodeType.normalize("6", range) == 6
    assert NodeType.normalize("7", range) == 7

    with pytest.raises(ValueError, match=r"^8\.0 is not in range: 0, 2\.2, 5\.\.7$"):
        NodeType.normalize("8", range)


def test_normalize_value_file():
    assert NodeType.normalize("test0", "file") == "test0"
    assert NodeType.normalize("./test1", "file") == "test1"
    assert NodeType.normalize(Path("./test2"), "file") == "test2"

    with pytest.raises(ValueError, match=r"^file must be a string or Path, not <class 'int'>$"):
        NodeType.normalize(1, "file")


def test_normalize_value_dir():
    assert NodeType.normalize("test0", "dir") == "test0"
    assert NodeType.normalize("./test1", "dir") == "test1"
    assert NodeType.normalize(Path("./test2"), "dir") == "test2"

    with pytest.raises(ValueError, match=r"^dir must be a string or Path, not <class 'int'>$"):
        NodeType.normalize(1, "dir")


def test_normalize_value_nodetype():
    assert NodeType.normalize("test0", NodeType("dir")) == "test0"
    assert NodeType.normalize("./test1",  NodeType("[str]")) == ["./test1"]


def test_normalize_invalid_type():
    with pytest.raises(ValueError, match=r"^Invalid type specifier: invalid$"):
        NodeType.normalize('1235', 'invalid')


def test_normalize_invalid_int():
    with pytest.raises(ValueError, match=r"^\"a\" unable to convert to int$"):
        NodeType.normalize('a', 'int')


def test_normalize_invalid_list_entry():
    with pytest.raises(ValueError, match=r"^\"a\" unable to convert to int$"):
        NodeType.normalize(['a'], ['int'])


def test_normalize_invalid_float():
    with pytest.raises(ValueError, match=r"^\"a\" unable to convert to float$"):
        NodeType.normalize('a', 'float')


def test_normalize_invalid_bool():
    with pytest.raises(ValueError, match=r"^\"a\" unable to convert to boolean$"):
        NodeType.normalize('a', 'bool')


def test_normalize_invalid_tuple():
    with pytest.raises(ValueError, match=r"^\(a\) does not have 2 entries$"):
        NodeType.normalize('(a)', ("int", "str"))
    with pytest.raises(ValueError, match=r"^\(a\) does not have 2 entries$"):
        NodeType.normalize('a', ("int", "str"))
    with pytest.raises(ValueError, match=r"^\(a\) \(<class 'set'>\) cannot be converted to tuple$"):
        NodeType.normalize(set(['a']), ("int", "str"))
    with pytest.raises(ValueError, match=r"^\(1\) \(<class 'int'>\) cannot be converted to tuple$"):
        NodeType.normalize(1, ("int", "str"))


def test_normalize_invalid_str():
    with pytest.raises(ValueError, match=r'^"<class \'list\'>" unable to convert to str$'):
        NodeType.normalize(list(['a', 'b']), 'str')
    with pytest.raises(ValueError, match=r'^"<class \'set\'>" unable to convert to str$'):
        NodeType.normalize(set(['a', 'b']), 'str')
    with pytest.raises(ValueError, match=r'^"<class \'tuple\'>" unable to convert to str$'):
        NodeType.normalize(tuple(['a', 'b']), 'str')


@pytest.mark.parametrize("sctype", [
    "str",
    "bool",
    "int<0,2,5>",
    "int<0..5>",
    "int<..-5>",
    "int<-5..>",
    "int<..-5,5..>",
    "float<..-5.0,5.0..>",
    "[str]",
    "[int]",
    "(str,int)",
    "(str,int,bool,float,<hello,world>)",
    "[(str,int)]",
    "[<hello,world>]",
    "[int<0,2,5..9>]",
    "{(str,int,int,str)}",
])
def test_str(sctype):
    assert str(NodeType(sctype)) == sctype


def test_str_enum():
    assert str(NodeType("str<hello,world>")) == "<hello,world>"
    assert str(NodeType("[str<hello,world>]")) == "[<hello,world>]"


def test_str_floatrange():
    assert str(NodeType("float<0,2.1,5..9>")) == "float<0.0,2.1,5.0..9.0>"
    assert str(NodeType("[float<0,2.1,5..9>]")) == "[float<0.0,2.1,5.0..9.0>]"


def test_str_invalid():
    with pytest.raises(ValueError, match=r"^<class 'int'> not a recognized type$"):
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
    ("bool", "enum", False),
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
    ("{(str,int<0..5>)}", "int", True),
    ("{(str,int)}", tuple, True),
    ("{(str,int)}", list, False),
    ("{(str,int)}", set, True),
    ("{(str,int)}", "tuple", True),
    ("{(str,int)}", "list", False),
    ("{(str,int)}", "set", True),
    ("{(str,int)}", "bool", False),
    ("(str,int,bool,float,<hello,world>)", "str", True),
    ("(str,int,bool,float,<hello,world>)", "int", True),
    ("(str,int,bool,float,<hello,world>)", "bool", True),
    ("(str,int,bool,float,<hello,world>)", "float", True),
    ("(str,int,bool,float,<hello,world>)", "enum", True),
    ("(str,int,bool,float,<hello,world>)", NodeEnumType, True),
    ("(str,int,bool,float,<hello,world>)", tuple, True),
    ("(str,int,bool,float,<hello,world>)", "tuple", True),
    ("(str,int,bool,float,<hello,world>)", list, False),
    ("(str,int,bool,float,<hello,world>)", "list", False),
    ("(str,int,bool,float,<hello,world>)", "set", False),
    ("(str,int,bool,float,<hello,world>)", set, False),
    # Remaining scalar bases (float/file/dir) matched directly
    ("float", "float", True),
    ("float", "int", False),
    ("file", "file", True),
    ("file", "dir", False),
    ("dir", "dir", True),
    ("dir", "file", False),
    # Enum scalar, via 'enum' token and the NodeEnumType class
    ("<one,two>", "enum", True),
    ("<one,two>", NodeEnumType, True),
    ("<one,two>", "str", False),
    ("int", "enum", False),
    ("[<one,two>]", "enum", True),
    ("[<one,two>]", NodeEnumType, True),
    # Range scalar matches its numeric base, 'range' token, and NodeRangeType
    ("int<0..10>", "int", True),
    ("int<0..10>", "float", False),
    ("int<0..10>", "range", True),
    ("int<0..10>", NodeRangeType, True),
    ("float<0.0..1.0>", "float", True),
    ("int", "range", False),
    # Simple single-element containers, via class and string token (recursing)
    ("[int]", "int", True),
    ("[int]", list, True),
    ("[int]", "list", True),
    ("[int]", set, False),
    ("[int]", "set", False),
    ("{int}", "int", True),
    ("{int}", set, True),
    ("{int}", "set", True),
    ("{int}", list, False),
    ("{int}", "list", False),
    ("[file]", "file", True),
])
def test_contains(sctype, check, expect):
    # Parsed structure and NodeType wrapper inputs must give the same result.
    assert NodeType.contains(NodeType.parse(sctype), check) is expect
    assert NodeType.contains(NodeType(sctype), check) is expect


def test_parse_negative_float_range():
    # Range from -0.5 to 0.5
    parsed = NodeType.parse("float<-0.5..0.5>")
    assert isinstance(parsed, NodeRangeType)
    assert parsed.base == "float"
    assert parsed.values == [(-0.5, 0.5)]


def test_parse_outoforder_float_range():
    # Range from -0.5 to 0.5
    parsed = NodeType.parse("float<0.5..-0.5>")
    assert isinstance(parsed, NodeRangeType)
    assert parsed.base == "float"
    assert parsed.values == [(-0.5, 0.5)]


def test_parse_scientific_notation_range():
    # Range from 1e-5 to 1e-2
    parsed = NodeType.parse("float<1e-5..1e-2>")
    assert isinstance(parsed, NodeRangeType)
    assert parsed.base == "float"
    assert parsed.values == [(1e-5, 1e-2)]
    assert str(parsed) == "float<1e-05..0.01>"


def test_parse_mixed_ranges_and_values():
    # Mixed single values and ranges with negatives
    parsed = NodeType.parse("int<-10,-5,0..5>")
    assert isinstance(parsed, NodeRangeType)
    assert parsed.values == [(-10, -10), (-5, -5), (0, 5)]


def test_normalize_negative_range():
    rnge = NodeType.parse("int<-10..10>")
    assert NodeType.normalize("-5", rnge) == -5
    assert NodeType.normalize("10", rnge) == 10
    assert NodeType.normalize("-10", rnge) == -10
    with pytest.raises(ValueError):
        NodeType.normalize("-11", rnge)


def test_parse_open_range_high():
    # int<0..>
    rnge = NodeType.parse("int<0..>")
    assert isinstance(rnge, NodeRangeType)
    assert rnge.values == [(0, None)]

    assert NodeType.normalize(0, rnge) == 0
    assert NodeType.normalize(100, rnge) == 100
    with pytest.raises(ValueError):
        NodeType.normalize(-1, rnge)


def test_parse_open_negative_range_high():
    # int<-10..>
    rnge = NodeType.parse("int<-10..>")
    assert isinstance(rnge, NodeRangeType)
    assert rnge.values == [(-10, None)]

    assert NodeType.normalize(-10, rnge) == -10
    assert NodeType.normalize(0, rnge) == 0
    with pytest.raises(ValueError):
        NodeType.normalize(-11, rnge)


def test_parse_open_range_low():
    # int<..-5>
    rnge = NodeType.parse("int<..-5>")
    assert isinstance(rnge, NodeRangeType)
    assert rnge.values == [(None, -5)]

    assert NodeType.normalize(-5, rnge) == -5
    assert NodeType.normalize(-100, rnge) == -100
    with pytest.raises(ValueError):
        NodeType.normalize(0, rnge)


def test_parse_open_negative_range_low():
    # int<..-5>
    rnge = NodeType.parse("int<..-5>")
    assert isinstance(rnge, NodeRangeType)
    assert rnge.values == [(None, -5)]

    assert NodeType.normalize(-5, rnge) == -5
    assert NodeType.normalize(-100, rnge) == -100
    with pytest.raises(ValueError):
        NodeType.normalize(0, rnge)


def test_parse_negative_range():
    # int<-10..-5>
    rnge = NodeType.parse("int<-10..-5>")
    assert isinstance(rnge, NodeRangeType)
    assert rnge.values == [(-10, -5)]

    assert NodeType.normalize(-10, rnge) == -10
    assert NodeType.normalize(-7, rnge) == -7
    with pytest.raises(ValueError):
        NodeType.normalize(-11, rnge)
    with pytest.raises(ValueError):
        NodeType.normalize(-4, rnge)


@pytest.mark.parametrize("range_str,expect", [
    ("int<-10..-5>", [(-10, -5)]),
    ("int<-20..-15,..-5>", [(None, -5), (-20, -15)]),
    ("float<-2.5..1.5,..-0.5>", [(None, -0.5), (-2.5, 1.5)]),
])
def test_parse_range(range_str, expect):
    rnge = NodeType.parse(range_str)
    assert isinstance(rnge, NodeRangeType)
    assert rnge.values == expect


def test_range_eq():
    r0 = NodeType.parse("int<-10..-5>")
    r1 = NodeType.parse("float<-10..-5>")

    assert r0 == NodeRangeType("int", (-10, -5))
    assert r0 != r1


@pytest.mark.parametrize("range_str,expect", [
    # Leading decimal point
    ("float<.5..1.5>", [(0.5, 1.5)]),
    ("float<-.5...5>", [(-0.5, 0.5)]),
    # Trailing decimal point
    ("float<1...2.>", [(1.0, 2.0)]),
    ("float<5.>", [(5.0, 5.0)]),
    # Explicit positive sign
    ("float<+1..+2>", [(1.0, 2.0)]),
    # Scientific notation, both cases
    ("float<1E5..2E5>", [(1e5, 2e5)]),
    ("float<1e-5..1e-2>", [(1e-5, 1e-2)]),
    ("float<1E-5..1e-2>", [(1e-5, 1e-2)]),
    ("float<+1.5e3..+2.5e3>", [(1.5e3, 2.5e3)]),
    # Mix of scientific notation single values and ranges
    ("float<1e-5,2e-3..4e-2>", [(1e-5, 1e-5), (0.002, 0.04)]),
])
def test_parse_float_range_formats(range_str, expect):
    """Well-formed floating point range specifiers should parse correctly."""
    parsed = NodeType.parse(range_str)
    assert isinstance(parsed, NodeRangeType)
    assert parsed.base == "float"
    assert parsed.values == expect


@pytest.mark.parametrize("range_str,expect", [
    ("int<+0,+2,+5..+9>", [(0, 0), (2, 2), (5, 9)]),
    ("int<+5..+9>", [(5, 9)]),
])
def test_parse_int_range_formats(range_str, expect):
    """Well-formed integer range specifiers should parse correctly."""
    parsed = NodeType.parse(range_str)
    assert isinstance(parsed, NodeRangeType)
    assert parsed.base == "int"
    assert parsed.values == expect


@pytest.mark.parametrize("range_str,match", [
    # Float value in an int range
    ("int<1.5..2>", r"^invalid literal for int\(\) with base 10: '1\.5'$"),
    ("int<1.5>", r"^invalid literal for int\(\) with base 10: '1\.5'$"),
    ("int<0..2.5>", r"^invalid literal for int\(\) with base 10: '2\.5'$"),
    # Dash used instead of '..' as the range separator
    ("int<5-7>", r"^invalid literal for int\(\) with base 10: '5-7'$"),
    ("float<5-7>", r"^could not convert string to float: '5-7'$"),
    # Non-numeric garbage
    ("float<abc..2>", r"^could not convert string to float: 'abc\.\.2'$"),
    ("int<abc>", r"^invalid literal for int\(\) with base 10: 'abc'$"),
    # Empty range specifier
    ("int<>", r"^invalid literal for int\(\) with base 10: ''$"),
    ("float<>", r"^could not convert string to float: ''$"),
    # Too many dots / malformed decimals
    ("float<1..2..3>", r"^could not convert string to float: '1\.\.2\.\.3'$"),
    ("int<1.2.3>", r"^invalid literal for int\(\) with base 10: '1\.2\.3'$"),
    # Interior whitespace is not stripped by the range regex
    ("int< 0 .. 5 >", r"^invalid literal for int\(\) with base 10: ' 0 \.\. 5 '$"),
])
def test_parse_invalid_range(range_str, match):
    """Poorly formatted numbers inside a range must raise a ValueError."""
    with pytest.raises(ValueError, match=match):
        NodeType.parse(range_str)


@pytest.mark.parametrize("range_str", [
    "int<..>",
    "float<..>",
    "int<..,0..5>",
    "float<1..2,..>",
])
def test_parse_fully_unbounded_range(range_str):
    """A range with both ends open (<..>) is not a valid, bounded range."""
    with pytest.raises(ValueError, match=r"^range cannot be fully unbounded$"):
        NodeType.parse(range_str)


def test_parse_bare_unbounded_enum():
    """A bare <..> with no base type is parsed as an enum, not a range."""
    parsed = NodeType.parse("<..>")
    assert isinstance(parsed, NodeEnumType)
    assert parsed.values == set([".."])


def test_noderange_empty():
    with pytest.raises(ValueError, match=r"^range cannot be empty set$"):
        NodeRangeType("int")


def test_noderange_fully_unbounded():
    with pytest.raises(ValueError, match=r"^range cannot be fully unbounded$"):
        NodeRangeType("int", (None, None))


@pytest.mark.parametrize("range_str,value,expect", [
    ("float<0.0..1.0>", "0.5", 0.5),
    ("float<0.0..1.0>", ".5", 0.5),
    ("float<0.0..1.0>", "5e-1", 0.5),
    ("float<-1.5..1.5>", "-1.5", -1.5),
    ("float<0.0..1.0>", 0.5, 0.5),
])
def test_normalize_float_range_values(range_str, value, expect):
    """Well-formed floats normalize against a float range."""
    assert NodeType.normalize(value, NodeType.parse(range_str)) == expect


@pytest.mark.parametrize("range_str,value,match", [
    # Malformed value fails base conversion before the range check
    ("float<0.0..1.0>", "abc", r"^\"abc\" unable to convert to float$"),
    ("int<0..10>", "1.5", r"^\"1\.5\" unable to convert to int$"),
    ("int<0..10>", "5.0", r"^\"5\.0\" unable to convert to int$"),
    # Well-formed but out of range
    ("float<0.0..1.0>", "1.5", r"^1\.5 is not in range: 0\.0\.\.1\.0$"),
    ("float<0.0..1.0>", "-0.1", r"^-0\.1 is not in range: 0\.0\.\.1\.0$"),
])
def test_normalize_float_range_invalid(range_str, value, match):
    """Poorly formatted or out-of-range values raise on normalize."""
    with pytest.raises(ValueError, match=match):
        NodeType.normalize(value, NodeType.parse(range_str))


@pytest.mark.parametrize("sctype,check,expect", [
    # Scalar exact match
    ("int", "int", True),
    ("int", "float", False),
    ("float", "float", True),
    ("float", "int", False),
    ("str", "str", True),
    ("bool", "bool", True),
    ("file", "file", True),
    ("dir", "dir", True),
    ("file", "dir", False),
    ("str", "enum", False),
    # Range types match on their numeric base
    ("int<0..10>", "int", True),
    ("int<0..10>", "float", False),
    ("float<0.0..1.0>", "float", True),
    ("float<0.0..1.0>", "int", False),
    ("int<0..10>", NodeRangeType, True),
    ("float<0.0..1.0>", NodeRangeType, True),
    ("int", NodeRangeType, False),
    # Enum types match 'enum' or the NodeEnumType class
    ("<one,two,three>", "enum", True),
    ("<one,two,three>", "str", False),
    ("<one,two,three>", NodeEnumType, True),
    ("int", NodeEnumType, False),
    # Containers never match a scalar name (this is the precision contains lacks)
    ("[int]", "int", False),
    ("{int}", "int", False),
    ("(int,int)", "int", False),
    ("[<one,two>]", "enum", False),
    # Containers match their own class only, non-recursively
    ("[int]", list, True),
    ("[int]", set, False),
    ("[int]", tuple, False),
    ("{int}", set, True),
    ("{int}", list, False),
    ("(int,str)", tuple, True),
    ("(int,str)", list, False),
    ("int", list, False),
    ("int", set, False),
    ("int", tuple, False),
    # The same checks expressed as astype string tokens instead of classes
    ("int<0..10>", "range", True),
    ("int", "range", False),
    ("<one,two,three>", "enum", True),
    ("[<one,two>]", "enum", False),
    ("[int]", "list", True),
    ("[int]", "set", False),
    ("[int]", "tuple", False),
    ("{int}", "set", True),
    ("{int}", "list", False),
    ("(int,str)", "tuple", True),
    ("(int,str)", "list", False),
    ("int", "list", False),
    ("int", "set", False),
    ("int", "tuple", False),
])
def test_istype(sctype, check, expect):
    """istype matches the top-level type only, without recursing into containers.

    Checks are exercised both as classes (``list``, ``NodeEnumType``, ...) and
    as the equivalent :meth:`astype` string tokens (``'list'``, ``'enum'``, ...).
    """
    assert NodeType.istype(sctype, check) is expect


def test_istype_multiple_checks():
    """istype accepts several candidate types and matches any of them."""
    assert NodeType.istype("int", "int", "float") is True
    assert NodeType.istype("float", "int", "float") is True
    assert NodeType.istype("str", "int", "float") is False
    assert NodeType.istype("int", "int", "float", "str", "bool") is True
    assert NodeType.istype("[int]", list, set, tuple) is True
    assert NodeType.istype("int", list, set, tuple) is False


def test_istype_no_checks():
    """istype with no candidate types matches nothing."""
    assert NodeType.istype("int") is False
    assert NodeType.istype("[int]") is False


def test_istype_accepts_nodetype_and_type_objects():
    """istype works on NodeType instances and raw parsed type objects."""
    assert NodeType.istype(NodeType("int"), "int") is True
    assert NodeType.istype(NodeType("[int]"), list) is True
    assert NodeType.istype(NodeType.parse("int<0..10>"), "int") is True
    assert NodeType.istype(NodeType.parse("<one,two>"), "enum") is True


@pytest.mark.parametrize("sctype,expect", [
    # Scalars return themselves
    ("int", "int"),
    ("float", "float"),
    ("str", "str"),
    ("bool", "bool"),
    ("file", "file"),
    ("dir", "dir"),
    # Range types collapse to their numeric base
    ("int<0..10>", "int"),
    ("float<0.0..1.0>", "float"),
    # Enum types collapse to 'enum'
    ("<one,two,three>", "enum"),
    # Homogeneous containers return their element base
    ("[int]", "int"),
    ("{str}", "str"),
    ("[file]", "file"),
    ("{dir}", "dir"),
    ("[<one,two>]", "enum"),
    ("[int<0..10>]", "int"),
    ("(int,int)", "int"),
    ("(str,str)", "str"),
    # Nested containers recurse to the leaf
    ("[[int]]", "int"),
    # Heterogeneous tuples have no single base
    ("(str,int)", None),
    ("(int,float)", None),
])
def test_basetype(sctype, expect):
    """basetype unwraps containers and range/enum wrappers to the scalar base."""
    assert NodeType.basetype(sctype) == expect


def test_basetype_accepts_nodetype_and_type_objects():
    """basetype works on NodeType instances and raw parsed type objects."""
    assert NodeType.basetype(NodeType("int")) == "int"
    assert NodeType.basetype(NodeType("[int]")) == "int"
    assert NodeType.basetype(NodeType.parse("int<0..10>")) == "int"
    assert NodeType.basetype(NodeType.parse("(str,int)")) is None


@pytest.mark.parametrize("spec,expect", [
    # String tokens resolve to their classes
    ("list", list),
    ("set", set),
    ("tuple", tuple),
    ("enum", NodeEnumType),
    ("range", NodeRangeType),
    # Scalar names pass through unchanged
    ("int", "int"),
    ("float", "float"),
    ("file", "file"),
    # Unknown strings pass through unchanged
    ("bogus", "bogus"),
    # Classes and instances pass through unchanged
    (list, list),
    (NodeEnumType, NodeEnumType),
    (NodeRangeType, NodeRangeType),
    (enum1, enum1),
])
def test_astype(spec, expect):
    """astype maps friendly tokens to check objects and passes the rest through."""
    assert NodeType.astype(spec) == expect
