import os
import importlib
import re
import shutil
import sys
import siliconcompiler
from siliconcompiler.floorplan import _infer_diearea

####################################################################
# Make Docs
####################################################################

def make_docs():
    '''
    OpenROAD is an automated physical design platform for
    integreated circuit design with a complete set of features
    needed to translate a synthesized netlist to a tapeout ready
    GDSII.

    Documentation:https://github.com/The-OpenROAD-Project/OpenROAD

    Sources: https://github.com/The-OpenROAD-Project/OpenROAD

    Installation: https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts

    '''

    chip = siliconcompiler.Chip()
    chip.set('arg', 'step', '<step>')
    chip.set('arg', 'index', '<index>')
    chip.set('design', '<design>')
    setup(chip)

    return chip

################################
# Setup Tool (pre executable)
################################

def setup(chip, mode='batch'):

    # default tool settings, note, not additive!

    tool = 'openroad'
    refdir = 'tools/'+tool
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')

    if mode == 'show':
        clobber = True
        script = '/sc_display.tcl'
        option = "-no_init -gui"
    else:
        clobber = False
        script = '/sc_apr.tcl'
        option = "-no_init"

    # exit automatically in batch mode and not bkpt
    if (mode=='batch') & (step not in chip.get('bkpt')):
        option += " -exit"

    chip.set('eda', tool, 'exe', tool, clobber=clobber)
    chip.set('eda', tool, 'vswitch', '-version', clobber=clobber)
    chip.set('eda', tool, 'version', 'v2.0', clobber=clobber)
    chip.set('eda', tool, 'format', 'tcl', clobber=clobber)
    chip.set('eda', tool, 'copy', 'true', clobber=clobber)
    chip.set('eda', tool, 'option',  step, index, option, clobber=clobber)
    chip.set('eda', tool, 'refdir',  step, index, refdir, clobber=clobber)
    chip.set('eda', tool, 'script',  step, index, refdir + script, clobber=clobber)
    chip.set('eda', tool, 'threads', step, index, os.cpu_count(), clobber=clobber)

    # Input/Output requirements
    if step == 'floorplan':
        if (not chip.valid('read', 'netlist', step, index) or
            not chip.get('read', 'netlist', step, index)):
            chip.add('eda', tool, 'input', step, index, chip.get('design') +'.vg')
    else:
        if (not chip.valid('read', 'def', step, index) or
            not chip.get('read', 'def', step, index)):
            chip.add('eda', tool, 'input', step, index, chip.get('design') +'.def')

    chip.add('eda', tool, 'output', step, index, chip.get('design') + '.sdc')
    chip.add('eda', tool, 'output', step, index, chip.get('design') + '.vg')
    chip.add('eda', tool, 'output', step, index, chip.get('design') + '.def')

    # openroad makes use of these parameters
    targetlibs = chip.get('asic', 'logiclib')
    stackup = chip.get('asic', 'stackup')
    if bool(stackup) & bool(targetlibs):
        mainlib = targetlibs[0]
        macrolibs = chip.get('asic', 'macrolib')
        libtype = str(chip.get('library', mainlib, 'arch'))
        techlef = chip.get('pdk', 'aprtech', 'openroad', stackup, libtype, 'lef')

        chip.add('eda', tool, 'require', step, index, ",".join(['asic', 'logiclib']))
        chip.add('eda', tool, 'require', step, index, ",".join(['asic', 'stackup']))
        chip.add('eda', tool, 'require', step, index, ",".join(['library', mainlib, 'arch']))
        chip.add('eda', tool, 'require', step, index, ",".join(['pdk', 'aprtech', 'openroad', stackup, libtype, 'lef']))

        for lib in (targetlibs + macrolibs):
            for corner in chip.getkeys('library', lib, 'nldm'):
                nldm = chip.get('library', lib, 'nldm', corner, 'lib')
                chip.add('eda', tool, 'require', step, index, ",".join(['library', lib, 'nldm', corner, 'lib']))
            lef = chip.get('library', lib, 'lef')
            chip.add('eda', tool, 'require', step, index, ",".join(['library', lib, 'lef']))
    else:
        chip.error = 1
        chip.logger.error(f'Stackup and targetlib paremeters required for OpenROAD.')


    # defining default dictionary
    default_options = {
        'place_density': [],
        'pad_global_place': [],
        'pad_detail_place': [],
        'macro_place_halo': [],
        'macro_place_channel': []
    }

    # Setting up technologies with default values
    # NOTE: no reasonable defaults, for halo and channel.
    # TODO: Could possibly scale with node number for default, but safer to error out?
    # perhaps we should use node as comp instead?
    if chip.get('pdk', 'process'):
        process = chip.get('pdk', 'process')
        if process == 'freepdk45':
            default_options = {
                'place_density': ['0.3'],
                'pad_global_place': ['2'],
                'pad_detail_place': ['1'],
                'macro_place_halo': ['22.4', '15.12'],
                'macro_place_channel': ['18.8', '19.95']
            }
        elif process == 'asap7':
            default_options = {
                'place_density': ['0.77'],
                'pad_global_place': ['2'],
                'pad_detail_place': ['1'],
                'macro_place_halo': ['22.4', '15.12'],
                'macro_place_channel': ['18.8', '19.95']
            }
        elif process == 'skywater130':
            default_options = {
                'place_density': ['0.6'],
                'pad_global_place': ['4'],
                'pad_detail_place': ['2'],
                'macro_place_halo': ['1', '1'],
                'macro_place_channel': ['80', '80']
            }
        else:
            chip.error = 1
            chip.logger.error(f'Process {process} not supported with OpenROAD.')
    else:
        default_options = {
            'place_density': ['1'],
            'pad_global_place': ['<space>'],
            'pad_detail_place': ['<space>'],
            'macro_place_halo': ['<xspace>', '<yspace>'],
            'macro_place_channel': ['<xspace>', '<yspace>']
        }

    for option in default_options:
        if chip.valid('eda', tool, 'variable', step, index, option, quiet=True, default_valid=False):
            chip.logger.info('User provided variable %s OpenROAD flow detected.', option)
        elif not default_options[option]:
            chip.error = 1
            chip.logger.error('Missing variable %s for OpenROAD.', option)
        else:
            chip.set('eda', tool, 'variable', step, index, option, default_options[option], clobber=clobber)

    for clock in chip.getkeys('clock'):
        chip.add('eda', tool, 'require', step, index, ','.join(['clock', clock, 'period']))
        chip.add('eda', tool, 'require', step, index, ','.join(['clock', clock, 'pin']))

