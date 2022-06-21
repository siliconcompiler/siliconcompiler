import siliconcompiler
import os
import json
import pytest

@pytest.mark.eda
@pytest.mark.quick
def test_spree(spree_dir):
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

    manifest_file = os.path.join(chip._getworkdir(), 'spree.pkg.json')
    assert os.path.exists(manifest_file)
    
    manifest = json.load(open(manifest_file))
    flow_graph = manifest["flowgraph"]["fpgaflow"] 
    for step in flow_graph:
        assert flow_graph[step]["0"]["status"]["value"] == "success"

if __name__ == "__main__":
    from tests.fixtures import scroot
    spree_dir = os.path.join(scroot(), 'examples', 'spree')
    test_spree(spree_dir)