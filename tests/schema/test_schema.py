from siliconcompiler.schema import Schema
from siliconcompiler.schema.schema_cfg import scparam

def test_list_of_lists():
    cfg = {}
    scparam(cfg, ['test'], sctype='[[str]]', shorthelp='Test')

    schema = Schema(cfg=cfg)
    schema.set('test', [['foo']])

    assert schema.get('test') == [['foo']]
