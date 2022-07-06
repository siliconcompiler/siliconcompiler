import siliconcompiler
import os
import pytest

    
@pytest.mark.eda
@pytest.mark.quick
def test_parity(scroot):
    parity_dir = os.path.join(scroot, 'examples', 'parity')
    source = os.path.join(parity_dir, 'parity.v')
    arch = os.path.join(parity_dir, 'arch.xml')
    
    chip = siliconcompiler.Chip('parity')
    
    chip.add('input', 'verilog', source)
    chip.set('fpga', 'arch', arch)
    chip.set('fpga', 'partname', 'dummy')
    chip.load_flow('fpgaflow')

    chip.set('option', 'flow', 'fpgaflow')
    
    chip.run()

    fasm_file = os.path.join(chip._getworkdir(), 'bitstream', '0', 'parity.fasm')
    assert os.path.exists(fasm_file)


if __name__ == "__main__":
    from tests.fixtures import scroot
    test_parity(scroot())