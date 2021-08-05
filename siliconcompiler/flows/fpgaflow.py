import importlib
import os
import siliconcompiler
import re

####################################################
# Flowgraph Setup
####################################################
def setup_flow(chip, partname):

    # A simple linear flow
    flowpipe = ['import',
                'syn',
                'apr',
                'bitstream']

    #TODO: add 'program' stage

    for i in range(len(flowpipe)-1):
        chip.add('flowgraph', flowpipe[i], 'output', flowpipe[i+1])
        
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
                tool = 'vpr'
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
