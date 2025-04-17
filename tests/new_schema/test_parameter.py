import pytest

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
    assert param.get(field='pernode') == PerNode.OPTIONAL
    assert param.get(field='enum') == ["test0", "test1"]
    assert param.get(field='unit') is None
    assert param.get(field='hashalgo') is None
    assert param.get(field='copy') is None
    assert param.get(field='require') is False


def test_from_dict_rount_trip():
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
