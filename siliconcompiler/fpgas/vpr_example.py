import os
import siliconcompiler


####################################################
# Setup for vpr_example Family FPGAs
####################################################
def setup(chip):
    '''
    The vpr_example FPGA family is a set of
    open source architectures used as illustrative
    examples for academic FPGA architectures.  They
    are based on numerous examples furnished over the
    the years by the University of Toronto with different
    distributions of VPR

    For more information about VPR and its architecture models,
    see Murray et. al, "VTR 8: High Performance CAD and Customizable
    FPGA Architecture Modelling", ACM Trans. Reconfigurable Technol.
    Syst., 2020, https://www.eecg.utoronto.ca/~kmurray/vtr/vtr8_trets.pdf
    '''

    vendor = 'N/A'

    flow_root = os.path.join("../", 'examples', 'fpga_flow')

    lut_size = '4'

    all_fpgas = []

    all_part_names = [
        'example_arch_X005Y005',
        'example_arch_X008Y008',
    ]

    # Settings common to all parts in family
    for part_name in all_part_names:

        fpga = siliconcompiler.FPGA(chip, part_name)

        fpga.set('fpga', part_name, 'vendor', vendor)

        fpga.set('fpga', part_name, 'lutsize', lut_size)

        arch_root = os.path.join(flow_root, 'arch', part_name)
        fpga.set('fpga', part_name, 'file', 'archfile', os.path.join(arch_root, f'{part_name}.xml'))

        if (part_name == 'example_arch_X005Y005'):
            arch_root = os.path.join(flow_root, 'arch', 'example_arch_X005Y005')
            fpga.set('fpga', 'example_arch_X005Y005', 'file', 'graphfile',
                     os.path.join(arch_root, 'example_arch_X005Y005_rr_graph.xml'))
            fpga.set('fpga', 'example_arch_X005Y005', 'var', 'channelwidth', '32')

        if (part_name == 'example_arch_X008Y008'):
            # No RR graph for this architecture to support testing
            fpga.set('fpga', 'example_arch_X008Y008', 'var', 'channelwidth', '32')

        all_fpgas.append(fpga)

    return all_fpgas


#########################
if __name__ == "__main__":
    for fpga in setup(siliconcompiler.Chip('<fpga>')):
        fpga.write_manifest(f'{fpga.design}.json')
