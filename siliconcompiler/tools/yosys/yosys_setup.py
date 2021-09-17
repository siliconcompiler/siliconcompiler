import os
import re
import sys
import defusedxml.ElementTree as ET

import siliconcompiler
from siliconcompiler.schema_utils import schema_path

######################################################################
# Make Docs
######################################################################

def make_docs():
    '''Yosys is a framework for RTL synthesis.

    Features:

    * Process almost any synthesizable Verilog-2005 design
    * Converting Verilog to BLIF / EDIF/ BTOR / SMT-LIB / Verilog / etc.
    * Built-in formal methods for checking properties and equivalence
    * Mapping to ASIC standard cell libraries
    * Mapping to FPGAs.
    * Foundation and/or front-end for custom flows

    The interface from SC to yosys is done through 'sc_manifest.tcl'.
    The entry point for all yosys based steps is the 'sc_syn.tcl' script.
    The script handles general input/output function and is the main
    interface to SC.

    Installation Instructions:

    SC TCL scripts:

    Source code:
    * https://github.com/YosysHQ/yosys

    Documentation:
    * http://www.clifford.at/yosys/documentation.html

    '''

    chip = siliconcompiler.Chip()
    setup_tool(chip,'syn','<index>')
    return chip


################################
# Setup Tool (pre executable)
################################

def setup_tool(chip, step, index):
    ''' Tool specific function to run before step execution

    Tool-specific options:

    - techmap: list of Verilog files used for mapping generic Yosys cells.
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

    # Since tool options are of type str (not file), we manually resolve any
    # paths the user added using schema_path and stuff them back into the
    # options entry.
    techmap_paths = []
    if 'techmap' in chip.getkeys('eda', tool, step, index, 'option'):
        for mapfile in chip.get('eda', tool, step, index, 'option', 'techmap'):
            abspath = schema_path(mapfile)
            # TODO: should we check here that file exists? warning or error if not?
            techmap_paths.append(abspath)

    # Next, we add the default techmap files bundled into SC.
    # These don't need absolute paths since the files live in the tool
    # directory, and copy=True (so they'll be accessible as a relative path
    # from TCL).
    if chip.get('pdk','process'):
        process = chip.get('pdk','process')
        if process == 'freepdk45':
            techmap_paths.append('cells_latch_freepdk45.v')
        elif process == 'skywater130':
            # TODO: might want to eventually switch on libname rather than
            # process so we can support other sky130 variations besides HD.
            techmap_paths.append('cells_latch_sky130hd.v')

    chip.set('eda', tool, step, index, 'option', 'techmap', techmap_paths)

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
# Version Check
################################

def check_version(chip, step, index, version):
    ''' Tool specific version checking
    '''
    required = chip.get('eda', 'yosys', step, index, 'version')
    #insert code for parsing the funtion based on some tool specific
    #semantics.
    #syntax for version is string, >=string

    return 0



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

    chip = make_docs()
    chip.writecfg("yosys.json")
