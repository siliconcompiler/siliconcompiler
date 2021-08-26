import os
import re
import sys
import defusedxml.ElementTree as ET

import siliconcompiler
from siliconcompiler.schema import schema_path

################################
# Setup Tool (pre executable)
################################

def setup_tool(chip, step, index):
    ''' Tool specific function to run before step execution
    '''

    chip.logger.debug("Setting up Yosys")

    tool = 'yosys'
    refdir = 'siliconcompiler/tools/yosys'
    chip.set('eda', 'format',  tool, step, index, 'tcl')
    chip.set('eda', 'copy',    tool, step, index, 'true')
    chip.set('eda', 'vendor',  tool, step, index, 'yosys')
    chip.set('eda', 'exe',     tool, step, index, 'yosys')
    chip.set('eda', 'vswitch', tool, step, index, '--version')
    chip.set('eda', 'version', tool, step, index, '0.9+3672')
    chip.set('eda', 'option',  tool, step, index, 'cmdline', '-c')
    chip.set('eda', 'refdir',  tool, step, index, refdir)
    chip.set('eda', 'script',  tool, step, index, refdir + '/sc_syn.tcl')

    #Input/output requirements
    chip.add('eda', 'input', tool, step, index, chip.get('design') + '.v')
    chip.add('eda', 'output', tool, step, index, chip.get('design') + '.v')

    #Schema requirements
    if chip.get('mode') == 'asic':
        chip.add('eda', 'param', tool, step, index, ",".join(['pdk', 'process']))
        chip.add('eda', 'param', tool, step, index, ",".join(['asic', 'targetlib']))
    else:
        chip.add('eda', 'param', tool, step, index, 'constraint')
        chip.add('eda', 'param', tool, step, index, ",".join(['fpga','partname']))

    #TODO: remove special treatment for fpga??
    if chip.get('target'):
        targetlist = chip.get('target').split('_')
    else:
        targetlist = ['no','no']
    if targetlist[0] == 'openfpga':
        # Synthesis for OpenFPGA/VPR needs to know the size of the LUTs in the
        # FPGA architecture. We infer this from the VPR architecture file, then
        # dump it to a TCL file imported by the synthesis script.
        # Inference code adapted from OpenFPGA:
        # https://github.com/lnis-uofu/OpenFPGA/blob/c393ee695975c98342b8708c5bee19b677f4a062/openfpga_flow/scripts/run_fpga_flow.py#L473

        lut_size = None
        for arch_file in chip.get('fpga', 'arch'):
            tree = ET.parse(schema_path(arch_file))
            root = tree.getroot()
            if root.tag == 'architecture':
                lut_size = max([int(pb_type.find("input").get("num_pins"))
                                for pb_type in root.iter("pb_type")
                                if pb_type.get("class") == "lut"])

        if lut_size == None:
            chip.logger.error('Could not infer FPGA LUT size from architecture '
                'files')
            os.sys.exit()

        with open('fpga_lutsize.tcl', 'w') as f:
            f.write('set lutsize ' + str(lut_size))

################################
# Post_process (post executable)
################################
def post_process(chip, step, index):
    ''' Tool specific function to run after step execution
    '''
    tool = 'yosys'
    exe = chip.get('eda',tool, step, index, 'exe')
    with open(exe + ".log") as f:
        for line in f:
            area = re.search(r'Chip area for module.*\:\s+(.*)', line)
            cells = re.search(r'Number of cells\:\s+(.*)', line)
            warnings = re.search(r'Warnings.*\s(\d+)\s+total', line)

            if area:
                chip.set('metric', step, index, 'real', 'area_cells', round(float(area.group(1)),2))
            elif cells:
                chip.set('metric', step, index, 'real', 'cells', int(cells.group(1)))
            elif warnings:
                chip.set('metric', step, index, 'real', 'warnings', int(warnings.group(1)))

    #Return 0 if successful
    return 0

##################################################
if __name__ == "__main__":

    # File being executed
    prefix = os.path.splitext(os.path.basename(__file__))[0]
    output = prefix + '.json'

    # create a chip instance
    chip = siliconcompiler.Chip()
    # load configuration
    setup_tool(chip, step='syn', index='0')
    # write out results
    chip.writecfg(output)
