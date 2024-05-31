from siliconcompiler.tools.yosys.yosys import syn_setup, syn_post_process
import json
from siliconcompiler import sc_open


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

    if chip.valid('fpga', part_name, 'file', 'yosys_flop_techmap') and \
       chip.get('fpga', part_name, 'file', 'yosys_flop_techmap'):

        chip.add('tool', tool, 'task', task, 'require',
                 ",".join(['fpga', part_name, 'file', 'yosys_flop_techmap']),
                 step=step, index=index)

    if chip.valid('fpga', part_name, 'file', 'yosys_dsp_techmap') and \
       chip.get('fpga', part_name, 'file', 'yosys_dsp_techmap'):

        chip.add('tool', tool, 'task', task, 'require',
                 ",".join(['fpga', part_name, 'file', 'yosys_dsp_techmap']),
                 step=step, index=index)

    if chip.valid('fpga', part_name, 'file', 'yosys_extractlib') and \
       chip.get('fpga', part_name, 'file', 'yosys_extractlib'):

        chip.add('tool', tool, 'task', task, 'require',
                 ",".join(['fpga', part_name, 'file', 'yosys_extractlib']),
                 step=step, index=index)

    if chip.valid('fpga', part_name, 'file', 'yosys_macrolib') and \
       chip.get('fpga', part_name, 'file', 'yosys_macrolib'):

        chip.add('tool', tool, 'task', task, 'require',
                 ",".join(['fpga', part_name, 'file', 'yosys_macrolib']),
                 step=step, index=index)

    # Verify memory techmapping setup.  If a memory libmap
    # is provided a memory techmap verilog file is needed too
    if (chip.valid('fpga', part_name, 'file', 'yosys_memory_libmap') and
        chip.get('fpga', part_name, 'file', 'yosys_memory_libmap')) or \
        (chip.valid('fpga', part_name, 'file', 'yosys_memory_techmap') and
         chip.get('fpga', part_name, 'file', 'yosys_memory_techmap')):

        chip.add('tool', tool, 'task', task, 'require',
                 ",".join(['fpga', part_name, 'file', 'yosys_memory_libmap']),
                 step=step, index=index)
        chip.add('tool', tool, 'task', task, 'require',
                 ",".join(['fpga', part_name, 'file', 'yosys_memory_techmap']),
                 step=step, index=index)

    chip.add('tool', tool, 'task', task, 'output', design + '.netlist.json', step=step, index=index)
    chip.add('tool', tool, 'task', task, 'output', design + '.blif', step=step, index=index)


##################################################
def post_process(chip):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    part_name = chip.get('fpga', 'partname')

    syn_post_process(chip)

    with sc_open("reports/stat.json") as f:
        metrics = json.load(f)
        if "design" in metrics:
            metrics = metrics["design"]
        else:
            return

        if "num_cells_by_type" in metrics:
            metrics = metrics["num_cells_by_type"]
        else:
            return

        dff_cells = chip.get('fpga', part_name, 'resources', 'registers')
        brams_cells = chip.get('fpga', part_name, 'resources', 'brams')
        dsps_cells = chip.get('fpga', part_name, 'resources', 'dsps')

        data = {
            "registers": 0,
            "luts": 0,
            "dsps": 0,
            "brams": 0
        }
        for cell, count in metrics.items():
            if cell == "$lut":
                data["luts"] += count
            elif cell in dff_cells:
                data["registers"] += count
            elif cell in dsps_cells:
                data["dsps"] += count
            elif cell in brams_cells:
                data["brams"] += count

        for metric, value in data.items():
            chip._record_metric(step, index, metric, value, "reports/stat.json")
