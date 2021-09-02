import os
from string import Template
import defusedxml.ElementTree as ET
import siliconcompiler
from siliconcompiler.schema_utils import schema_path

################################
# Setup OpenFPGA
################################

OPENFPGA_SCRIPT = 'openfpga_script.openfpga'

def setup_tool(chip, step, index):
    ''' Sets up default settings on a per step basis
    '''

    tool = 'openfpga'
    refdir = 'siliconcompiler/tools/openfpga'

    chip.set('eda', tool, step, index, 'version', '0.0')
    chip.set('eda', tool, step, index, 'vendor', 'openfpga')
    chip.set('eda', tool, step, index, 'copy', 'true')
    chip.set('eda', tool, step, index, 'refdir', refdir)

    if step == 'apr':
        chip.set('eda', tool, step, index, 'exe', 'openfpga')
        chip.add('eda', tool, step, index, 'option', 'cmdline', '-batch -f ' + OPENFPGA_SCRIPT)
    elif step == 'bitstream':
        # bitstream step is currently a NOP, since apr and bitstream generation
        # are integrated in shell script
        chip.set('eda', tool, step, index, 'exe', 'cp')
        chip.add('eda', tool, step, index, 'option', 'cmdline', ' -r inputs/ outputs/')


def pre_process(chip, step, index):
    topmodule = chip.get('design')

    input_blif = 'inputs/' + topmodule + '.blif'

    # Search through and parse architecture XML files to find VPR and OpenFPGA
    # files
    vpr_arch_file = None
    openfpga_arch_file = None
    openfpga_sim_file = None

    for arch_file in chip.get('fpga', 'arch'):
        path = schema_path(arch_file)
        root_tag = ET.parse(path).getroot().tag
        if root_tag == 'architecture':
            vpr_arch_file = path
        elif root_tag == 'openfpga_architecture':
            openfpga_arch_file = path
        elif root_tag == 'openfpga_simulation_setting':
            openfpga_sim_file = path

    # Raising exceptions here ensures the issue is caught by runstep() and
    # everything is killed safely with regards to parallel processing.
    if vpr_arch_file == None:
        raise ValueError('No VPR architecture file was specified')
    if openfpga_arch_file == None:
        raise ValueError('No OpenFPGA architecture file was specified')
    if openfpga_sim_file == None:
        raise ValueError('No OpenFPGA simulation file was specified')

    # Fill in OpenFPGA shell script template
    scriptdir = os.path.dirname(os.path.abspath(__file__))

    openfpga_script_template = f'{scriptdir}/openfpga_script_template.openfpga'

    tmpl_vars = {'VPR_ARCH_FILE': vpr_arch_file,
                 'VPR_TESTBENCH_BLIF': input_blif,
                 'OPENFPGA_ARCH_FILE': openfpga_arch_file,
                 'OPENFPGA_SIM_FILE': openfpga_sim_file,
                 'TOP': topmodule
                 }

    tmpl = Template(open(openfpga_script_template, encoding='utf-8').read())
    with open(OPENFPGA_SCRIPT, 'w') as f:
        f.write(tmpl.safe_substitute(tmpl_vars))

################################
# Post Run Command
################################

def post_process(chip, step, index):
    ''' Tool specific function to run after step execution
    '''

    # Return 0 if successful
    return 0

##################################################
if __name__ == "__main__":

    # File being executed
    prefix = os.path.splitext(os.path.basename(__file__))[0]
    output = prefix + '.json'

    # create a chip instance
    chip = siliconcompiler.Chip()
    # load configuration
    setup_tool(chip, step='apr')
    # write out results
    chip.writecfg(output)
