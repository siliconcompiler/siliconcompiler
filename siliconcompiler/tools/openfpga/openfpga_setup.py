import os
from string import Template
import defusedxml.ElementTree as ET
import siliconcompiler
from siliconcompiler.schema import schema_path

################################
# Setup OpenFPGA
################################

OPENFPGA_SCRIPT = 'openfpga_script.openfpga'

def setup_tool(chip, step):
    ''' Sets up default settings on a per step basis
    '''

    refdir = 'siliconcompiler/tools/openfpga'

    tool = 'openfpga'
    chip.add('eda', tool, step, 'threads', '4')
    chip.add('eda', tool, step, 'format', 'cmdline')

    chip.add('eda', tool, step, 'vendor', 'openfpga')
    chip.add('eda', tool, step, 'refdir', refdir)
    if step == 'apr':
        chip.add('eda', tool, step, 'exe', 'openfpga')
        chip.add('eda', tool, step, 'option', 'cmdline', '-batch -f ' + OPENFPGA_SCRIPT)
    elif step == 'bitstream':
        # bitstream step is currently a NOP, since apr and bitstream generation
        # are integrated in shell script
        chip.add('eda', tool, step, 'exe', 'cp')
        chip.add('eda', tool, step, 'option', 'cmdline', ' -r inputs/ outputs/')
    chip.add('eda', tool, step, 'copy', 'true')

    topmodule = chip.get('design')

    input_blif = 'inputs/' + topmodule + '.blif'

    # Search through and parse architecture XML files to find VPR and OpenFPGA
    # files
    vpr_arch_file = None
    openfpga_arch_file = None

    for arch_file in chip.get('fpga', 'arch'):
        path = schema_path(arch_file)
        root_tag = ET.parse(path).getroot().tag
        if root_tag == 'architecture':
            vpr_arch_file = path
        elif root_tag == 'openfpga_architecture':
            openfpga_arch_file = path

    if vpr_arch_file == None:
        chip.logger.error('No VPR architecture file was specified')
        os.sys.exit()
    if openfpga_arch_file == None:
        chip.logger.error('No OpenFPGA architecture file was specified')
        os.sys.exit()

    # Fill in OpenFPGA shell script template
    scriptdir = os.path.dirname(os.path.abspath(__file__))

    openfpga_script_template = f'{scriptdir}/openfpga_script_template.openfpga'

    tmpl_vars = {'VPR_ARCH_FILE': vpr_arch_file,
                 'VPR_TESTBENCH_BLIF': input_blif,
                 'OPENFPGA_ARCH_FILE': openfpga_arch_file,
                 'TOP': topmodule
                 }

    tmpl = Template(open(openfpga_script_template, encoding='utf-8').read())
    with open(OPENFPGA_SCRIPT, 'w') as f:
        f.write(tmpl.safe_substitute(tmpl_vars))

################################
# Post Run Command
################################

def post_process(chip, step):
    ''' Tool specific function to run after step execution
    '''

    # Return 0 if successful
    return 0
