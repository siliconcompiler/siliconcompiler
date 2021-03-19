import os
from string import Template
import subprocess

################################
# Setup OpenFPGA
################################

OPENFPGA_SCRIPT = 'openfpga_script.openfpga'

def setup_tool(chip, step):
    ''' Sets up default settings on a per step basis
    '''

    refdir = 'eda/openfpga'

    chip.add('flow', step, 'threads', '4')
    chip.add('flow', step, 'format', 'cmdline')

    chip.add('flow', step, 'vendor', 'openfpga')
    chip.add('flow', step, 'refdir', refdir)
    chip.add('flow', step, 'opt', '-batch -f ' + OPENFPGA_SCRIPT)

    # skip non-floorplan steps
    if step in ("floorplan"):
        chip.add('flow', step, 'exe', 'openfpga')
        chip.add('flow', step, 'copy', 'true')
    else:
        # copy output of this stage along to export stage
        chip.add('flow', step, 'exe', 'cp')
        chip.add('flow', step, 'copy', 'false')

################################
# Set OpenFPGA Runtime Options
################################

def setup_options(chip,step):
    ''' Per tool/step function that returns a dynamic options string based on
    the dictionary settings.
    '''

    options = chip.get('flow', step, 'opt')
    return options

def make_abs_path(path, root):
    '''Helper for constructing absolute path relative to root, if path is not
    already absolute
    '''
    if os.path.isabs(path):
        return path
    return os.path.join(root, path)

################################
# Pre and Post Run Commands
################################
def pre_process(chip,step):
    '''Tool specific function to run before step execution - need to d
    '''

    # skip non-floorplan steps
    if step != 'floorplan':
        return

    topmodule = chip.cfg['design']['value'][-1]

    yosys_blif = 'inputs/' + topmodule + '.blif'
    ace_blif = topmodule + '_ace_out.blif'
    combined_blif = topmodule + '.blif'
    activity_file = topmodule + '.act'

    # Step 1: run ace2
    #
    # These pre-processing steps were taken from the OpenFPGA flow. The first
    # step runs ace2 to get an activity estimation for the circuit. This step
    # produces a new blif file with renamed nets, which is somehow incorporated
    # into the original blif using a perl script provided by OpenFPGA, which
    # gives the final blif passed on to VPR.
    #
    # TODO: determine if activity estimation is necessary if you just want to
    # generate a bitstream? I don't see why it would be, but I couldn't get the
    # OpenFPGA flow to work without passing in an activity file.

    command = ['ace', '-b', yosys_blif, '-o', activity_file, '-n', ace_blif, '-c clk']
    print(command)
    subprocess.run(" ".join(command), shell=True)

    # TODO: should figure out what this script does and if it's necessary (and
    # possibly port to Python) so we don't have perl as an additional dependency
    command = ['perl', 'pro_blif.pl', '-i', ace_blif, '-o', combined_blif, '-initial', yosys_blif]
    subprocess.run(" ".join(command), shell=True)

    # Step 2: fill out shell script template
    #
    # OpenFPGA doesn't have a rich command line interface or a tcl interface, so
    # we use a template script in OpenFPGA's scripting language and fill it in
    # with relevant variables, similar to how the OpenFPGA flow itself works

    cwd = os.getcwd()
    run_dir = cwd + "/../../../" # directory `sc` was run from

    vpr_arch_file = make_abs_path(chip.get('fpga_xml')[-1], run_dir)
    openfpga_arch_file = make_abs_path(chip.get('openfpga_xml')[-1], run_dir)
    sim_settings_file = make_abs_path(chip.get('openfpga_simsettings')[-1], run_dir)
    openfpga_script_template = 'openfpga_script_template.openfpga'

    tmpl_vars = {'VPR_ARCH_FILE': vpr_arch_file,
                 'VPR_TESTBENCH_BLIF': combined_blif,
                 'OPENFPGA_ARCH_FILE': openfpga_arch_file,
                 'OPENFPGA_SIM_SETTING_FILE': sim_settings_file,
                 'ACTIVITY_FILE': activity_file,
                 'TOP': topmodule
                 }

    tmpl = Template(open(openfpga_script_template, encoding='utf-8').read())
    with open(OPENFPGA_SCRIPT, 'w') as f:
        f.write(tmpl.safe_substitute(tmpl_vars))

def post_process(chip,step):
    ''' Tool specific function to run after step execution
    '''
    pass
