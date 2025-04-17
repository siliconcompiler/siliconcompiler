import pytest

from siliconcompiler.schema.new.parameter import Parameter, PerNode


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
