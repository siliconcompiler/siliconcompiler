def setup_platform(chip):
    chip.add('mode', 'fpga')
    chip.set('fpga', 'vendor', 'lattice')
    chip.set('fpga', 'device', 'ecp5-25k-285c')
