import importlib
import os
import siliconcompiler
import re

####################################################
# Flowgraph Setup
####################################################
def setup_flow(chip, partname):
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

    # Inferring vendor name based on part number
    if re.match('ice', partname):
        chip.set('fpga','vendor', 'lattice')


    # A simple linear flow
    flowpipe = ['import',
                'syn',
                'apr',
                'bitstream']
    # Set the steplist which can run remotely (if required)
    chip.set('remote', 'steplist', flowpipe[1:])

    #TODO: add 'program' stage

    for i, step in enumerate(flowpipe):
        chip.set('flowgraph', flowpipe[i], 'mergeop', 'min')
        chip.set('flowgraph', flowpipe[i], 'nproc',  1)
        for metric in chip.getkeys('metric','default', 'default'):
            chip.set('flowgraph', flowpipe[i], 'weight',  metric, 1.0)
        if i > 0:
            chip.add('flowgraph', flowpipe[i], 'input', flowpipe[i-1])
        else:
            chip.add('flowgraph', flowpipe[i], 'input', 'source')

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
        chip.set('flowgraph', step, 'tool', tool)

##################################################
if __name__ == "__main__":

    # File being executed
    prefix = os.path.splitext(os.path.basename(__file__))[0]
    output = prefix + '.json'

    # create a chip instance
    chip = siliconcompiler.Chip(defaults=False)
    # load configuration
    setup_flow(chip, "partname")
    # write out results
    chip.writecfg(output)
    chip.write_flowgraph(prefix + ".svg")
