import pytest

from siliconcompiler.schema.new.parameter import Parameter, PerNode, Scope


def test_pernode_is_never():
    assert len([val for val in PerNode]) == 3
    assert PerNode.NEVER.is_never()
    assert not PerNode.OPTIONAL.is_never()
    assert not PerNode.REQUIRED.is_never()


@pytest.mark.parametrize("sctype", ("str", "float"))
def test_default_init(sctype):
    param = Parameter(sctype)
    assert param.getdict() == {
        'type': sctype,
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


def test_default_init_file():
    param = Parameter("file")
    assert param.getdict() == {
        'type': 'file',
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
