'''
Yosys is a framework for RTL synthesis that takes synthesizable
Verilog-2005 design and converts it to BLIF, EDIF, BTOR, SMT,
Verilog netlist etc. The tool supports logical synthesis and
tech mapping to ASIC standard cell libraries, FPGA architectures.
In addition it has built in formal methods for property and
equivalence checking.

Documentation: https://yosyshq.readthedocs.io/projects/yosys/en/latest/

Sources: https://github.com/YosysHQ/yosys

Installation: https://github.com/YosysHQ/yosys
'''

import re
import json

######################################################################
# Make Docs
######################################################################
def make_docs(chip):
    chip.load_target("asap7_demo")

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
    task = chip._get_task(step, index)
    design = chip.top()

    # Standard Setup
    chip.set('tool', tool, 'exe', 'yosys')
    chip.set('tool', tool, 'vswitch', '--version')
    chip.set('tool', tool, 'version', '>=0.24', clobber=False)
    chip.set('tool', tool, 'format', 'tcl', clobber=False)

    # Task Setup
    # common to all
    chip.set('tool', tool, 'task', task, 'option', '-c', step=step, index=index, clobber=False)
    chip.set('tool', tool, 'task', task, 'refdir', refdir, step=step, index=index, clobber=False)
    chip.set('tool', tool, 'task', task, 'regex', 'warnings', "Warning:", step=step, index=index, clobber=False)
    chip.set('tool', tool, 'task', task, 'regex', 'errors', "^ERROR", step=step, index=index, clobber=False)
    for metric in ('cells', 'nets', 'pins'):
        chip.set('tool', tool, 'task', task, 'report', metric, "reports/stat.json", step=step, index=index)
    for metric in ('cellarea', 'errors', 'warnings', 'cellarea', 'drvs', 'coverage', 'security',
                   'luts', 'dsps', 'brams', 'registers', 'buffers'):
        chip.set('tool', tool, 'task', task, 'report', metric, f"{step}.log", step=step, index=index)

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

def syn_setup(chip):
    ''' Helper method for configs specific to synthesis tasks.
    '''

    # Generic tool setup.
    setup(chip)

    tool = 'yosys'
    step = chip.get('arg','step')
    index = chip.get('arg','index')
    task = chip._get_task(step, index)
    design = chip.top()

    # Set yosys script path.
    chip.set('tool', tool, 'task', task, 'script', 'sc_syn.tcl', step=step, index=index, clobber=False)

    # Input/output requirements.
    chip.set('tool', tool, 'task', task, 'input', design + '.v', step=step, index=index)
    chip.set('tool', tool, 'task', task, 'output', design + '.vg', step=step, index=index)

##################################################
def syn_post_process(chip):
    ''' Tool specific function to run after step execution
    '''

    tool = 'yosys'
    step = chip.get('arg','step')
    index = chip.get('arg','index')

    #TODO: looks like Yosys exits on error, so no need to check metric
    chip.set('metric', 'errors', 0, step=step, index=index)
    with open("reports/stat.json", 'r') as f:
        metrics = json.load(f)
        if "design" in metrics:
            metrics = metrics["design"]

        if "area" in metrics:
            chip.set('metric', 'cellarea', float(metrics["area"]), step=step, index=index)
        if "num_cells" in metrics:
            chip.set('metric', 'cells', int(metrics["num_cells"]), step=step, index=index)

    registers = None
    with open(f"{step}.log", 'r') as f:
        for line in f:
            area_metric = re.findall(r"^SC_METRIC: area: ([0-9.]+)", line)
            if area_metric:
                chip.set('metric', 'cellarea', float(area_metric[0]), step=step, index=index)
            line_registers = re.findall(r"^\s*mapped ([0-9]+) \$_DFF.*", line)
            if line_registers:
                if registers is None:
                    registers = 0
                registers += int(line_registers[0])
    if registers is not None:
        chip.set('metric', 'registers', registers, step=step, index=index)

##################################################
if __name__ == "__main__":

    chip = make_docs()
    chip.write_manifest("yosys.json")
