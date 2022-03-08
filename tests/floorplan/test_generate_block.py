import siliconcompiler
from siliconcompiler.floorplan import Floorplan

import os

def test_generate_block_freepdk45():
    chip = siliconcompiler.Chip()

    chip.set('design', 'gcd')
    chip.load_target('freepdk45_demo')
    fp = Floorplan(chip)

    diearea = [(0,0), (100.13,100.8)]
    corearea = [(10.07,11.2), (90.25,91)]
    inputs = [
        ('clk', 1),
        ('req_val', 1),
        ('reset', 1),
        ('resp_rdy', 1),
        ('req_msg', 32)
    ]
    outputs = [
        ('req_rdy', 1),
        ('resp_val', 1),
        ('resp_msg', 16)
    ]
    pdn_params = {
        'vdd': 'vdd',
        'vss': 'vss',
        'hwidth': 2,
        'hspacing': 10,
        'hlayer': 'm9',
        'vwidth': 2,
        'vspacing': 10,
        'vlayer': 'm10',
        'stdcell_pin_vdd': 'VDD',
        'stdcell_pin_vss': 'VSS',
        'stdcell_pin_width': 0.17
    }

    fp.generate_block_floorplan(diearea, corearea, inputs, outputs, pdn_params)
    fp.write_def('gcd.def')

    assert os.path.isfile('gcd.def')