import siliconcompiler
import os
import pytest

    
@pytest.mark.eda
@pytest.mark.quick
def test_spree(scroot):
    spree_dir = os.path.join(scroot, 'examples', 'spree')
    source = os.path.join(spree_dir, 'spree.v')
    arch = os.path.join(spree_dir, 'arch.xml')
    
    chip = siliconcompiler.Chip('spree')
    
    chip.add('input', 'verilog', source)
    chip.set('fpga', 'arch', arch)
    chip.set('fpga', 'partname', 'dummy')
    chip.load_flow('fpgaflow')

    chip.set('option', 'flow', 'fpgaflow')
    print(chip.list_steps())
    

    chip.set('option', 'steplist', ['import', 'syn_vpr', 'pack-place-route'])
    print(chip.list_steps())
    
    chip.run()

    route_file = os.path.join(chip._getworkdir(), 'pack-place-route', '0', 'spree.route')
    assert os.path.exists(route_file)


if __name__ == "__main__":
    from tests.fixtures import scroot
    test_spree(scroot())