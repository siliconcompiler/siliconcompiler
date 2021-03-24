import os

################################
# Setup NextPNR
################################

def setup_tool(chip, step, tool):
    ''' Sets up default settings on a per step basis
    '''

    refdir = 'eda/nextpnr'

    chip.add('flow', step, 'threads', '4')
    chip.add('flow', step, 'format', 'cmdline')
    chip.add('flow', step, 'vendor', 'nextpnr')
    chip.add('flow', step, 'refdir', refdir)
    chip.add('flow', step, 'exe', 'nextpnr-ice40')
    chip.add('flow', step, 'copy', 'true')

    # hardcode settings for icebreaker dev board for now
    chip.add('flow', step, 'option', '--up5k --package sg48 --freq 12')

################################
# Set NextPNR Runtime Options
################################

def setup_options(chip, step, tool):
    ''' Per tool/step function that returns a dynamic options string based on
    the dictionary settings.
    '''

    #Get default opptions from setup
    options = chip.get('flow', step, 'option')

    topmodule = chip.get('design')[-1]

    pcf_file = None
    for constraint_file in chip.get('constraint'):
        if os.path.splitext(constraint_file)[-1] == '.pcf':
            pcf_file = make_abs_path(constraint_file)

    if pcf_file == None:
        chip.logger.error('Pin constraint file required')
        os.sys.exit()

    options.append('--pcf ' + pcf_file)
    options.append('--json inputs/' + topmodule + '.json')
    options.append('--asc outputs/' + topmodule + '.asc')

    return options

def pre_process(chip, step, tool):
    ''' Tool specific function to run before step execution
    '''
    pass

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
