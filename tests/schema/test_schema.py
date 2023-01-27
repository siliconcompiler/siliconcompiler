import pytest

from siliconcompiler.core import SiliconCompilerError
from siliconcompiler.schema import Schema
from siliconcompiler.schema.schema_cfg import scparam

def test_list_of_lists():
    cfg = {}
    scparam(cfg, ['test'], sctype='[[str]]', shorthelp='Test')

    schema = Schema(cfg=cfg)
    schema.set('test', [['foo']])

    assert schema.get('test') == [['foo']]

def test_pernode_mandatory():
    cfg = {}
    scparam(cfg, ['test'], sctype='str', shorthelp='Test', pernode='mandatory')

    schema = Schema(cfg=cfg)

    # Should fail
    with pytest.raises(ValueError):
        schema.set('test', 'foo')

    # Should succeed
    assert schema.set('test', 'foo', step='syn', index=0)
