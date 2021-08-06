import importlib
import os
import siliconcompiler

####################################################
# Flowgraph Setup
####################################################
def setup_flow(chip, platform):

    # A simple linear flow
    flowpipe = ['import',
                'syn',
                'synopt',
                'floorplan',
                'place',
                'cts',
                'route',
                'dfm',
                'export']

    for i in range(len(flowpipe)-1):
        chip.add('flowgraph', flowpipe[i], 'output', flowpipe[i+1])

    # Per step tool selection
    for step in flowpipe:
        if step == 'import':
            tool = 'verilator'
        elif step == 'syn':
            tool = 'yosys'
        elif step == 'export':
            tool = 'klayout'
        else:
            tool = 'openroad'
        chip.set('flowgraph', step, 'tool', tool)


##################################################
if __name__ == "__main__":

    # File being executed
    prefix = os.path.splitext(os.path.basename(__file__))[0]
    output = prefix + '.json'

    # create a chip instance
    chip = siliconcompiler.Chip(defaults=False)
    # load configuration
    setup_flow(chip, "freepdk45")
    # write out results
    chip.writecfg(output)
    chip.write_flowgraph(prefix + ".svg")
