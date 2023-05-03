from siliconcompiler.tools.yosys.yosys import syn_setup, syn_post_process
import os
import shutil
from jinja2 import Template
from siliconcompiler.utils import Arch


def make_docs(chip):
    chip.set('fpga', 'partname', 'ice40up5k-sg48')
    chip.load_target("fpgaflow_demo")


def setup(chip):
    '''
    Perform FPGA synthesis
    '''

    # Generic synthesis task setup.
    syn_setup(chip)

    # FPGA-specific setup.
    setup_fpga(chip)


def setup_fpga(chip):
    ''' Helper method for configs specific to FPGA steps (both syn and lec).
    '''

    tool = 'yosys'
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    task = chip._get_task(step, index)
    design = chip.top()

    # Require that a partname is set for FPGA scripts.
    chip.add('tool', tool, 'task', task, 'require', ",".join(['fpga', 'partname']),
             step=step, index=index)

    chip.add('tool', tool, 'task', task, 'output', design + '_netlist.json', step=step, index=index)
    chip.add('tool', tool, 'task', task, 'output', design + '.blif', step=step, index=index)


################################
# copy and render the VPR library
################################
def create_vpr_lib(chip):

    # copy the VPR techmap library to the input directory
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')

    src = os.path.join(os.path.dirname(__file__), "vpr_yosyslib")
    dst = os.path.join(chip._getworkdir(step=step, index=index), "inputs", "vpr_yosyslib")

    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    arch = Arch(chip.get('fpga', 'arch')[0])
    max_lut_size = arch.find_max_lut_size()
    max_mem_addr_width = arch.find_memory_addr_width()

    # render the template placeholders
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
def pre_process(chip):
    ''' Tool specific function to run before step execution
    '''

    # copy the VPR library to the yosys input directory and render the placeholders
    if chip.get('fpga', 'arch'):
        create_vpr_lib(chip)
        return


##################################################
def post_process(chip):
    syn_post_process(chip)
