# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import pytest
import os
import siliconcompiler
from siliconcompiler import sc_open


def test_hash_files():
    chip = siliconcompiler.Chip('top')

    chip.load_target("freepdk45_demo")
    chip.write_manifest("raw.json")
    allkeys = chip.allkeys()
    for keypath in allkeys:
        if 'default' in keypath:
            continue
        sc_type = chip.get(*keypath, field='type')
        if 'file' in sc_type:
            for vals, step, index in chip.schema._getvals(*keypath):
                hashes = chip.hash_files(*keypath, step=step, index=index)
                schema_hashes = chip.schema.get(*keypath, step=step, index=index, field='filehash')
                assert hashes == schema_hashes
                if sc_type.startswith('['):
                    assert len(hashes) == len(vals)
    chip.write_manifest("hashed.json")


def test_err_mismatch():
    chip = siliconcompiler.Chip('top')

    # Necessary due to find_files() quirk, we need a flow w/ an import step
    chip.load_target('freepdk45_demo')

    # Create foo.txt and compute its hash
    with open('foo.txt', 'w', newline='\n') as f:
        f.write('foobar\n')
    chip.set('input', 'rtl', 'verilog', 'foo.txt')
    assert chip.hash_files('input', 'rtl', 'verilog') == \
        ['aec070645fe53ee3b3763059376134f058cc337247c978add178b6ccdfb0019f']

    # Change foo.txt
    with open('foo.txt', 'w', newline='\n') as f:
        f.write('FOObar\n')

    with pytest.raises(siliconcompiler.SiliconCompilerError):
        # foo.txt is changed, so should trigger error
        chip.hash_files('input', 'rtl', 'verilog', update=False)

    # Restore foo.txt
    with open('foo.txt', 'w', newline='\n') as f:
        f.write('foobar\n')

    # No error since foo.txt was restored, and update=False in previous call
    # ensures original hash wasn't overwritten
    assert chip.hash_files('input', 'rtl', 'verilog', update=False) == \
        ['aec070645fe53ee3b3763059376134f058cc337247c978add178b6ccdfb0019f']


@pytest.mark.parametrize('algorithm,expected', [
    ('md5', '14758f1afd44c09b7992073ccf00b43d'),
    ('sha1', '988881adc9fc3655077dc2d4d757d480b5ea0e11'),
    ('sha224', '90a81bdaa85b5d9dfc4c0cd89d9edaf93255d5f4160cd67bead46a91'),
    ('sha256', 'aec070645fe53ee3b3763059376134f058cc337247c978add178b6ccdfb0019f'),
    ('sha384', '190d8045dc5875c1004e4dd31f13194eea25043cf9ffc40550cca30fdcae20f8d7eed05f3c94058b206329dbe8d2312e'),  # noqa E501
    ('sha512', 'e79b8ad22b34a54be999f4eadde2ee895c208d4b3d83f1954b61255d2556a8b73773c0dc0210aa044ffcca6834839460959cbc9f73d3079262fc8bc935d46262')])  # noqa E501
def test_changed_algorithm(algorithm, expected):

    # Create foo.txt and compute its hash
    with open('foo.txt', 'w', newline='\n') as f:
        f.write('foobar\n')

    chip = siliconcompiler.Chip('top')

    # Necessary due to find_files() quirk, we need a flow w/ an import step
    chip.load_target('freepdk45_demo')
    chip.set('input', 'rtl', 'verilog', 'foo.txt')
    chip.set('input', 'rtl', 'verilog', algorithm, field='hashalgo')
    print(chip.hash_files('input', 'rtl', 'verilog'))
    assert chip.hash_files('input', 'rtl', 'verilog') == [expected]


def test_directory_hash():
    os.makedirs('test1', exist_ok=True)
    # Create foo.txt and compute its hash
    with open('test1/foo.txt', 'w', newline='\n') as f:
        f.write('foobar\n')
    with open('test1/foo1.txt', 'w', newline='\n') as f:
        f.write('foobar\n')

    chip = siliconcompiler.Chip('top')

    # Necessary due to find_files() quirk, we need a flow w/ an import step
    chip.load_target('freepdk45_demo')
    chip.set('option', 'idir', 'test1')
    print(chip.hash_files('option', 'idir'))
    assert chip.hash_files('option', 'idir') == \
        ['6d9a946394ed8d2815169e42e225efc52cf6f92aa9f50e88fd05c0750d6c336c']


