from siliconcompiler.tools.yosys.yosys import syn_setup, syn_post_process


######################################################################
# Make Docs
######################################################################
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

    part_name = chip.get('fpga', 'partname')

    # Require that a lut size is set for FPGA scripts.
    chip.add('tool', tool, 'task', task, 'require',
             ",".join(['fpga', part_name, 'lutsize']),
             step=step, index=index)

    chip.add('tool', tool, 'task', task, 'require',
             ",".join(['fpga', part_name, 'var', 'legalize_flops']),
             step=step, index=index)

    # Do not require tech libraries, as there are some FPGAs that
    # are so simple (in academia) that they do not require any

    chip.add('tool', tool, 'task', task, 'output', design + '_netlist.json', step=step, index=index)
    chip.add('tool', tool, 'task', task, 'output', design + '.blif', step=step, index=index)


##################################################
def pre_process(chip):
    ''' Tool specific function to run before step execution
    '''

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = chip._get_tool_task(step, index)

    part_name = chip.get('fpga', 'partname')

    # Some tool/task variables can have their values determined
    # purely from part name, rely on part drivers to provide
    # these and grab them for feeding to yosys here:
    feature_set = chip.get('fpga', part_name, 'var', 'feature_set')
    chip.set('tool', tool, 'task', task, 'var', 'feature_set', feature_set)

    legalize_flops = chip.get('fpga', part_name, 'var', 'legalize_flops')
    chip.set('tool', tool, 'task', task, 'var', 'legalize_flops', legalize_flops)

    # Convert all part-specific techmap files to tool/task
    # files for yosys script consumption

    if not chip.valid('fpga', part_name, 'file', 'yosys_techmap'):
        chip.logger.warning("No yosys_techmap supplied")
    for techmap in chip.find_files('fpga', part_name, 'file', 'yosys_techmap'):
        if techmap is None:
            chip.logger.warning("yosys_techmap provided is None")
        chip.add('tool', tool, 'task', task, 'file', 'techmap', techmap,
                 step=step, index=index)

    if not chip.valid('fpga', part_name, 'file', 'yosys_flop_techmap'):
        chip.logger.warning("No yosys_flop_techmap supplied")
    for techmap in chip.find_files('fpga', part_name, 'file', 'yosys_flop_techmap'):
        if techmap is None:
            chip.logger.warning("yosys_flop_techmap provided is None")
        chip.add('tool', tool, 'task', task, 'file', 'flop_techmap', techmap,
                 step=step, index=index)


##################################################
def post_process(chip):
    syn_post_process(chip)
