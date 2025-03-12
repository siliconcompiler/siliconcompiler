from siliconcompiler import Chip, FPGA


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

    all_fpgas = []

    for part_name in ("ice40up5k-sg48",):
        fpga = FPGA(part_name)

        fpga.set('fpga', part_name, 'vendor', 'lattice')
        fpga.set('fpga', part_name, 'lutsize', 4)

        all_fpgas.append(fpga)

    return all_fpgas


#########################
if __name__ == "__main__":
    for fpga in setup(Chip('<fpga>')):
        fpga.write_manifest(f'{fpga.design}.json')
