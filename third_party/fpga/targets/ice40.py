def setup_platform(chip):
    chip.add('mode', 'fpga')
    chip.set('fpga', 'vendor', 'lattice')
    chip.set('fpga', 'device', 'ice40up5k-sg48')
