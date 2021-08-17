import glob
import os
import re
import shutil
import subprocess
import sys

import siliconcompiler
from siliconcompiler.schema import schema_path

################################
# Setup Tool (pre executable)
################################

def setup_tool(chip, step, index):
    ''' Tool specific function to run before step execution
    '''

    chip.logger.debug("Setting up Yosys")

    tool = 'python3'
    refdir = 'siliconcompiler/tools/yosys'
    chip.set('eda', tool, step, index, 'format', 'py')
    chip.set('eda', tool, step, index, 'copy', 'false')
    chip.set('eda', tool, step, index, 'exe', 'python3')

    if step == 'rtlgen':
        chip.set('eda', tool, step, index, 'vendor', 'OpenFPGA')

    if not 'OPENFPGA_PATH' in os.environ:
        chip.logger.error('$OPENFPGA_PATH is not set; cannot generate FPGA netlist.')
        os.sys.exit()

    ofpga_run_path = os.environ['OPENFPGA_PATH'] + '/openfpga_flow/scripts/run_fpga_task.py'
    ofpga_task_dir = chip.status['openfpga_task_dir']
    chip.add('eda', tool, step, index, 'option', 'cmdline', ofpga_run_path)
    chip.add('eda', tool, step, index, 'option', 'cmdline', ofpga_task_dir)

################################
# Post_process (post executable)
################################
def post_process(chip, step, index):
    ''' Tool specific function to run after step execution
    '''

    # Copy generated sources and relevant SDC file[s].
    ofpga_task_dir = chip.status['openfpga_task_dir']
    src_glob = f'{ofpga_task_dir}/latest/*/*/*/'
    # There should only be one generated-code directory.
    src_dir = next(glob.iglob(src_glob))
    shutil.copytree(os.path.realpath(src_dir + "/SRC"), os.path.abspath("outputs/SRC"))
    shutil.copy(src_dir + "/SDC/global_ports.sdc", os.path.abspath("outputs/global_ports.sdc"))

    # Modify the top-level file to use absolute file paths.
    # TODO: Python file open/close instead of sed dependency?
    subprocess.run(['sed', '-i', f's;\./SRC;{os.path.abspath("outputs/SRC")};g', os.path.abspath("outputs/SRC/fabric_netlists.v")])

    # Modify the 'inv_buf_passgate.v' file to remove '$random' directives.
    # TODO: These calls cause errors because Verilator does not support tri-state
    # logic, but to my untrained eye they look like they exist for simulation.
    # I believe it should be safe to remove them from the physical design.
    subprocess.run(['sed', '-i', 's/(in === 1\'bz)? $random : //g', os.path.abspath('outputs/SRC/sub_module/inv_buf_passgate.v')])

    # Return 0 if successful.
    return 0

##################################################
if __name__ == "__main__":

    # File being executed
    prefix = os.path.splitext(os.path.basename(__file__))[0]
    output = prefix + '.json'

    # create a chip instance
    chip = siliconcompiler.Chip(defaults=False)
    # load configuration
    setup_tool(chip, step='syn')
    # write out results
    chip.writecfg(output)
