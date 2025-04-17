import pytest

from pathlib import Path

from siliconcompiler.schema.new.parameter import Parameter, PerNode, Scope


def test_pernode_is_never():
    assert len([val for val in PerNode]) == 3
    assert PerNode.NEVER.is_never()
    assert not PerNode.OPTIONAL.is_never()
    assert not PerNode.REQUIRED.is_never()


@pytest.mark.parametrize("sctype", ("str", "float", "int"))
def test_default_init(sctype):
    param = Parameter(sctype)
    assert param.getdict() == {
        'type': sctype,
        'require': False,
        'scope': 'job',
        'lock': False,
        'switch': [],
        'shorthelp': None,
        'example': [],
        'help': None,
        'notes': None,
        'pernode': 'never',
        'node': {'default': {'default': {'value': None, 'signature': None}}}
    }


@pytest.mark.parametrize("sctype", ("str", "float", "int"))
def test_default_init_list(sctype):
    param = Parameter(f"[{sctype}]")
    assert param.getdict() == {
        'type': f"[{sctype}]",
        'require': False,
        'scope': 'job',
        'lock': False,
        'switch': [],
        'shorthelp': None,
        'example': [],
        'help': None,
        'notes': None,
        'pernode': 'never',
        'node': {'default': {'default': {'value': [], 'signature': []}}}
    }


def test_default_init_file():
    param = Parameter("file")
    assert param.getdict() == {
        'type': 'file',
        'require': False,
        'scope': 'job',
        'lock': False,
        'switch': [],
        'shorthelp': None,
        'example': [],
        'help': None,
        'notes': None,
        'pernode': 'never',
        'copy': False,
        'hashalgo': 'sha256',
        'node': {'default': {'default': {
            'author': [],
            'date': [],
            'filehash': [],
            'package': [],
            'value': None,
            'signature': None}}}
    }


def test_default_init_dir():
    param = Parameter("dir")
    assert param.getdict() == {
        'type': 'dir',
        'require': False,
        'scope': 'job',
        'lock': False,
        'switch': [],
        'shorthelp': None,
        'example': [],
        'help': None,
        'notes': None,
        'pernode': 'never',
        'copy': False,
        'hashalgo': 'sha256',
        'node': {'default': {'default': {
            'filehash': [],
            'package': [],
            'value': None,
            'signature': None}}}
    }


def test_get_invalid_field():
    param = Parameter("str")

    with pytest.raises(ValueError, match='"invalidfield" is not a valid field'):
        param.get(field='invalidfield')


def test_get_fields_str():
    param = Parameter(
        "str",
        scope=Scope.SCRATCH,
        lock=True,
        switch="-test",
        shorthelp="test short",
        example="example1",
        help="long help",
        notes="note",
        pernode=PerNode.OPTIONAL,
        enum=["test0", "test1"],
        unit="nm",
        hashalgo="md5",
        copy=True)

    assert param.get(field='type') == "str"
    assert param.get(field='scope') == Scope.SCRATCH
    assert param.get(field='lock') is True
    assert param.get(field='switch') == ["-test"]
    assert param.get(field='shorthelp') == "test short"
    assert param.get(field='example') == ["example1"]
    assert param.get(field='help') == "long help"
    assert param.get(field='notes') == "note"
    assert param.get(field='pernode') == PerNode.OPTIONAL
    assert param.get(field='enum') is None
    assert param.get(field='unit') is None
    assert param.get(field='hashalgo') is None
    assert param.get(field='copy') is None
    assert param.get(field='require') is False


