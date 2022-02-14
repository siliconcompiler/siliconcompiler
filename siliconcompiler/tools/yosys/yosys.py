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
    setup(chip)
    return chip

################################
# Setup Tool (pre executable)
################################

def setup(chip):
    ''' Tool specific function to run before step execution
    '''

    # If the 'lock' bit is set, don't reconfigure.
    tool = 'yosys'
    refdir = 'tools/'+tool
    step = chip.get('arg','step')
    index = chip.get('arg','index')

    # Standard Setup
    chip.set('eda', tool, 'exe', 'yosys', clobber=False)
    chip.set('eda', tool, 'vswitch', '--version', clobber=False)
    chip.set('eda', tool, 'version', '0.9', clobber=False)
    chip.set('eda', tool, 'format', 'tcl', clobber=False)
    chip.set('eda', tool, 'copy', 'true', clobber=False)
    chip.set('eda', tool, 'option', step, index, '-c', clobber=False)
    chip.set('eda', tool, 'refdir', step, index, refdir, clobber=False)

    if step == 'syn':
        script = 'sc_syn.tcl'
    elif step == 'lec':
        script = 'sc_lec.tcl'
    else:
        chip.logger.error(f'Yosys does not support step {step}.')

    chip.set('eda', tool, 'script', step, index, refdir + '/' + script, clobber=False)

    # Input/output requirements
    if step == 'syn':
        # TODO: Our yosys script can also accept uhdm or ilang files. How do we
        # represent a set of possible inputs where you must pick one?
        chip.set('eda', tool, 'input', step, index, chip.get('design') + '.v')
        chip.set('eda', tool, 'output', step, index, chip.get('design') + '.vg')
        chip.add('eda', tool, 'output', step, index, chip.get('design') + '_netlist.json')
        chip.add('eda', tool, 'output', step, index, chip.get('design') + '.blif')
    elif step == 'lec':
        if (not chip.valid('read', 'netlist', step, index) or
            not chip.get('read', 'netlist', step, index)):
            chip.set('eda', tool, 'input', step, index, chip.get('design') + '.vg')
        if not chip.get('source'):
            chip.set('eda', tool, 'input', step, index, chip.get('design') + '.v')

    # Schema requirements
    if chip.get('mode') == 'asic':
        chip.add('eda', tool, 'require', step, index, ",".join(['pdk', 'process']))
        chip.add('eda', tool, 'require', step, index, ",".join(['design']))
        chip.add('eda', tool, 'require', step, index, ",".join(['asic', 'logiclib']))

        mainlib = chip.get('asic', 'logiclib')[0]
        chip.add('eda', tool, 'require', step, index, ",".join(['library', mainlib, 'nldm', 'typical', 'lib']))

        macrolibs = chip.get('asic', 'macrolib')
        for lib in macrolibs:
            if chip.valid('library', lib, 'nldm', 'typical', 'lib'):
                chip.add('eda', tool, 'require', step, index, ",".join(['library', lib, 'nldm', 'typical', 'lib']))
    else:
        chip.add('eda', tool, 'require', step, index, ",".join(['fpga','partname']))


#############################################
# Runtime pre processing
#############################################

def pre_process(chip):

    tool = 'yosys'
    step = chip.get('arg','step')
    index = chip.get('arg','index')

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

    # Setting up regex patterns
    chip.set('eda', tool, 'regex', step, index, 'warnings', "Warning", clobber=False)
    chip.set('eda', tool, 'regex', step, index, 'errors', "Error", clobber=False)

    # Reports
    for metric in ('errors', 'warnings', 'drvs', 'coverage', 'security',
                   'luts', 'dsps', 'brams',
                   'cellarea',
                   'cells', 'registers', 'buffers', 'nets', 'pins'):
        chip.set('eda', tool, 'report', step, index, metric, f"{step}.log")

    # Extracting
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
