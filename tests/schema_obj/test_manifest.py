import pathlib

from siliconcompiler import Schema


def test_manifest():
    schema = Schema()

    schema.set('input', 'rtl', 'verilog', 'foo.v')
    schema.write_manifest('tmp.json')

    schema2 = Schema(manifest='tmp.json')
    assert schema2.get('input', 'rtl', 'verilog') == ['foo.v']

    # Ensure pathlib input works
    schema3 = Schema(manifest=pathlib.Path('tmp.json'))
    assert schema3.get('input', 'rtl', 'verilog') == ['foo.v']
