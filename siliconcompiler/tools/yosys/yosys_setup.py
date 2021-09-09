import os
import re
import sys
import defusedxml.ElementTree as ET

import siliconcompiler
from siliconcompiler.schema_utils import schema_path

################################
# Setup Tool (pre executable)
################################

def setup_tool(chip, step, index):
    ''' Tool specific function to run before step execution
    '''

    # If the 'lock' bit is set, don't reconfigure.
    tool = 'yosys'
    refdir = 'siliconcompiler/tools/yosys'
    configured = chip.get('eda', tool, step, index, 'exe', field='lock')
    if configured and (configured != 'false'):
        chip.logger.warning('Tool already configured: ' + tool)
        return

    # Standard Setup
    chip.set('eda', tool, step, index, 'copy', 'true', clobber=False)
    chip.set('eda', tool, step, index, 'vendor', 'yosys', clobber=False)
    chip.set('eda', tool, step, index, 'exe', 'yosys', clobber=False)
    chip.set('eda', tool, step, index, 'vswitch', '--version', clobber=False)
    chip.set('eda', tool, step, index, 'version', '0.9+3672', clobber=False)
    chip.set('eda', tool, step, index, 'option', 'cmdline', '-c', clobber=False)
    chip.set('eda', tool, step, index, 'refdir', refdir, clobber=False)
    chip.set('eda', tool, step, index, 'script', refdir + '/sc_syn.tcl', clobber=False)

    #Input/output requirements
    chip.add('eda', tool, step, index, 'input', chip.get('design') + '.v')
    chip.add('eda', tool, step, index, 'output', chip.get('design') + '.v')

    #Schema requirements
    if chip.get('mode') == 'asic':
        chip.add('eda', tool, step, index, 'req', ",".join(['pdk', 'process']))
        chip.add('eda', tool, step, index, 'req', ",".join(['design']))
        chip.add('eda', tool, step, index, 'req', ",".join(['asic', 'targetlib']))
    else:
        chip.add('eda', tool, step, index, 'req', ",".join(['fpga','partname']))

def pre_process(chip, step, index):
    #TODO: remove special treatment for fpga??
    if chip.get('target') is None:
        return
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
def post_process(chip, step, index):
    ''' Tool specific function to run after step execution
    '''
    tool = 'yosys'
    exe = chip.get('eda', tool, step, index, 'exe')
    with open(exe + ".log") as f:
        for line in f:
            area = re.search(r'Chip area for module.*\:\s+(.*)', line)
            cells = re.search(r'Number of cells\:\s+(.*)', line)
            warnings = re.search(r'Warnings.*\s(\d+)\s+total', line)

            if area:
                chip.set('metric', step, index, 'cellarea', 'real', round(float(area.group(1)),2), clobber=True)
            elif cells:
                chip.set('metric', step, index, 'cells', 'real', int(cells.group(1)), clobber=True)
            elif warnings:
                chip.set('metric', step, index, 'warnings', 'real', int(warnings.group(1)), clobber=True)

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