def test_directory_hash_rename():
    os.makedirs('test1', exist_ok=True)
    # Create foo.txt and compute its hash
    with open('test1/foo.txt', 'w', newline='\n') as f:
        f.write('foobar\n')
    with open('test1/foo1.txt', 'w', newline='\n') as f:
        f.write('foobar\n')

    chip = siliconcompiler.Chip('top')

    # Necessary due to find_files() quirk, we need a flow w/ an import step
    chip.load_target('freepdk45_demo')
    chip.set('option', 'idir', 'test1')

    assert chip.hash_files('option', 'idir') == \
        ['6d9a946394ed8d2815169e42e225efc52cf6f92aa9f50e88fd05c0750d6c336c']

    os.rename('test1/foo1.txt', 'test1/foo2.txt')
    print(chip.hash_files('option', 'idir', check=False))
    assert chip.hash_files('option', 'idir', check=False) == \
        ['e054f2dbdb854c8b7c96eca9b0e41acdaedc1f66b816c868338386d474b53a13']


def test_hash_no_check():
    # Create foo.txt and compute its hash
    with open('foo.txt', 'w', newline='\n') as f:
        f.write('foobar\n')

    chip = siliconcompiler.Chip('top')

    # Necessary due to find_files() quirk, we need a flow w/ an import step
    chip.load_target('freepdk45_demo')
    chip.set('input', 'rtl', 'verilog', 'foo.txt')
    print(chip.hash_files('input', 'rtl', 'verilog'))
    assert chip.hash_files('input', 'rtl', 'verilog') == \
        ['aec070645fe53ee3b3763059376134f058cc337247c978add178b6ccdfb0019f']

    # Create foo.txt and compute its new hash
    with open('foo.txt', 'w', newline='\n') as f:
        f.write('foobar1\n')
    assert chip.hash_files('input', 'rtl', 'verilog', check=False) == \
        ['4908f9d57d35771d56a6326334f6dca3f6940e738f2d142e4ee2e5c34017f118']
    assert chip.get('input', 'rtl', 'verilog', field='filehash') == \
        ['4908f9d57d35771d56a6326334f6dca3f6940e738f2d142e4ee2e5c34017f118']


def test_hash_no_update():
    # Create foo.txt and compute its hash
    with open('foo.txt', 'w', newline='\n') as f:
        f.write('foobar\n')

    chip = siliconcompiler.Chip('top')

    # Necessary due to find_files() quirk, we need a flow w/ an import step
    chip.load_target('freepdk45_demo')
    chip.set('input', 'rtl', 'verilog', 'foo.txt')
    print(chip.hash_files('input', 'rtl', 'verilog'))
    assert chip.hash_files('input', 'rtl', 'verilog') == \
        ['aec070645fe53ee3b3763059376134f058cc337247c978add178b6ccdfb0019f']

    # Create foo.txt and compute its new hash
    with open('foo.txt', 'w', newline='\n') as f:
        f.write('foobar1\n')

    assert chip.hash_files('input', 'rtl', 'verilog', update=False, check=False) == \
        ['4908f9d57d35771d56a6326334f6dca3f6940e738f2d142e4ee2e5c34017f118']
    assert chip.get('input', 'rtl', 'verilog', field='filehash') == \
        ['aec070645fe53ee3b3763059376134f058cc337247c978add178b6ccdfb0019f']


def test_hash_global_file():
    # Create foo.txt and compute its hash
    with open('foo.txt', 'w', newline='\n') as f:
        f.write('foobar\n')

    chip = siliconcompiler.Chip('top')

    # Necessary due to find_files() quirk, we need a flow w/ an import step
    chip.load_target('freepdk45_demo')
    chip.set('input', 'rtl', 'verilog', 'foo.txt')
    assert chip.hash_files('input', 'rtl', 'verilog', step='test', index=0) == \
        ['aec070645fe53ee3b3763059376134f058cc337247c978add178b6ccdfb0019f']
    assert chip.get('input', 'rtl', 'verilog', field='filehash', step='test', index=0) == \
        ['aec070645fe53ee3b3763059376134f058cc337247c978add178b6ccdfb0019f']
    assert chip.get('input', 'rtl', 'verilog', field='filehash', step='test') == \
        ['aec070645fe53ee3b3763059376134f058cc337247c978add178b6ccdfb0019f']
    assert chip.get('input', 'rtl', 'verilog', field='filehash') == \
        ['aec070645fe53ee3b3763059376134f058cc337247c978add178b6ccdfb0019f']


