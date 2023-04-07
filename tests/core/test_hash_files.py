# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import pytest

import siliconcompiler

def test_hash_files():
    chip = siliconcompiler.Chip('top')

    chip.load_target("freepdk45_demo")
    chip.write_manifest("raw.json")
    allkeys = chip.allkeys()
    for keypath in allkeys:
        if 'file' in chip.get(*keypath, field='type'):
            for vals, step, index in chip.schema._getvals(*keypath):
                hashes = chip.hash_files(*keypath, step=step, index=index)
                schema_hashes = chip.schema.get(*keypath, step=step, index=index, field='filehash')
                assert hashes == schema_hashes
                assert len(hashes) == len(vals)
    chip.write_manifest("hashed.json")

def test_err_mismatch():
    chip = siliconcompiler.Chip('top')

    # Necessary due to find_files() quirk, we need a flow w/ an import step
    chip.load_target('freepdk45_demo')

    # Create foo.txt and compute its hash
    with open('foo.txt', 'w') as f:
        f.write('foobar\n')
    chip.set('input', 'rtl', 'verilog', 'foo.txt')
    assert chip.hash_files('input', 'rtl', 'verilog') == ['aec070645fe53ee3b3763059376134f058cc337247c978add178b6ccdfb0019f']

    # Change foo.txt
    with open('foo.txt', 'w') as f:
        f.write('FOObar\n')

    with pytest.raises(siliconcompiler.SiliconCompilerError):
        # foo.txt is changed, so should trigger error
        chip.hash_files('input', 'rtl', 'verilog', update=False)

    # Restore foo.txt
    with open('foo.txt', 'w') as f:
        f.write('foobar\n')

    # No error since foo.txt was restored, and update=False in previous call
    # ensures original hash wasn't overwritten
    assert chip.hash_files('input', 'rtl', 'verilog', update=False) == ['aec070645fe53ee3b3763059376134f058cc337247c978add178b6ccdfb0019f']

@pytest.mark.parametrize('algorithm,expected', [('md5', '14758f1afd44c09b7992073ccf00b43d'),
                                                ('sha1', '988881adc9fc3655077dc2d4d757d480b5ea0e11'),
                                                ('sha224', '90a81bdaa85b5d9dfc4c0cd89d9edaf93255d5f4160cd67bead46a91'),
                                                ('sha256', 'aec070645fe53ee3b3763059376134f058cc337247c978add178b6ccdfb0019f'),
                                                ('sha384', '190d8045dc5875c1004e4dd31f13194eea25043cf9ffc40550cca30fdcae20f8d7eed05f3c94058b206329dbe8d2312e'),
                                                ('sha512', 'e79b8ad22b34a54be999f4eadde2ee895c208d4b3d83f1954b61255d2556a8b73773c0dc0210aa044ffcca6834839460959cbc9f73d3079262fc8bc935d46262')])
def test_changed_algorithm(algorithm, expected):

    # Create foo.txt and compute its hash
    with open('foo.txt', 'w') as f:
        f.write('foobar\n')

    chip = siliconcompiler.Chip('top')

    # Necessary due to find_files() quirk, we need a flow w/ an import step
    chip.load_target('freepdk45_demo')
    chip.set('input', 'rtl', 'verilog', 'foo.txt')
    chip.set('input', 'rtl', 'verilog', algorithm, field='hashalgo')
    print(chip.hash_files('input', 'rtl', 'verilog'))
    assert chip.hash_files('input', 'rtl', 'verilog') == [expected]

#########################
if __name__ == "__main__":
    test_changed_algorithm('md5')
