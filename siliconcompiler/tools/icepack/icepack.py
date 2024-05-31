
'''
Icepack converts an ASCII bitstream file to a .bin file for the
ICE40 FPGA.

Documentation: https://clifford.at/icestorm

Sources: https://github.com/YosysHQ/icestorm

Installation: https://github.com/YosysHQ/icestorm
'''


#####################################################################
# Make Docs
#####################################################################
def make_docs(chip):
    from siliconcompiler.tools.icepack.bitstream import setup
    setup(chip)
    return chip


################################
#  Custom runtime options
################################
def runtime_options(chip):
    ''' Custom runtime options, returnst list of command line options.
    '''

    topmodule = chip.top()

    cmdlist = []
    cmdlist.append("inputs/" + topmodule + ".asc")
    cmdlist.append("outputs/" + topmodule + ".bit")

    return cmdlist


##################################################
if __name__ == "__main__":

    chip = make_docs()
    chip.write_manifest("icepack.json")
