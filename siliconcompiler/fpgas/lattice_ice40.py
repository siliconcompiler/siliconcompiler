import siliconcompiler
from siliconcompiler.utils import register_sc_data_source


####################################################
# Setup for ICE40 Family FPGAs
####################################################
def setup():
    '''
    Lattice ICE40 FPGAs are a family of small parts
    made by Lattice Semiconductor.  A fully open source
    RTL to bitstream flow for ICE40 is available using
    yosys + nextpnr
    '''

    vendor = 'lattice'

    lut_size = '4'

    all_fpgas = []

    all_part_names = [
        "ice40up5k-sg48",
    ]

    for part_name in all_part_names:
        fpga = siliconcompiler.FPGA(part_name, package='siliconcompiler_data')
        register_sc_data_source(fpga)

        fpga.set('fpga', part_name, 'vendor', vendor)
        fpga.set('fpga', part_name, 'lutsize', lut_size)

        all_fpgas.append(fpga)

    return all_fpgas


#########################
if __name__ == "__main__":
    for fpga in setup(siliconcompiler.Chip('<fpga>')):
        fpga.write_manifest(f'{fpga.design}.json')
