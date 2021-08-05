import importlib
import os
import siliconcompiler

####################################################
# Flowgraph Setup
####################################################
def setup_flow(chip, name=None):


    #Get edaflow, partname
    edaflow = chip.get('fpga','edaflow')[-1]
    partname = chip.get('fpga','partname')[-1]

    # Vendor/EDA lookup table
    if edaflow == 'xilinx':
        vendor_tool = 'vivado'
    elif edaflow == 'intel':
        vendor_tool = 'quartus'
    elif edaflow == 'lattice':
        vendor_tool = 'radiant'
    elif edaflow == 'microchip':
        vendor_tool = 'libero'

    # A simple linear flow
    flowpipe = ['import',
                'syn',
                'apr',
                'bitgen',
                'program']

    for i in range(len(flowpipe)-1):
        chip.add('flowgraph', flowpipe[i], 'output', flowpipe[i+1])

    # Per step tool selection
    for step in flowpipe:
        if step == 'import':
            tool = 'verilator'
        elif step == 'syn':
            if edaflow in ['openfpga', 'icestorm']:
                tool = 'yosys'
            else:
                tool = vendor_tool
        elif step == 'apr':
            if edaflow in ['icestorm']:
                tool = 'nextpnr'
            elif edaflow in ['openfpga']:
                tool = 'vpr'
            else:
                tool = vendor_tool
        elif step == 'bitgen':
            if edaflow in ['icestorm']:
                tool = 'icepack'
            elif edaflow in ['openfpga']:
                tool = 'openfpga'
            else:
                tool = vendor_tool
        elif step == 'program':
            if edaflow in ['icestorm']:
                tool = 'FAIL'
            elif edaflow in ['openfpga']:
                tool = 'FAIL'
            else:
                tool = vendor_tool

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
