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

    chip = siliconcompiler.Chip('<design>')
    chip.set('arg','step', 'syn')
    chip.set('arg','index', '<index>')
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
    chip.set('tool', tool, 'exe', 'yosys', clobber=False)
    chip.set('tool', tool, 'vswitch', '--version', clobber=False)
    chip.set('tool', tool, 'version', '>=0.13', clobber=False)
    chip.set('tool', tool, 'format', 'tcl', clobber=False)
    chip.set('tool', tool, 'option', step, index, '-c', clobber=False)
    chip.set('tool', tool, 'refdir', step, index, refdir, clobber=False)

    if re.search(r'syn', step):
        script = 'sc_syn.tcl'
    elif re.search(r'lec', step):
        script = 'sc_lec.tcl'
    else:
        chip.logger.error(f'Yosys does not support step {step}.')

    chip.set('tool', tool, 'script', step, index, script, clobber=False)

    # Input/output requirements
    if step == 'syn':
        # TODO: Our yosys script can also accept uhdm or ilang files. How do we
        # represent a set of possible inputs where you must pick one?
        chip.set('tool', tool, 'input', step, index, chip.design + '.v')
        chip.set('tool', tool, 'output', step, index, chip.design + '.vg')
        chip.add('tool', tool, 'output', step, index, chip.design + '_netlist.json')
        chip.add('tool', tool, 'output', step, index, chip.design + '.blif')
    elif step == 'lec':
        if (not chip.valid('input', 'netlist') or
            not chip.get('input', 'netlist')):
            chip.set('tool', tool, 'input', step, index, chip.design + '.vg')
        if not chip.get('input', 'verilog'):
            # TODO: Not sure this logic makes sense? Seems like reverse of
            # what's in TCL
            chip.set('tool', tool, 'input', step, index, chip.design + '.v')

    # Schema requirements
    if chip.get('option', 'mode') == 'asic':
        chip.add('tool', tool, 'require', step, index, ",".join(['asic', 'logiclib']))

        targetlibs = chip.get('asic', 'logiclib')
        for lib in targetlibs:
            # mandatory for logiclibs
            for corner in chip.getkeys('library', lib, 'model', 'timing', 'nldm'):
                chip.add('tool', tool, 'require', step, index, ",".join(['library', lib, 'model','timing', 'nldm', corner]))

        macrolibs = chip.get('asic', 'macrolib')
        for lib in macrolibs:
            # optional for macrolibs
            if chip.valid('library', lib, 'model', 'timing', 'nldm'):
                for corner in chip.getkeys('library', lib, 'model', 'timing', 'nldm'):
                    chip.add('tool', tool, 'require', step, index, ",".join(['library', lib, 'model','timing', 'nldm', corner]))
    else:
        chip.add('tool', tool, 'require', step, index, ",".join(['fpga','partname']))

    # Setting up regex patterns
    chip.set('tool', tool, 'regex', step, index, 'warnings', "Warning", clobber=False)
    chip.set('tool', tool, 'regex', step, index, 'errors', "Error", clobber=False)

    # Reports
    for metric in ('errors', 'warnings', 'drvs', 'coverage', 'security',
                   'luts', 'dsps', 'brams',
                   'cellarea',
                   'cells', 'registers', 'buffers', 'nets', 'pins'):
        chip.set('tool', tool, 'report', step, index, metric, f"{step}.log")

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
    return stdout.split()[1]

def normalize_version(version):
    # Replace '+', which represents a "local version label", with '-', which is
    # an "implicit post release number".
    return version.replace('+', '-')

################################
# Post_process (post executable)
################################
def post_process(chip):
    ''' Tool specific function to run after step execution
    '''

    step = chip.get('arg','step')
    index = chip.get('arg','index')

    # Extracting
    if step == 'syn':
        #TODO: looks like Yosys exits on error, so no need to check metric
        chip.set('metric', step, index, 'errors', 0, clobber=True)
        with open(step + ".log") as f:
            for line in f:
                area = re.search(r'Chip area for module.*\:\s+(.*)', line)
                cells = re.search(r'Number of cells\:\s+(.*)', line)
                warnings = re.search(r'Warnings.*\s(\d+)\s+total', line)
                if area:
                    chip.set('metric', step, index, 'cellarea', round(float(area.group(1)),2), clobber=True)
                elif cells:
                    chip.set('metric', step, index, 'cells', int(cells.group(1)), clobber=True)
                elif warnings:
                    chip.set('metric', step, index, 'warnings', int(warnings.group(1)), clobber=True)
    elif step == 'lec':
        with open(step + ".log") as f:
            for line in f:
                if line.endswith('Equivalence successfully proven!'):
                    chip.set('metric', step, index, 'errors', 0, clobber=True)
                    continue

                errors = re.search(r'Found a total of (\d+) unproven \$equiv cells.', line)
                if errors is not None:
                    num_errors = int(errors.group(1))
                    chip.set('metric', step, index, 'errors', num_errors, clobber=True)



    #Return 0 if successful
    return 0

##################################################
if __name__ == "__main__":

    chip = make_docs()
    chip.write_manifest("yosys.json")