def test_get_fields_int():
    param = Parameter(
        "int",
        scope=Scope.SCRATCH,
        lock=True,
        switch="-test",
        shorthelp="test short",
        example="example1",
        help="long help",
        notes="note",
        pernode=PerNode.OPTIONAL,
        enum=["test0", "test1"],
        unit="nm",
        hashalgo="md5",
        copy=True)

    assert param.get(field='type') == "int"
    assert param.get(field='scope') == Scope.SCRATCH
    assert param.get(field='lock') is True
    assert param.get(field='switch') == ["-test"]
    assert param.get(field='shorthelp') == "test short"
    assert param.get(field='example') == ["example1"]
    assert param.get(field='help') == "long help"
    assert param.get(field='notes') == "note"
    assert param.get(field='pernode') == PerNode.OPTIONAL
    assert param.get(field='enum') is None
    assert param.get(field='unit') == "nm"
    assert param.get(field='hashalgo') is None
    assert param.get(field='copy') is None
    assert param.get(field='require') is False


def test_get_fields_float():
    param = Parameter(
        "float",
        scope=Scope.SCRATCH,
        lock=True,
        switch="-test",
        shorthelp="test short",
        example="example1",
        help="long help",
        notes="note",
        pernode=PerNode.OPTIONAL,
        enum=["test0", "test1"],
        unit="nm",
        hashalgo="md5",
        copy=True)

    assert param.get(field='type') == "float"
    assert param.get(field='scope') == Scope.SCRATCH
    assert param.get(field='lock') is True
    assert param.get(field='switch') == ["-test"]
    assert param.get(field='shorthelp') == "test short"
    assert param.get(field='example') == ["example1"]
    assert param.get(field='help') == "long help"
    assert param.get(field='notes') == "note"
    assert param.get(field='pernode') == PerNode.OPTIONAL
    assert param.get(field='enum') is None
    assert param.get(field='unit') == "nm"
    assert param.get(field='hashalgo') is None
    assert param.get(field='copy') is None
    assert param.get(field='require') is False


def test_get_fields_file():
    param = Parameter(
        "file",
        scope=Scope.SCRATCH,
        lock=True,
        switch="-test",
        shorthelp="test short",
        example="example1",
        help="long help",
        notes="note",
        pernode=PerNode.OPTIONAL,
        enum=["test0", "test1"],
        unit="nm",
        hashalgo="md5",
        copy=True)

    assert param.get(field='type') == "file"
    assert param.get(field='scope') == Scope.SCRATCH
    assert param.get(field='lock') is True
    assert param.get(field='switch') == ["-test"]
    assert param.get(field='shorthelp') == "test short"
    assert param.get(field='example') == ["example1"]
    assert param.get(field='help') == "long help"
    assert param.get(field='notes') == "note"
    assert param.get(field='pernode') == PerNode.OPTIONAL
    assert param.get(field='enum') is None
    assert param.get(field='unit') is None
    assert param.get(field='hashalgo') == "md5"
    assert param.get(field='copy') is True
    assert param.get(field='require') is False


def test_get_fields_dir():
    param = Parameter(
        "dir",
        scope=Scope.SCRATCH,
        lock=True,
        switch="-test",
        shorthelp="test short",
        example="example1",
        help="long help",
        notes="note",
        pernode=PerNode.OPTIONAL,
        enum=["test0", "test1"],
        unit="nm",
        hashalgo="md5",
        copy=True)

    assert param.get(field='type') == "dir"
    assert param.get(field='scope') == Scope.SCRATCH
    assert param.get(field='lock') is True
    assert param.get(field='switch') == ["-test"]
    assert param.get(field='shorthelp') == "test short"
    assert param.get(field='example') == ["example1"]
    assert param.get(field='help') == "long help"
    assert param.get(field='notes') == "note"
    assert param.get(field='pernode') == PerNode.OPTIONAL
    assert param.get(field='enum') is None
    assert param.get(field='unit') is None
    assert param.get(field='hashalgo') == "md5"
    assert param.get(field='copy') is True
    assert param.get(field='require') is False


