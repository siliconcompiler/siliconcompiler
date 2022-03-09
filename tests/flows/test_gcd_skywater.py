import os
import siliconcompiler
from siliconcompiler.floorplan import Floorplan
import pytest


def make_floorplan(chip):
    fp = Floorplan(chip)

    diearea = [(0, 0), (200.56, 201.28)]
    corearea = [(20.24, 21.76), (180.32, 184.96)]
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
        'hlayer': 'm5',
        'vwidth': 2,
        'vspacing': 10,
        'vlayer': 'm4',
        'stdcell_pin_vdd': 'VPWR',
        'stdcell_pin_vss': 'VGND',
        'stdcell_pin_width': 0.48
    }

    fp.generate_block_floorplan(diearea, corearea, inputs, outputs, pdn_params)
    fp.write_def('gcd.def')
    return 'gcd.def'

##################################
@pytest.mark.eda
@pytest.mark.quick
def test_gcd_checks(scroot):
    '''Test EDA flow with LVS and DRC
    '''

    # Create instance of Chip class
    chip = siliconcompiler.Chip()

    gcd_ex_dir = os.path.join(scroot, 'examples', 'gcd')

    # Inserting value into configuration
    chip.add('source', os.path.join(gcd_ex_dir, 'gcd.v'))
    chip.set('design', 'gcd')
    chip.set('relax', True)
    chip.set('quiet', True)
    chip.set('clock', 'core_clock', 'pin', 'clk')
    chip.set('clock', 'core_clock', 'period', 2)
    chip.set('flowarg', 'verify', 'true')

    chip.load_target("skywater130_demo")

    chip.set('supply', 'vdd', 'pin', 'vdd')
    # dummy level, just needs to be >0 to indicate power
    chip.set('supply', 'vdd', 'level', 1)

    chip.set('supply', 'vss', 'pin', 'vss')
    chip.set('supply', 'vss', 'level', 0)

    def_path = make_floorplan(chip)
    chip.set('read', 'def', 'floorplan', '0', def_path)

    # Run the chip's build process synchronously.
    chip.run()

    # Verify that GDS and SVG files were generated.
    assert os.path.isfile('build/gcd/job0/export/0/outputs/gcd.gds')

    # Verify that the build was LVS and DRC clean.
    assert chip.get('metric', 'lvs', '0', 'errors', 'real') == 0
    assert chip.get('metric', 'drc', '0', 'errors', 'real') == 0

if __name__ == "__main__":
    from tests.fixtures import scroot
    test_gcd_checks(scroot())
