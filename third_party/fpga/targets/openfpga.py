def setup_platform(chip):
    chip.set('mode', 'fpga')

    openfpga_dir = 'fpga/openfpga/'
    chip.add('fpga', 'xml', openfpga_dir + 'k6_frac_N10_40nm_vpr.xml')
    chip.add('fpga', 'xml', openfpga_dir + 'k6_frac_N10_40nm_openfpga.xml')
