from siliconcompiler import FPGADevice


class ICE40Up5k_sg48(FPGADevice):
    '''
    SiliconCompiler object for the Lattice iCE40UP5K FPGA with the SG48 package.

    This class configures the SiliconCompiler framework to target the iCE40UP5K,
    a small, low-power FPGA from Lattice Semiconductor. It leverages the fully
    open-source RTL-to-bitstream toolchain consisting of Yosys for synthesis
    and nextpnr for place-and-route.
    '''

    def __init__(self):
        super().__init__("ice40up5k-sg48")
        self.package.set_vendor("lattice")
        self.set_partname("ice40up5k-sg48")
        self.set_lutsize(4)