def test_get_fields_enum():
    param = Parameter(
        "enum",
        scope=Scope.SCRATCH,
        lock=True,
        switch="-test",
        shorthelp="test short",
        example="example1",
        help="long help",
        notes="note",
        pernode=PerNode.OPTIONAL,
        enum=["test0", "test1"],
        unit='nm',
        hashalgo="md5",
        copy=True)

    assert param.get(field='type') == "enum"
    assert param.get(field='scope') == Scope.SCRATCH
    assert param.get(field='lock') is True
    assert param.get(field='switch') == ["-test"]
    assert param.get(field='shorthelp') == "test short"
    assert param.get(field='example') == ["example1"]
    assert param.get(field='help') == "long help"
    assert param.get(field='notes') == "note"
    assert param.get(field='pernode') == PerNode.OPTIONAL
    assert param.get(field='enum') == ["test0", "test1"]
    assert param.get(field='unit') is None
    assert param.get(field='hashalgo') is None
    assert param.get(field='copy') is None
    assert param.get(field='require') is False


def test_add_fields_enum():
    param = Parameter(
        "[enum]",
        enum=["test0", "test1"])

    assert param.add("test2", field="enum")
    assert param.get(field='enum') == ["test0", "test1", "test2"]

    assert param.add("test2", field="switch")
    assert param.get(field='switch') == ["test2"]

    assert param.add("test3", field="example")
    assert param.get(field='example') == ["test3"]

    with pytest.raises(ValueError, match='"invalid" is not a valid field'):
        param.add("test3", field="invalid")


def test_from_dict_round_trip():
    param = Parameter(
        "file",
        scope=Scope.SCRATCH,
        lock=True,
        switch="-test",
        shorthelp="test short",
        example="example1",
        help="long help",
        pernode=PerNode.OPTIONAL,
        enum=["test0", "test1"],
        unit="nm",
        hashalgo="md5",
        copy=True)

    param_check = Parameter.from_dict(param.getdict(), [], None)
    assert param.getdict() == param_check.getdict()


def test_from_dict_round_trip_tuple():
    param = Parameter(
        "(str,int)",
        scope=Scope.SCRATCH,
        switch="-test",
        shorthelp="test short",
        example="example1",
        help="long help",
        pernode=PerNode.OPTIONAL,
        enum=["test0", "test1"],
        unit="nm",
        hashalgo="md5",
        copy=True)

    param.set(("test", 1))
    param.set(("step", 2), step="teststep", index="0")

    param_check = Parameter.from_dict(param.getdict(), [], None)
    assert param.getdict() == param_check.getdict()

    assert param_check.get() == ("test", 1)
    assert param_check.get(step="teststep", index="0") == ("step", 2)


def test_from_dict_locked():
    param = Parameter(
        "(str,int)",
        scope=Scope.SCRATCH,
        switch="-test",
        shorthelp="test short",
        example="example1",
        help="long help",
        pernode=PerNode.OPTIONAL,
        enum=["test0", "test1"],
        unit="nm",
        hashalgo="md5",
        copy=True)
    param_check = Parameter(
        "(str,int)",
        scope=Scope.SCRATCH,
        lock=True,
        switch="-test",
        shorthelp="test short",
        example="example1",
        help="long help",
        pernode=PerNode.OPTIONAL,
        enum=["test0", "test1"],
        unit="nm",
        hashalgo="md5",
        copy=True)

    param.set(("test", 1))
    param.set(("step", 2), step="teststep", index="0")

    expect = param_check.getdict()
    param_check._from_dict(param.getdict(), [], None)

    assert param.getdict() != param_check.getdict()
    assert expect == param_check.getdict()


def test_list_of_lists_str():
    param = Parameter("[[str]]")
    param.set([['foo']])

    assert param.get() == [['foo']]


def test_list_of_lists_int():
    param = Parameter("[[int]]")
    param.set([['1']])

    assert param.get() == [[1]]


def test_list_of_bools():
    param = Parameter("[bool]")

    param.set([True, False])

    assert param.get() == [True, False]


def test_list_of_bools_from_str():
    param = Parameter("[bool]")

    param.set(['True', 'False'])

    assert param.get() == [True, False]


def test_list_of_tuples_tuple_input():
    param = Parameter("[(str,str)]")

    param.set(('import', '0'))
    assert param.get() == [('import', '0')]


