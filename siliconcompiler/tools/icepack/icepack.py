import siliconcompiler

#####################################################################
# Make Docs
#####################################################################

def make_docs():
    '''
    Icepack converts an ASCII bitstream file to a .bin file for the
    ICE40 FPGA.

    Documentation: http://bygone.clairexen.net/icestorm/

    Sources: https://github.com/YosysHQ/icestorm

    Installation: https://github.com/YosysHQ/icestorm

    '''

    chip = siliconcompiler.Chip('<design>')
    chip.set('arg','step','bitstream')
    chip.set('arg','index','<index>')
    setup(chip)
    return chip


################################
# Setup Tool (pre executable)
################################

def setup(chip):
    ''' Sets up default settings on a per step basis
    '''
    tool = 'icepack'
    step = chip.get('arg','step')
    index = chip.get('arg','index')
    clobber = False
    chip.set('tool', tool, 'exe', tool)
    chip.set('tool', tool, 'option', step, index, "", clobber=clobber)

    design = chip.top()
    chip.set('tool', tool, 'input', step, index, f'{design}.asc')
    chip.set('tool', tool, 'output', step, index, f'{design}.bit')

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
