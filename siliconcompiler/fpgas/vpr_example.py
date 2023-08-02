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

    part_name = chip.get('fpga', 'partname')

    family = 'vpr_example'
    vendor = 'N/A'

    lut_size = '4'

    fpga = siliconcompiler.FPGA(chip, family)

    fpga.set('fpga', 'vendor', vendor)
    fpga.set('fpga', family, 'lut_size', lut_size)

    flow_root = os.path.join("../", 'examples', 'fpga_flow')
    arch_root = os.path.join(flow_root, 'arch', part_name)

    if (part_name == 'example_arch_X005Y005'):
        xml_file = os.path.join(arch_root, f'{part_name}.xml')
        rr_graph_file = os.path.join(arch_root, f'{part_name}_rr_graph.xml')
        route_chan_width = 32
    elif (part_name == 'example_arch_X008Y008'):
        xml_file = os.path.join(arch_root, f'{part_name}.xml')
        # ***NOTE:  this architecture doesn't yet have a RR graph file;
        #           which helps both with file size and with testing that
        #           the flow works if none is provided
        # rr_graph_file = os.path.join(arch_root, f'{part_name}_rr_graph.xml')
        rr_graph_file = None
        route_chan_width = 32
    else:
        chip.error("vpr_example family does not support part name {part_name}", fatal=True)

    chip.set('tool', 'yosys', 'task', 'syn', 'var', 'lut_size', f'{lut_size}')

    for task in ['place', 'route', 'bitstream']:
        chip.set('tool', 'vpr', 'task', task, 'file', 'arch_file', xml_file)
        # ***NOTE:  If the RR graph is not specified, the FASM bitstream will
        #           generate but omit any bitstream data for programmable
        #           interconnect (SBs and CBs); meaning that the FPGA will
        #           not be correctly programmed.
        chip.set('tool', 'vpr', 'task', task, 'file', 'rr_graph', f'{rr_graph_file}')
        chip.set('tool', 'vpr', 'task', task, 'var', 'route_chan_width', f'{route_chan_width}')

    return fpga


#########################
if __name__ == "__main__":
    fpga = setup(siliconcompiler.Chip('<fpga>'))
    fpga.write_manifest(f'{fpga.top()}.json')
