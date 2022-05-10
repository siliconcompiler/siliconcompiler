import siliconcompiler

import os

def test_read_lef(scroot):
    chip = siliconcompiler.Chip('test')

    freepdk45_tlef = os.path.join(scroot,
                                  'third_party',
                                  'pdks',
                                  'virtual',
                                  'freepdk45',
                                  'pdk',
                                  'r1p0',
                                  'apr',
                                  'freepdk45.tech.lef')
    stackup = '10M'
    chip.read_lef(freepdk45_tlef, 'freepdk45', stackup)

    assert len(chip.getkeys('pdk', 'freepdk45', 'grid', stackup)) == 10

    assert chip.get('pdk', 'freepdk45', 'grid', stackup, 'metal4', 'name') == 'm4'
    assert chip.get('pdk', 'freepdk45', 'grid', stackup, 'metal4', 'xpitch') == 0.28
    assert chip.get('pdk', 'freepdk45', 'grid', stackup, 'metal4', 'ypitch') == 0.28
    assert chip.get('pdk', 'freepdk45', 'grid', stackup, 'metal4', 'xoffset') == 0.095
    assert chip.get('pdk', 'freepdk45', 'grid', stackup, 'metal4', 'yoffset') == 0.07
    assert chip.get('pdk', 'freepdk45', 'grid', stackup, 'metal4', 'dir') == 'vertical'

    assert chip.get('pdk', 'freepdk45', 'grid', stackup, 'metal9', 'name') == 'm9'
    assert chip.get('pdk', 'freepdk45', 'grid', stackup, 'metal9', 'xpitch') == 1.6
    assert chip.get('pdk', 'freepdk45', 'grid', stackup, 'metal9', 'ypitch') == 1.6
    assert chip.get('pdk', 'freepdk45', 'grid', stackup, 'metal9', 'xoffset') == 0.095
    assert chip.get('pdk', 'freepdk45', 'grid', stackup, 'metal9', 'yoffset') == 0.07
    assert chip.get('pdk', 'freepdk45', 'grid', stackup, 'metal9', 'dir') == 'horizontal'
