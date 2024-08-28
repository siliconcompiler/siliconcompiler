import os
import siliconcompiler
from siliconcompiler.utils import register_sc_data_source


####################################################
# Setup for vpr_example Family FPGAs
####################################################
def setup():
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

    flow_root = os.path.join('examples', 'fpga_flow')

    lut_size = '4'

    all_fpgas = []

    all_part_names = [
        'example_arch_X005Y005',
        'example_arch_X008Y008',
        'example_arch_X014Y014',
        'example_arch_X030Y030',
    ]

    # Settings common to all parts in family
    for part_name in all_part_names:
        fpga = siliconcompiler.FPGA(part_name, package='siliconcompiler_data')
        register_sc_data_source(fpga)

        fpga.set('fpga', part_name, 'vendor', vendor)

        fpga.set('fpga', part_name, 'lutsize', lut_size)

        arch_root = os.path.join(flow_root, 'arch', part_name)
        fpga.set('fpga', part_name, 'file', 'archfile', os.path.join(arch_root, f'{part_name}.xml'))

        fpga.set('fpga', part_name, 'var', 'vpr_clock_model', 'ideal')

        if (part_name == 'example_arch_X005Y005'):
            arch_root = os.path.join(flow_root, 'arch', part_name)
            fpga.set('fpga', part_name, 'file', 'graphfile',
                     os.path.join(arch_root, 'example_arch_X005Y005_rr_graph.xml'))
            fpga.set('fpga', part_name, 'var', 'channelwidth', '32')

        if (part_name == 'example_arch_X008Y008'):
            # No RR graph for this architecture to support testing
            fpga.set('fpga', part_name, 'var', 'channelwidth', '32')

        if ((part_name == 'example_arch_X014Y014') or (part_name == 'example_arch_X030Y030')):

            techlib_root = os.path.join(flow_root, 'techlib')

            if (part_name == 'example_arch_X014Y014'):
                fpga.set('fpga', part_name, 'file', 'constraints_map',
                         os.path.join(arch_root, f'{part_name}_constraint_map.json'))

            fpga.set('fpga', part_name, 'var', 'channelwidth', '80')
            fpga.add('fpga', part_name, 'var', 'feature_set', 'async_set')
            fpga.add('fpga', part_name, 'var', 'feature_set', 'async_reset')
            fpga.add('fpga', part_name, 'var', 'feature_set', 'enable')
            fpga.add('fpga', part_name, 'file', 'yosys_flop_techmap',
                     os.path.join(techlib_root, 'example_arch_techmap_flops.v'))

            fpga.add('fpga', part_name, 'file', 'yosys_dsp_techmap',
                     os.path.join(techlib_root, 'example_arch_techmap_dsp.v'))

            fpga.add('fpga', part_name, 'file', 'yosys_extractlib',
                     os.path.join(techlib_root, 'example_arch_techmap_dsp_extract.v'))

            # The same library used for the extraction pass can also be used to
            # define macros that can be passed through synthesis, specify that here
            fpga.add('fpga', part_name, 'file', 'yosys_macrolib',
                     os.path.join(techlib_root, 'example_arch_techmap_dsp_extract.v'))

            fpga.add('fpga', part_name, 'var', 'yosys_dsp_options', 'DSP_A_MAXWIDTH=18')
            fpga.add('fpga', part_name, 'var', 'yosys_dsp_options', 'DSP_B_MAXWIDTH=18')
            fpga.add('fpga', part_name, 'var', 'yosys_dsp_options', 'DSP_A_MINWIDTH=2')
            fpga.add('fpga', part_name, 'var', 'yosys_dsp_options', 'DSP_B_MINWIDTH=2')
            fpga.add('fpga', part_name, 'var', 'yosys_dsp_options', 'DSP_NAME=_dsp_block_')

            fpga.add('fpga', part_name, 'file', 'yosys_memory_techmap',
                     os.path.join(techlib_root, 'example_arch_techmap_bram.v'))
            fpga.add('fpga', part_name, 'file', 'yosys_memory_libmap',
                     os.path.join(techlib_root, 'example_arch_bram_memory_map.txt'))

        all_fpgas.append(fpga)

    return all_fpgas


#########################
if __name__ == "__main__":
    for fpga in setup(siliconcompiler.Chip('<fpga>')):
        fpga.write_manifest(f'{fpga.design}.json')
