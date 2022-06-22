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
    chip.add('tool', 'vpr', 'option', 'pack-place-route', '0',  '--route_chan_width 50')
    
    chip.run()

    post_route_net = os.path.join(chip._getworkdir(), 'pack-place-route', '0', 'spree.net.post_routing')
    assert os.path.exists(post_route_net)


if __name__ == "__main__":
    from tests.fixtures import scroot
    test_spree(scroot())