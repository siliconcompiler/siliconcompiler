import os
import re
import sys
import defusedxml.ElementTree as ET

import siliconcompiler

######################################################################
# Make Docs
######################################################################

def make_docs():
    '''
    Yosys is a framework for RTL synthesis that takes synthesizable
    Verilog-2005 design and converts it to BLIF, EDIF, BTOR, SMT,
    Verilog netlist etc. The tool supports logical synthesis and
    tech mapping to ASIC standard cell libraries, FPGA architectures.
    In addition it has built in formal methods for property and
    equivalence checking.

    Documentation: http://www.clifford.at/yosys/documentation.html

    Sources: https://github.com/YosysHQ/yosys

    Installation: https://github.com/YosysHQ/yosys

    '''

    chip = siliconcompiler.Chip()
    chip.set('arg','step', 'syn')
    chip.set('arg','index', '<index>')
    chip.set('design', '<design>')
    setup_tool(chip)
    return chip

################################
# Setup Tool (pre executable)
################################

def setup_tool(chip):
    ''' Tool specific function to run before step execution
    '''

    # If the 'lock' bit is set, don't reconfigure.
    tool = 'yosys'
    refdir = 'tools/'+tool
    step = chip.get('arg','step')
    index = chip.get('arg','index')

    # Standard Setup
    chip.set('eda', tool, step, index, 'copy', 'true', clobber=False)
    chip.set('eda', tool, step, index, 'exe', 'yosys', clobber=False)
    chip.set('eda', tool, step, index, 'vswitch', '--version', clobber=False)
    chip.set('eda', tool, step, index, 'version', '0.9', clobber=False)
    chip.set('eda', tool, step, index, 'option', '-c', clobber=False)
    chip.set('eda', tool, step, index, 'refdir', refdir, clobber=False)

    if step == 'syn':
        script = 'sc_syn.tcl'
    elif step == 'lec':
        script = 'sc_lec.tcl'
    else:
        chip.logger.error(f'Yosys does not support step {step}.')

    chip.set('eda', tool, step, index, 'script', refdir + '/' + script, clobber=False)

    #Input/output requirements
    #TODO: add back input requirements for all tools, currently failing
    #chip.add('eda', tool, step, index, 'input', chip.get('design') + '.v')
    chip.add('eda', tool, step, index, 'output', chip.get('design') + '.vg')

    #Schema requirements
    if chip.get('mode') == 'asic':
        chip.add('eda', tool, step, index, 'require', ",".join(['pdk', 'process']))
        chip.add('eda', tool, step, index, 'require', ",".join(['design']))
        chip.add('eda', tool, step, index, 'require', ",".join(['asic', 'targetlib']))
    else:
        chip.add('eda', tool, step, index, 'require', ",".join(['fpga','partname']))

#############################################
# Runtime pre processing
#############################################

def pre_process(chip):

    tool = 'yosys'
    step = chip.get('arg','step')
    index = chip.get('arg','index')

    #TODO: remove special treatment for fpga??
    if chip.get('target') is None:
        return
    targetlist = chip.get('target').split('_')

    if len(targetlist) == 2 and targetlist[1] == 'openfpga':
        # Synthesis for OpenFPGA/VPR needs to know the size of the LUTs in the
        # FPGA architecture. We infer this from the VPR architecture file, then
        # dump it to a TCL file imported by the synthesis script.
        # Inference code adapted from OpenFPGA:
        # https://github.com/lnis-uofu/OpenFPGA/blob/c393ee695975c98342b8708c5bee19b677f4a062/openfpga_flow/scripts/run_fpga_flow.py#L473

        lut_size = None
        for arch_file in chip.find_files('fpga', 'arch'):
            tree = ET.parse(arch_file)
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
# Version Check
################################

def parse_version(stdout):
    # Yosys 0.9+3672 (git sha1 014c7e26, gcc 7.5.0-3ubuntu1~18.04 -fPIC -Os)
    version = stdout.split()[1]
    return version.split('+')[0]

################################
# Post_process (post executable)
################################
def post_process(chip):
    ''' Tool specific function to run after step execution
    '''

    tool = 'yosys'
    step = chip.get('arg','step')
    index = chip.get('arg','index')

    if step == 'syn':
        #TODO: looks like Yosys exits on error, so no need to check metric
        chip.set('metric', step, index, 'errors', 'real', 0, clobber=True)
        with open(step + ".log") as f:
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
    elif step == 'lec':
        with open(step + ".log") as f:
            for line in f:
                if line.endswith('Equivalence successfully proven!'):
                    chip.set('metric', step, index, 'errors', 'real', 0, clobber=True)
                    continue

                errors = re.search(r'Found a total of (\d+) unproven \$equiv cells.', line)
                if errors is not None:
                    num_errors = int(errors.group(1))
                    chip.set('metric', step, index, 'errors', 'real', num_errors, clobber=True)

    #Return 0 if successful
    return 0

##################################################
if __name__ == "__main__":

    chip = make_docs()
    chip.writecfg("yosys.json")
