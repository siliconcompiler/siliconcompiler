import importlib
import os
import siliconcompiler

####################################################
# EDA Setup
####################################################
def setup_flow(chip, name=None):
    chip.logger.debug("Setting up an FPGA compilation flow'")

    # Define Compilation Steps
    flowpipe = ['validate',
                'import',
                'syn',
                'apr']

    for i in range(len(flowpipe)-1):
        chip.add('flowgraph', flowpipe[i], 'output', flowpipe[i+1])

    for step in flowpipe:
        if step == 'validate':
            tool = 'surelog'
        if step == 'import':
            tool = 'sv2v'
        elif step == 'syn':
            tool = 'yosys'
        elif step == 'apr':
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
    setup_flow(chip)
    # write out results
    chip.writecfg(output)
    chip.write_flowgraph(prefix + ".svg")
