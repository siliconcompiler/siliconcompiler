# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import siliconcompiler
import os

def test_write_manifest():

    chip = siliconcompiler.Chip()
    chip.add('constraint', 'top.sdc')
    chip.set('projversion', '0.1')
    chip.set('description', 'A dummy project')
    chip.add('source', 'top.v')
    chip.add('source', 'a.v')
    chip.add('source', 'b.v')
    chip.add('source', 'c.v')
    chip.set('design', 'top')

    chip.write_manifest('top.core')
    chip.write_manifest('top.pkg.json')
    chip.write_manifest('top.csv')
    chip.write_manifest('top.tcl')
    chip.write_manifest('top.yaml')

def test_write_manifest_dir_sanitize():

    chip = siliconcompiler.Chip()

    chip.status['local_dir'] = 'build'
    chip.set('dir', 'remote_build_dir')

    chip.add('constraint', 'top.sdc')
    chip.set('description', 'A dummy project')
    chip.add('cfg', os.path.join(chip.get('dir'), 'mycfg.json'))
    chip.add('source', 'top.v')
    chip.add('source', 'a.v')
    chip.add('source', 'b.v')
    chip.add('source', 'c.v')
    chip.set('design', 'top')

    chip.write_manifest('top.pkg.json')

    new_chip = siliconcompiler.Chip()
    new_chip.read_manifest('top.pkg.json')

    assert new_chip.get('dir') == chip.status['local_dir']
    assert new_chip.get('cfg')[0] == os.path.join(chip.status['local_dir'], 'mycfg.json')

#########################
if __name__ == "__main__":
    test_write_manifest()
