import os
import re
import sys
import defusedxml.ElementTree as ET

import siliconcompiler
from siliconcompiler.schema import schema_path

################################
# Setup Tool (pre executable)
################################
def setup_tool(chip, step):
    ''' Tool specific function to run before step execution
    '''

    chip.logger.debug("Setting up Yosys")

    tool = 'yosys'
    refdir = 'siliconcompiler/tools/yosys'
    chip.set('eda', tool, step, 'format', 'tcl')
    chip.set('eda', tool, step, 'copy', 'true')
    chip.set('eda', tool, step, 'vendor', 'yosys')
    chip.set('eda', tool, step, 'exe', 'yosys')
    chip.set('eda', tool, step, 'refdir', refdir)
    chip.add('eda', tool, step, 'script', refdir + '/sc_syn.tcl')
    chip.add('eda', tool, step, 'option', 'cmdline', '-c')

    #TODO: remove special treatment for fpga??
    targetlist = chip.get('target').split('_')
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
def post_process(chip, step):
    ''' Tool specific function to run after step execution
    '''
    tool = 'yosys'
    exe = chip.get('eda',tool, step, 'exe')
    with open(exe + ".log") as f:
        for line in f:
            area = re.search(r'Chip area for module.*\:\s+(.*)', line)
            cells = re.search(r'Number of cells\:\s+(.*)', line)
            warnings = re.search(r'Warnings.*\s(\d+)\s+total', line)

            if area:
                chip.set('metric', step, 'real', 'area_cells', round(float(area.group(1)),2))
            elif cells:
                chip.set('metric', step, 'real', 'cells', int(cells.group(1)))
            elif warnings:
                chip.set('metric', step, 'real', 'warnings', int(warnings.group(1)))

    #Return 0 if successful
    return 0

##################################################
if __name__ == "__main__":

    # File being executed
    prefix = os.path.splitext(os.path.basename(__file__))[0]
    output = prefix + '.json'

    # create a chip instance
    chip = siliconcompiler.Chip(defaults=False)
    # load configuration
    setup_tool(chip, step='syn')
    # write out results
    chip.writecfg(output)