def test_list_of_tuples_list_tuple_input():
    param = Parameter("[(str,str)]")

    param.set([('import', '0')])
    assert param.get() == [('import', '0')]


def test_list_of_tuples_list_input():
    param = Parameter("[(str,str)]")

    param.set(['import', '0'])
    assert param.get() == [('import', '0')]


def test_pernode_mandatory_get():
    param = Parameter("str", pernode=PerNode.REQUIRED)

    param.set("foo", step="test", index="0")
    assert param.get(step="test", index="0") == "foo"

    with pytest.raises(KeyError):
        param.get()


def test_pernode_mandatory_set():
    param = Parameter("str", pernode=PerNode.REQUIRED)

    with pytest.raises(KeyError, match="'step and index are required'"):
        param.set("foo")

    param.set("foo", step="test", index="0")
    assert param.get(step="test", index="0") == "foo"


def test_pernode_mandatory_add():
    param = Parameter("[str]", pernode=PerNode.REQUIRED)

    with pytest.raises(KeyError, match="'step and index are required'"):
        param.add("foo")

    param.add("foo", step="test", index="0")
    assert param.get(step="test", index="0") == ["foo"]


def test_is_empty():
    param = Parameter("str")

    assert param.is_empty()
    param.set("1.0")
    assert not param.is_empty()


def test_is_set():
    param = Parameter("str")

    assert not param.is_set()
    param.set("1.0")
    assert param.is_set()


def test_is_list():
    param = Parameter("str")
    assert not param.is_list()

    param = Parameter("[str]")
    assert param.is_list()


def test_getvalues():
    param = Parameter("str", defvalue="test", pernode=PerNode.OPTIONAL)

    assert param.getvalues() == [('test', None, None)]
    assert param.getvalues(return_defvalue=False) == []

    param.set("test0")
    param.set("test1", step="step")
    param.set("test2", step="step", index="0")

    assert param.getvalues() == [
        ('test0', None, None),
        ('test1', 'step', None),
        ('test2', 'step', '0')
    ]
    assert param.getvalues(return_defvalue=False) == [
        ('test0', None, None),
        ('test1', 'step', None),
        ('test2', 'step', '0')
    ]


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
    param = Parameter(type)
    if expect in (True, False, None):
        assert param.normalize(value) is expect
    else:
        assert param.normalize(value) == expect


def test_normalize_value_enum():
    param = Parameter("enum", enum=["test0", "test1", "test2"])
    assert param.normalize("test0") == "test0"
    assert param.normalize("test1") == "test1"
    assert param.normalize("test2") == "test2"

    with pytest.raises(ValueError, match="test3 is not a member of: test0, test1, test2"):
        param.normalize("test3")

    with pytest.raises(TypeError, match="enum must be a string, not a <class 'int'>"):
        param.normalize(1)


def test_normalize_value_file():
    param = Parameter("file")
    assert param.normalize("test0") == "test0"
    assert param.normalize("./test1") == "./test1"
    assert param.normalize(Path("./test2")) == "test2"

    with pytest.raises(TypeError, match="file must be a string or Path, not <class 'int'>"):
        param.normalize(1)


def test_normalize_value_dir():
    param = Parameter("dir")
    assert param.normalize("test0") == "test0"
    assert param.normalize("./test1") == "./test1"
    assert param.normalize(Path("./test2")) == "test2"

    with pytest.raises(TypeError, match="dir must be a string or Path, not <class 'int'>"):
        param.normalize(1)