################################
# Version Check
################################

def parse_version(stdout):
    # stdout will be in one of the following forms:
    # - 1 08de3b46c71e329a10aa4e753dcfeba2ddf54ddd
    # - 1 v2.0-880-gd1c7001ad
    # - v2.0-1862-g0d785bd84

    # strip off the "1" prefix if it's there
    version = stdout.split()[-1]

    # strip off extra details in new version styles
    return version.split('-')[0]

def pre_process(chip):
    step = chip.get('arg', 'step')

    # Only do diearea inference if we're on floorplanning step and these
    # parameters are all unset.
    if (step != 'floorplan' or
        chip.get('asic', 'diearea') or
        chip.get('asic', 'corearea') or
        ('floorplan' in chip.getkeys('read', 'def'))):
        return

    r = _infer_diearea(chip)
    if r is None:
        return
    diearea, corearea = r

    chip.set('asic', 'diearea', diearea)
    chip.set('asic', 'corearea', corearea)

################################
# Post_process (post executable)
################################

def post_process(chip):
    ''' Tool specific function to run after step execution
    '''

    #Check log file for errors and statistics
    tool = 'openroad'
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    design = chip.get('design')
    logfile = f"{step}.log"

    # basic warning and error grep check on logfile
    chip.set('eda', tool, 'regex', step, index, 'warnings', "WARNING", clobber=False)
    chip.set('eda', tool, 'regex', step, index, 'errors', "ERROR", clobber=False)

    # reports
    for metric in chip.getkeys('metric', step, index):
        if metric not in ('runtime', 'memory',
                          'luts', 'dsps', 'brams'):
            chip.set('eda', tool, 'report', step, index, metric, logfile)

    # parsing log file
    errors = 0
    warnings = 0
    metric = None

    with open(logfile) as f:
        for line in f:
            metricmatch = re.search(r'^SC_METRIC:\s+(\w+)', line)
            errmatch = re.match(r'^Error:', line)
            warnmatch = re.match(r'^\[WARNING', line)
            area = re.search(r'^Design area (\d+)\s+u\^2\s+(.*)\%\s+utilization', line)
            tns = re.search(r'^tns (.*)', line)
            wns = re.search(r'^wns (.*)', line)
            slack = re.search(r'^worst slack (.*)', line)
            vias = re.search(r'^Total number of vias = (.*).', line)
            wirelength = re.search(r'^Total wire length = (.*) um', line)
            power = re.search(r'^Total(.*)', line)
            if metricmatch:
                metric = metricmatch.group(1)
            elif errmatch:
                errors = errors + 1
            elif warnmatch:
                warnings = warnings +1
            elif area:
                #TODO: not sure the openroad utilization makes sense?
                cellarea = round(float(area.group(1)), 2)
                utilization = round(float(area.group(2)), 2)
                totalarea = round(cellarea/(utilization/100), 2)
                chip.set('metric', step, index, 'cellarea', 'real', cellarea, clobber=True)
                chip.set('metric', step, index, 'totalarea', 'real', totalarea, clobber=True)
                chip.set('metric', step, index, 'utilization', 'real', utilization, clobber=True)
            elif tns:
                chip.set('metric', step, index, 'setuptns', 'real', round(float(tns.group(1)), 2), clobber=True)
            elif wns:
                chip.set('metric', step, index, 'setupwns', 'real', round(float(wns.group(1)), 2), clobber=True)
            elif slack:
                chip.set('metric', step, index, metric, 'real', round(float(slack.group(1)), 2), clobber=True)
            elif wirelength:
                chip.set('metric', step, index, 'wirelength', 'real', round(float(wirelength.group(1)), 2), clobber=True)
            elif vias:
                chip.set('metric', step, index, 'vias', 'real', int(vias.group(1)), clobber=True)
            elif metric == "power":
                if power:
                    powerlist = power.group(1).split()
                    leakage = powerlist[2]
                    total = powerlist[3]
                    chip.set('metric', step, index, 'peakpower', 'real', float(total), clobber=True)
                    chip.set('metric', step, index, 'standbypower', 'real', float(leakage), clobber=True)

    #Setting Warnings and Errors
    chip.set('metric', step, index, 'errors', 'real', errors, clobber=True)
    chip.set('metric', step, index, 'warnings', 'real', warnings, clobber=True)

    #Temporary superhack!rm
    #Getting cell count and net number from DEF
    if errors == 0:
        with open("outputs/" + design + ".def") as f:
            for line in f:
                cells = re.search(r'^COMPONENTS (\d+)', line)
                nets = re.search(r'^NETS (\d+)', line)
                pins = re.search(r'^PINS (\d+)', line)
                if cells:
                    chip.set('metric', step, index, 'cells', 'real', int(cells.group(1)), clobber=True)
                elif nets:
                    chip.set('metric', step, index, 'nets', 'real', int(nets.group(1)), clobber=True)
                elif pins:
                    chip.set('metric', step, index, 'pins', 'real', int(pins.group(1)), clobber=True)

    if step == 'sta':
        # Copy along GDS for verification steps that rely on it
        design = chip.get('design')
        shutil.copy(f'inputs/{design}.gds', f'outputs/{design}.gds')

    #Return 0 if successful
    return 0



##################################################
if __name__ == "__main__":

    chip = make_docs()
    chip.write_manifest("openroad.json")
