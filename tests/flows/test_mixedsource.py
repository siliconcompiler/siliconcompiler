import os
import pytest
import siliconcompiler

##################################
@pytest.mark.skip(reason="Mixed-source functionality is still a work-in-progress.")
@pytest.mark.eda
@pytest.mark.quick
def test_mixedsrc_local_py(scroot):
    '''Basic Python API test: build the mixed-source example using only Python code.
    '''

    # Create instance of Chip class
    chip = siliconcompiler.Chip()

    ex_dir = os.path.join(scroot, 'examples', 'mixed-source')

    # Inserting value into configuration
    chip.add('source', os.path.join(ex_dir, 'eq1.vhd'))
    chip.add('source', os.path.join(ex_dir, 'eq2.v'))
    chip.set('design', 'eq2')

    chip.target("freepdk45")

    flow = [
        ('import', 'morty'),
        ('importvhdl', 'ghdl'),
        ('syn', 'yosys')
    ]

    for i, (step, tool) in enumerate(flow):
        if i > 0:
            chip.add('flowgraph', step, 'input', flow[i-1][0])
        chip.set('flowgraph', step, 'tool', tool)

    # Run the chip's build process synchronously.
    chip.run()

    # Verify that the Verilog netlist is generated
    assert os.path.isfile('build/eq2/job0/syn/0/outputs/eq2.v')

if __name__ == "__main__":
    from tests.fixtures import scroot
    test_mixedsrc_local_py(scroot())
