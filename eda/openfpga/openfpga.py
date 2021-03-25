import os
from string import Template
import defusedxml.ElementTree as ET

################################
# Setup OpenFPGA
################################

OPENFPGA_SCRIPT = 'openfpga_script.openfpga'

def setup_tool(chip, step, tool):
    ''' Sets up default settings on a per step basis
    '''

    refdir = 'eda/openfpga'

    chip.add('flow', step, 'threads', '4')
    chip.add('flow', step, 'format', 'cmdline')

    chip.add('flow', step, 'vendor', 'openfpga')
    chip.add('flow', step, 'refdir', refdir)
    chip.add('flow', step, 'option', '-batch -f ' + OPENFPGA_SCRIPT)
    chip.add('flow', step, 'exe', 'openfpga')
    chip.add('flow', step, 'copy', 'true')

################################
# Set OpenFPGA Runtime Options
################################

def setup_options(chip, step, tool):
    ''' Per tool/step function that returns a dynamic options string based on
    the dictionary settings.
    '''

    options = chip.get('flow', step, 'option')
    return options

################################
# Pre and Post Run Commands
################################

def pre_process(chip, step, tool):
    '''Tool specific function to run before step execution that fills out shell
    script template

    OpenFPGA doesn't have a rich command line interface or a tcl interface, so
    we use a template script in OpenFPGA's scripting language and fill it in
    with relevant variables, similar to how the OpenFPGA flow itself works
    '''

    topmodule = chip.cfg['design']['value'][-1]

    input_blif = 'inputs/' + topmodule + '.blif'

    # Search through and parse architecture XML files to find VPR and OpenFPGA
    # files
    vpr_arch_file = None
    openfpga_arch_file = None

    for arch_file in chip.get('fpga_xml'):
        path = make_abs_path(arch_file)
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
    openfpga_script_template = 'openfpga_script_template.openfpga'

    tmpl_vars = {'VPR_ARCH_FILE': vpr_arch_file,
                 'VPR_TESTBENCH_BLIF': input_blif,
                 'OPENFPGA_ARCH_FILE': openfpga_arch_file,
                 'TOP': topmodule
                 }

    tmpl = Template(open(openfpga_script_template, encoding='utf-8').read())
    with open(OPENFPGA_SCRIPT, 'w') as f:
        f.write(tmpl.safe_substitute(tmpl_vars))

def post_process(chip, step, tool):
    ''' Tool specific function to run after step execution
    '''
    pass

################################
# Utilities
################################

def make_abs_path(path):
    '''Helper for constructing absolute path, assuming `path` is relative to
    directory `sc` was run from
    '''

    if os.path.isabs(path):
        return path

    cwd = os.getcwd()
    run_dir = cwd + '/../../../' # directory `sc` was run from
    return os.path.join(run_dir, path)
