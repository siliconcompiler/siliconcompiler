import pathlib
import pytest

from siliconcompiler.schema import Schema


def test_manifest():
    schema = Schema()

    schema.set('input', 'rtl', 'verilog', 'foo.v')
    with open('tmp.json', 'w') as f:
        schema.write_json(f)

    schema2 = Schema(manifest='tmp.json')
    assert schema2.get('input', 'rtl', 'verilog') == ['foo.v']

    # Ensure pathlib input works
    schema3 = Schema(manifest=pathlib.Path('tmp.json'))
    assert schema3.get('input', 'rtl', 'verilog') == ['foo.v']


def test_read_manifest_with_allow_missing_keys():
    schema = Schema()

    schema.set('input', 'rtl', 'verilog', 'foo.v')
    schema.cfg['testing'] = schema.getdict('input')
    with open('tmp.json', 'w') as f:
        schema.write_json(f)

    schema2 = Schema()
    schema2.read_manifest('tmp.json', allow_missing_keys=True)


def test_read_manifest_with_disallow_missing_keys():
    schema = Schema()

    schema.set('input', 'rtl', 'verilog', 'foo.v')
    schema.cfg['testing'] = schema.getdict('input')
    with open('tmp.json', 'w') as f:
        schema.write_json(f)

    schema2 = Schema()
    with pytest.raises(ValueError):
        schema2.read_manifest('tmp.json', allow_missing_keys=False)
