import glob
import os
import shutil
import subprocess

################################
# Setup Tool (pre executable)
################################

def setup_tool(chip, step):
    ''' Per tool function that returns a dynamic options string based on
    the dictionary settings.
    '''

    # Standard Setup
    tool = 'python3'
    chip.set('eda', tool, step, 'threads', 4)
    chip.set('eda', tool, step, 'format', 'cmdline')
    chip.set('eda', tool, step, 'copy', 'false')

    if step == 'rtlgen':
        chip.set('eda', tool, step, 'exe', 'python3')
        chip.set('eda', tool, step, 'vendor', 'openfpga')

        # Cannot run if $OPENFPGA_PATH is not set.
        if not 'OPENFPGA_PATH' in os.environ:
            chip.logger.error('OpenFPGA script installation directory not found.')
            sys.exit()

        # OpenFPGA 'source' argument is the directory containing the OpenFPGA task.
        chip.add('eda', tool, step, 'option', f'{os.environ["OPENFPGA_PATH"]}/openfpga_flow/scripts/run_fpga_task.py')
        chip.add('eda', tool, step, 'option', os.path.abspath(chip.get('source')[0]))

################################
# Post_process (post executable)
################################

def post_process(chip, step):
    ''' Tool specific function to run after step execution
    '''

    # Copy generated sources and relevant SDC file[s].
    src_glob = f'{os.path.abspath(chip.get("source")[0])}/latest/*/*/*/'
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

    # Modify the config dictionary to setup the ASIC flow's "import" step.
    chip.set('source', os.path.abspath('outputs/SRC/fabric_netlists.v'))
    chip.set('constraint', os.path.abspath('outputs/global_ports.sdc'))

    # Return 0 if successful.
    return 0
