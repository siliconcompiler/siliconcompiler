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
            chip.hash_files(*keypath)
            for val, step, index in chip.schema._getvals(*keypath):
                hashes = chip.schema.get(*keypath, step=step, index=index)
                assert len(hashes) == len(val)
    chip.write_manifest("hashed.json")

def test_err_mismatch():
    chip = siliconcompiler.Chip('top')

    # Necessary due to find_files() quirk, we need a flow w/ an import step
    chip.load_target('freepdk45_demo')

    # Create foo.txt and compute its hash
    with open('foo.txt', 'w') as f:
        f.write('foobar\n')
    chip.set('input', 'rtl', 'verilog', 'foo.txt')
    chip.hash_files('input', 'rtl', 'verilog')

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
    chip.hash_files('input', 'rtl', 'verilog', update=False)

#########################
if __name__ == "__main__":
    test_hash_files()
