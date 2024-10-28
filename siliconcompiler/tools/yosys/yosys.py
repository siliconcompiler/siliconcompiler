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
from siliconcompiler import sc_open
from siliconcompiler.tools._common import get_tool_task, record_metric
from siliconcompiler.targets import asap7_demo


######################################################################
# Make Docs
######################################################################
def make_docs(chip):
    chip.use(asap7_demo)


################################
# Setup Tool (pre executable)
################################
def setup(chip):
    ''' Tool specific function to run before step execution
    '''

    # If the 'lock' bit is set, don't reconfigure.
    tool = 'yosys'
    refdir = 'tools/' + tool
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    _, task = get_tool_task(chip, step, index)

    # Standard Setup
    chip.set('tool', tool, 'exe', 'yosys')
    chip.set('tool', tool, 'vswitch', '--version')
    chip.set('tool', tool, 'version', '>=0.41', clobber=False)
    chip.set('tool', tool, 'format', 'tcl', clobber=False)

    # Task Setup
    # common to all
    option = []
    if chip.get('option', 'breakpoint', step=step, index=index):
        option.append('-C')
    option.append('-c')
    chip.set('tool', tool, 'task', task, 'option', option, step=step, index=index, clobber=False)
    chip.set('tool', tool, 'task', task, 'refdir', refdir, step=step, index=index,
             package='siliconcompiler', clobber=False)
    chip.set('tool', tool, 'task', task, 'regex', 'warnings', "Warning:",
             step=step, index=index, clobber=False)
    chip.set('tool', tool, 'task', task, 'regex', 'errors', "^ERROR",
             step=step, index=index, clobber=False)


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
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    _, task = get_tool_task(chip, step, index)
    design = chip.top()

    # Set yosys script path.
    chip.set('tool', tool, 'task', task, 'script', 'sc_syn.tcl',
             step=step, index=index, clobber=False)

    # Input/output requirements.
    chip.set('tool', tool, 'task', task, 'input', design + '.v', step=step, index=index)
    chip.set('tool', tool, 'task', task, 'output', design + '.vg', step=step, index=index)


##################################################
def syn_post_process(chip):
    ''' Tool specific function to run after step execution
    '''

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')

    with sc_open("reports/stat.json") as f:
        metrics = json.load(f)
        if "design" in metrics:
            metrics = metrics["design"]

        if "area" in metrics:
            record_metric(chip, step, index, 'cellarea',
                          float(metrics["area"]),
                          "reports/stat.json",
                          source_unit='um^2')
        if "num_cells" in metrics:
            record_metric(chip, step, index, 'cells',
                          metrics["num_cells"],
                          "reports/stat.json")
        if "num_wire_bits" in metrics:
            record_metric(chip, step, index, 'nets',
                          metrics["num_wire_bits"],
                          "reports/stat.json")
        if "num_port_bits" in metrics:
            record_metric(chip, step, index, 'pins',
                          metrics["num_port_bits"],
                          "reports/stat.json")

    registers = None
    with sc_open(f"{step}.log") as f:
        for line in f:
            line_registers = re.findall(r"^\s*mapped ([0-9]+) \$_DFF.*", line)
            if line_registers:
                if registers is None:
                    registers = 0
                registers += int(line_registers[0])
    if registers is not None:
        record_metric(chip, step, index, 'registers', registers, f"{step}.log")


##################################################
if __name__ == "__main__":

    chip = make_docs()
    chip.write_manifest("yosys.json")
