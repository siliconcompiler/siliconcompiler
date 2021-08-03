import importlib
import os
import siliconcompiler

####################################################
# Flowgraph Setup
####################################################
def setup_flow(chip, name=None):
    flowpipe = ['import', 'importvhdl', 'syn']
    flowtools = ['morty', 'ghdl', 'yosys']
    for i in range(len(flowpipe)-1):
        chip.add('flowgraph', flowpipe[i], 'output', flowpipe[i+1])
    for i, tool in enumerate(flowtools):
        chip.set('flowgraph', flowpipe[i], 'tool', tool)

##################################################
if __name__ == "__main__":

    # File being executed
    prefix = os.path.splitext(os.path.basename(__file__))[0]
    output = prefix + '.json'

    # create a chip instance
    chip = siliconcompiler.Chip(defaults=False)
    # load configuration
    setup_flow(chip)
    # write out results
    chip.writecfg(output)
    chip.write_flowgraph(prefix + ".svg")