def test_normalize_fields_scalar():
    param = Parameter("file")

    assert param.normalize("dir", field='type') == "dir"
    assert param.normalize("global", field='scope') == Scope.GLOBAL
    assert param.normalize("scratch", field='scope') == Scope.SCRATCH
    with pytest.raises(TypeError, match="invalid must be a member of global, job, scratch"):
        assert param.normalize("invalid", field='scope')
    assert param.normalize('t', field='lock') is True
    assert param.normalize("-test", field='switch') == ["-test"]
    assert param.normalize("test short", field='shorthelp') == "test short"
    assert param.normalize("example1", field='example') == ["example1"]
    assert param.normalize("long help", field='help') == "long help"
    assert param.normalize("optional", field='pernode') == PerNode.OPTIONAL
    assert param.normalize("never", field='pernode') == PerNode.NEVER
    with pytest.raises(TypeError, match="invalid must be a member of never, optional, required"):
        assert param.normalize("invalid", field='pernode')
    assert param.normalize("test", field='enum') == ["test"]
    assert param.normalize("nm", field='unit') == "nm"
    assert param.normalize("md5", field='hashalgo') == "md5"
    assert param.normalize('t', field='copy') is True
    assert param.normalize('f', field='require') is False
    assert param.normalize('1235', field='filehash') == '1235'
    assert param.normalize('1235', field='package') == '1235'
    assert param.normalize('1235', field='date') == '1235'
    assert param.normalize('1235', field='author') == ['1235']
    assert param.normalize('1235', field='signature') == '1235'


def test_normalize_fields_list():
    param = Parameter("[file]")

    assert param.normalize("dir", field='type') == "dir"
    assert param.normalize("global", field='scope') == Scope.GLOBAL
    assert param.normalize("scratch", field='scope') == Scope.SCRATCH
    with pytest.raises(TypeError, match="invalid must be a member of global, job, scratch"):
        assert param.normalize("invalid", field='scope')
    assert param.normalize('t', field='lock') is True
    assert param.normalize("-test", field='switch') == ["-test"]
    assert param.normalize("test short", field='shorthelp') == "test short"
    assert param.normalize("example1", field='example') == ["example1"]
    assert param.normalize("long help", field='help') == "long help"
    assert param.normalize("optional", field='pernode') == PerNode.OPTIONAL
    assert param.normalize("never", field='pernode') == PerNode.NEVER
    with pytest.raises(TypeError, match="invalid must be a member of never, optional, required"):
        assert param.normalize("invalid", field='pernode')
    assert param.normalize("test", field='enum') == ["test"]
    assert param.normalize("nm", field='unit') == "nm"
    assert param.normalize("md5", field='hashalgo') == "md5"
    assert param.normalize('t', field='copy') is True
    assert param.normalize('f', field='require') is False

    assert param.normalize('1235', field='filehash') == ['1235']
    assert param.normalize('1235', field='package') == ['1235']
    assert param.normalize('1235', field='date') == ['1235']
    assert param.normalize('1235', field='author') == ['1235']
    assert param.normalize('1235', field='signature') == ['1235']


def test_normalize_invalid_type():
    param = Parameter("invalid")

    with pytest.raises(ValueError, match="Invalid type specifier: invalid"):
        param.normalize('1235')


def test_str():
    param = Parameter("str", pernode=PerNode.OPTIONAL)

    assert str(param) == "{'default': {'default': {'value': None, 'signature': None}}}"

    assert param.set("test")
    assert str(param) == "{'default': {'default': {'value': None, 'signature': None}}, " \
                         "'global': {'global': {'value': 'test', 'signature': None}}}"

    assert param.set("test", step="teststep")
    assert str(param) == "{'default': {'default': {'value': None, 'signature': None}}, " \
                         "'global': {'global': {'value': 'test', 'signature': None}}, " \
                         "'teststep': {'global': {'value': 'test', 'signature': None}}}"


def test_int_as_index():
    param = Parameter("str", pernode=PerNode.OPTIONAL)

    assert param.set("notthis", step="teststep")
    assert param.set("test", step="teststep", index=1)
    assert param.get(step="teststep", index=0) == "notthis"
    assert param.get(step="teststep", index=1) == "test"


def test_copy():
    param = Parameter("enum", enum=["test"], pernode=PerNode.OPTIONAL)

    copy_param = param.copy()

    assert param is not copy_param

    assert param.getdict() == copy_param.getdict()


