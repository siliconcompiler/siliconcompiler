import os
import re
import os
import shutil
import importlib
from jinja2 import Template
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
    chip.set('tool', tool, 'exe', 'yosys')
    chip.set('tool', tool, 'vswitch', '--version')
    chip.set('tool', tool, 'version', '>=0.13', clobber=False)
    chip.set('tool', tool, 'format', 'tcl', clobber=False)
    chip.set('tool', tool, 'option', step, index, '-c', clobber=False)
    chip.set('tool', tool, 'refdir', step, index, refdir, clobber=False)

    if re.search(r'syn', step):
        script = 'sc_syn.tcl'
    elif re.search(r'lec', step):
        script = 'sc_lec.tcl'
    else:
        # Emit a warning for unsupported yosys step, but allow execution to proceed.
        # Users can configure their own flows involving yosys, but they will be responsible for
        # setting appropriate schema values, including 'script'.
        script = ''
        chip.logger.warning(f'Unsupported yosys step: {step}.')

    chip.set('tool', tool, 'script', step, index, script, clobber=False)

    design = chip.top()

    # Input/output requirements
    if step.startswith('syn'):
        # TODO: Our yosys script can also accept uhdm or ilang files. How do we
        # represent a set of possible inputs where you must pick one?
        chip.set('tool', tool, 'input', step, index, design + '.v')
        chip.set('tool', tool, 'output', step, index, design + '.vg')
        chip.add('tool', tool, 'output', step, index, design + '_netlist.json')
        chip.add('tool', tool, 'output', step, index, design + '.blif')
    elif step == 'lec':
        if (not chip.valid('input', 'netlist') or
            not chip.get('input', 'netlist')):
            chip.set('tool', tool, 'input', step, index, design + '.vg')
        if not chip.get('input', 'verilog'):
            # TODO: Not sure this logic makes sense? Seems like reverse of
            # what's in TCL
            chip.set('tool', tool, 'input', step, index, design + '.v')

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
    chip.set('tool', tool, 'regex', step, index, 'warnings', "Warning:", clobber=False)
    chip.set('tool', tool, 'regex', step, index, 'errors', "^ERROR", clobber=False)

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

    # copy the VPR library to the yosys input directory and render the placeholders
    if chip.get('fpga', 'arch'):
        create_vpr_lib(chip)

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
    if step.startswith('syn'):
        #TODO: looks like Yosys exits on error, so no need to check metric
        chip.set('metric', step, index, 'errors', 0, clobber=True)
        with open(step + ".log") as f:
            for line in f:
                area = re.search(r'Chip area for module.*\:\s+(.*)', line)
                cells = re.search(r'Number of cells\:\s+(.*)', line)
                if area:
                    chip.set('metric', step, index, 'cellarea', round(float(area.group(1)),2), clobber=True)
                elif cells:
                    chip.set('metric', step, index, 'cells', int(cells.group(1)), clobber=True)
    elif step == 'lec':
        with open(step + ".log") as f:
            for line in f:
                if line.endswith('Equivalence successfully proven!\n'):
                    chip.set('metric', step, index, 'drvs', 0, clobber=True)
                    continue

                errors = re.search(r'Found a total of (\d+) unproven \$equiv cells.', line)
                if errors is not None:
                    num_errors = int(errors.group(1))
                    chip.set('metric', step, index, 'drvs', num_errors, clobber=True)


################################
# copy and render the VPR library
################################
def create_vpr_lib(chip):

    #copy the VPR techmap library to the input directory
    step = chip.get('arg','step')
    index = chip.get('arg','index')

    src = f"{chip.scroot}/tools/yosys/vpr_yosyslib"
    dst = f"{chip._getworkdir()}/{step}/{index}/inputs/vpr_yosyslib"

    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    spec = importlib.util.spec_from_file_location("utils", f"{chip.scroot}/utils.py")
    imported = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(imported)

    Arch = getattr(imported, 'Arch')
    arch = Arch(chip.get('fpga', 'arch')[0])
    max_lut_size = arch.find_max_lut_size()
    max_mem_addr_width = arch.find_memory_addr_width()

    #render the template placeholders
    data = {
        "max_lut_size": max_lut_size,
        "memory_addr_width": max_mem_addr_width,
        "lib_dir": dst,
        "min_hard_adder_size": "1",
        "min_hard_mult_size": "3"
    }

    for _, _, lib_files in os.walk(dst):
        for file_name in lib_files:
            file = f"{dst}/{file_name}"
            print(file)
            with open(file) as template_f:
                template = Template(template_f.read())
            with open(file, "w") as rendered_f:
                rendered_f.write(template.render(data))

##################################################
if __name__ == "__main__":

    chip = make_docs()
    chip.write_manifest("yosys.json")


