import siliconcompiler


####################################################
# Setup for ICE40 Family FPGAs
####################################################
def setup(chip):
    '''
    Lattice ICE40 FPGAs are a family of small parts
    made by Lattice Semiconductor.  A fully open source
    RTL to bitstream flow for ICE40 is available using
    yosys + nextpnr
    '''

    family = 'ice40'
    vendor = 'lattice'

    lut_size = '4'

    fpga = siliconcompiler.FPGA(chip, family)

    fpga.set('fpga', 'vendor', vendor)
    fpga.set('fpga', family, 'lut_size', lut_size)

    chip.set('tool', 'yosys', 'task', 'syn', 'var', 'lut_size', f'{lut_size}')

    return fpga


#########################
if __name__ == "__main__":
    fpga = setup(siliconcompiler.Chip('<fpga>'))
    fpga.write_manifest(f'{fpga.top()}.json')