def test_tcl_optional():
    param = Parameter("str", pernode=PerNode.OPTIONAL)

    assert param.set("test0")
    assert param.set("test1", step="step")
    assert param.set("test2", step="step", index="0")

    assert param.gettcl() == '"test0"'
    assert param.gettcl(step="step") == '"test1"'
    assert param.gettcl(step="step", index="0") == '"test2"'


def test_tcl_required():
    param = Parameter("str", pernode=PerNode.REQUIRED)

    assert param.set("test1", step="step", index="0")
    assert param.set("test2", step="step", index="1")

    assert param.gettcl() is None
    assert param.gettcl(step="step", index="0") == '"test1"'
    assert param.gettcl(step="step", index="1") == '"test2"'


def test_tcl_never():
    param = Parameter("str", pernode=PerNode.NEVER)

    assert param.set("test0")

    assert param.gettcl() == '"test0"'


def test_tcl_empty():
    param = Parameter("str")

    assert param.gettcl() == ''


def test_tcl_int():
    param = Parameter("int")

    assert param.set(3)

    assert param.gettcl() == '3'


def test_tcl_float():
    param = Parameter("float")

    assert param.set(3.5)

    assert param.gettcl() == '3.5'


def test_tcl_list():
    param = Parameter("[float]")

    assert param.add(3.5)
    assert param.add(4.5)

    assert param.gettcl() == '[list 3.5 4.5]'


def test_tcl_tuple():
    param = Parameter("(float,int)")

    assert param.set((3.5, 2))

    assert param.gettcl() == '[list 3.5 2]'


def test_tcl_list_tuple():
    param = Parameter("[(float,int)]")

    assert param.add((3.5, 2))
    assert param.add((5.5, 5))

    assert param.gettcl() == '[list [list 3.5 2] [list 5.5 5]]'


def test_unset():
    param = Parameter("bool", pernode=PerNode.NEVER)
    assert param.get() is False
    param.set(True)
    assert param.get() is True

    # Clearing a parameter resets it to default value
    param.unset()
    assert param.get() is False

    # Able to set a keypath after it's been cleared even if clobber=False
    assert param.set(True, clobber=False)
    assert param.get() is True


def test_unset_clear_fields():
    '''Ensure unset() clears pernode-fields other than value'''
    param = Parameter("[file]", pernode=PerNode.OPTIONAL)

    param.set('foo.txt')
    param.set('abc123', field='filehash')
    param.unset()

    # arbitrary step/index to avoid error
    assert param.get(step='syn', index=0) == []
    assert param.get(step='syn', index=0, field='filehash') == []


def test_unset_required_pernode():
    param = Parameter("int", pernode=PerNode.REQUIRED)
    param.set(5, step='syn', index=0)
    param.unset(step='syn', index=0)

    assert param.get(step='syn', index=0) is None

    param.set(6, step='syn', index=0, clobber=False)

    assert param.get(step='syn', index=0) == 6


def test_unset_optional_pernode():
    param = Parameter("[str]", pernode=PerNode.OPTIONAL)
    assert param.set('default_lib')
    assert param.get(step='syn', index=0) == ['default_lib']

    assert param.set('syn_lib', step='syn', index=0)
    assert param.get(step='syn', index=0) == ['syn_lib']

    param.unset(step='syn', index=0)
    param.unset(step='syn', index=1)
    assert param.get(step='syn', index=0) == ['default_lib']
    assert param.get() == ['default_lib']

    assert not param.set('syn_lib', step='syn', index=0, clobber=False)
    assert param.get(step='syn', index=0) == ['default_lib']


def test_unset_lock():
    param = Parameter("[str]", pernode=PerNode.OPTIONAL)
    assert param.set('default_lib')
    assert param.get(step='syn', index=0) == ['default_lib']

    assert param.set(True, field='lock')

    param.unset(step='syn', index=0)
    assert param.get(step='syn', index=0) == ['default_lib']
    assert param.get() == ['default_lib']
