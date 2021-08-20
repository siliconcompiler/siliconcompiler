import os
import siliconcompiler
from tests.fixtures import test_wrapper

##################################
def test_mixedsrc_local_py():
    '''Basic Python API test: build the mixed-source example using only Python code.
    '''

    # Create instance of Chip class
    chip = siliconcompiler.Chip(loglevel='NOTSET')

    ex_dir = os.path.abspath(__file__)
    ex_dir = ex_dir[:ex_dir.rfind('/tests/quick_tests/asic')] + '/examples/mixed-source/'

    # Inserting value into configuration
    chip.add('source', ex_dir + 'eq1.vhd')
    chip.add('source', ex_dir + 'eq2.v')
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
    assert os.path.isfile('build/eq2/job0/syn0/outputs/eq2.v')
