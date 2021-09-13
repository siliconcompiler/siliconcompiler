import importlib
import os
import siliconcompiler
import re

####################################################
# Flowgraph Setup
####################################################
def setup_flow(chip):
    '''
    This is a standard open source FPGA flow based on high quality tools.
    The flow supports SystemVerilog, VHDL, and mixed SystemVerilog/VHDL
    flows. The asic flow is a linera pipeline that includes the
    stages below. To skip the last three verification steps, you can
    specify "-stop export" at the command line.

    import: Sources are collected and packaged for compilation.
            A design manifest is created to simplify design sharing.

    syn: Translates RTL to netlist using Yosys

    apr: Automated place and route

    bitstream: Bistream generation

    program: Download bitstream to hardware (requires physical connection).

    Args:
        partname (string): Mandatory argument specifying the compiler target
            partname. The partname is needed in syn, apr, bitstream, and
            program steps to produce correct results.

    '''

    if chip.get('fpga', 'partname'):
        partname = chip.get('fpga', 'partname')
    else:
        partname = "UNDEFINED"

    # Inferring vendor name based on part number
    if re.match('ice', partname):
        chip.set('fpga','vendor', 'lattice')

    # A simple linear flow
    flowpipe = ['import',
                'syn',
                'apr',
                'bitstream']

    # Linear flow
    index = '0'

    # Set the steplist which can run remotely (if required)
    chip.set('remote', 'steplist', flowpipe[1:])

    # Minimal setup
    for i, step in enumerate(flowpipe):

        # Metrics
        chip.set('flowgraph', step, index, 'weight',  'cellarea', 1.0)
        chip.set('flowgraph', step, index, 'weight',  'peakpower', 1.0)
        chip.set('flowgraph', step, index, 'weight',  'standbypower', 1.0)

        # Goals
        chip.set('metric', step, index, 'drv', 'errors', 0)
        #chip.set('metric', step, index, 'drv', 'warnings', 0)
        chip.set('metric', step, index, 'drv', 'goal', 0.0)
        chip.set('metric', step, index, 'holdwns', 'goal', 0.0)
        chip.set('metric', step, index, 'holdtns', 'goal', 0.0)
        chip.set('metric', step, index, 'setupwns', 'goal', 0.0)
        chip.set('metric', step, index, 'setuptns', 'goal', 0.0)

        if i > 0:
            chip.add('flowgraph', flowpipe[i], index, 'input', flowpipe[i-1], "0")

    # Per step tool selection
    for step in flowpipe:
        if step == 'import':
            tool = 'verilator'
        elif step == 'syn':
            tool = 'yosys'
        elif step == 'apr':
            if re.match('ice', partname):
                tool = 'nextpnr'
            else:
                # TODO: eventually we want to drive vpr directly without going
                # through openfpga
                # tool = 'vpr'
                tool = 'openfpga'
        elif step == 'bitstream':
            if re.match('ice', partname):
                tool = 'icepack'
            else:
                tool = 'openfpga'
        elif step == 'program':
            if re.match('ice', partname):
                tool = 'iceprog'
            else:
                tool = 'openfpga'
        chip.set('flowgraph', step, index, 'tool', tool)

##################################################
if __name__ == "__main__":

    # File being executed
    prefix = os.path.splitext(os.path.basename(__file__))[0]
    chip = siliconcompiler.Chip(defaults=False)
    setup_flow(chip)
    chip.writecfg(prefix + ".json")
    chip.writegraph(prefix + ".png")