def test_hash_step_file():
    # Create foo.txt and compute its hash
    with open('foo.txt', 'w', newline='\n') as f:
        f.write('foobar\n')

    chip = siliconcompiler.Chip('top')

    # Necessary due to find_files() quirk, we need a flow w/ an import step
    chip.load_target('freepdk45_demo')
    chip.set('input', 'rtl', 'verilog', 'foo.txt', step='test')
    assert chip.hash_files('input', 'rtl', 'verilog', step='test', index=0) == \
        ['aec070645fe53ee3b3763059376134f058cc337247c978add178b6ccdfb0019f']
    assert chip.get('input', 'rtl', 'verilog', field='filehash', step='test', index=0) == \
        ['aec070645fe53ee3b3763059376134f058cc337247c978add178b6ccdfb0019f']
    assert chip.get('input', 'rtl', 'verilog', field='filehash', step='test') == \
        ['aec070645fe53ee3b3763059376134f058cc337247c978add178b6ccdfb0019f']
    assert chip.get('input', 'rtl', 'verilog', field='filehash') == []


def test_hash_node_file():
    # Create foo.txt and compute its hash
    with open('foo.txt', 'w', newline='\n') as f:
        f.write('foobar\n')

    chip = siliconcompiler.Chip('top')

    # Necessary due to find_files() quirk, we need a flow w/ an import step
    chip.load_target('freepdk45_demo')
    chip.set('input', 'rtl', 'verilog', 'foo.txt', step='test', index=0)
    assert chip.hash_files('input', 'rtl', 'verilog', step='test', index=0) == \
        ['aec070645fe53ee3b3763059376134f058cc337247c978add178b6ccdfb0019f']
    assert chip.get('input', 'rtl', 'verilog', field='filehash', step='test', index=0) == \
        ['aec070645fe53ee3b3763059376134f058cc337247c978add178b6ccdfb0019f']
    assert chip.get('input', 'rtl', 'verilog', field='filehash', step='test') == []
    assert chip.get('input', 'rtl', 'verilog', field='filehash') == []


@pytest.mark.quick
@pytest.mark.eda
@pytest.mark.timeout(300)
def test_error_in_run_while_hashing(gcd_chip):
    # Set a value that will cause place to break
    gcd_chip.set('tool', 'openroad', 'task', 'place', 'var', 'place_density', 'asdf',
                 step='place', index='0')

    gcd_chip.set('option', 'to', 'cts')
    gcd_chip.set('option', 'hash', True)

    with pytest.raises(siliconcompiler.SiliconCompilerError):
        gcd_chip.run()

    schema = siliconcompiler.Schema(
        manifest=os.path.join(gcd_chip.getworkdir(step='floorplan', index='0'),
                              'outputs', f'{gcd_chip.design}.pkg.json'))
    assert len(schema.get('tool', 'openroad', 'task', 'floorplan', 'output',
                          field='filehash', step='floorplan', index='0')) == 4

    schema = siliconcompiler.Schema(
        manifest=os.path.join(gcd_chip.getworkdir(step='place', index='0'),
                              'outputs', f'{gcd_chip.design}.pkg.json'))
    assert len(schema.get('tool', 'openroad', 'task', 'place', 'output',
                          field='filehash', step='place', index='0')) == 0


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(150)
def test_rerunning_with_hashing():
    chip = siliconcompiler.Chip('')
    chip.load_target('asic_demo')

    chip.set('option', 'hash', True)
    chip.set('option', 'to', 'floorplan')

    chip.run()
    chip.run()


def test_hash_no_cache():
    # Create foo.txt and compute its hash
    with open('foo.txt', 'w', newline='\n') as f:
        f.write('foobar\n')

    chip = siliconcompiler.Chip('top')

    # Necessary due to find_files() quirk, we need a flow w/ an import step
    chip.load_target('freepdk45_demo')
    chip.set('input', 'rtl', 'verilog', 'foo.txt', step='test', index=0)
    assert chip.hash_files('input', 'rtl', 'verilog', step='test', index=0) == \
        ['aec070645fe53ee3b3763059376134f058cc337247c978add178b6ccdfb0019f']

    hashes = getattr(chip, '_Chip__hashes')
    assert hashes[os.path.abspath('foo.txt')] == \
        'aec070645fe53ee3b3763059376134f058cc337247c978add178b6ccdfb0019f'
    hashes[os.path.abspath('foo.txt')] = 'h'
    assert hashes[os.path.abspath('foo.txt')] == 'h'
    assert chip.hash_files('input', 'rtl', 'verilog', check=False, allow_cache=True,
                           step='test', index=0) == ['h']


#########################
if __name__ == "__main__":
    test_changed_algorithm('md5')
