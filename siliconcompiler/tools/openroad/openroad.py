import math
import os
import re

import siliconcompiler
from siliconcompiler.floorplan import _infer_diearea

####################################################################
# Make Docs
####################################################################

def make_docs():
    '''
    OpenROAD is an automated physical design platform for
    integrated circuit design with a complete set of features
    needed to translate a synthesized netlist to a tapeout ready
    GDSII.

    Documentation:https://github.com/The-OpenROAD-Project/OpenROAD

    Sources: https://github.com/The-OpenROAD-Project/OpenROAD

    Installation: https://github.com/The-OpenROAD-Project/OpenROAD-flow-scripts

    '''

    chip = siliconcompiler.Chip('<design>')
    chip.set('arg', 'step', '<step>')
    chip.set('arg', 'index', '<index>')
    # TODO: how to make it clear in docs that certain settings are
    # target-dependent?
    chip.load_target('freepdk45_demo')
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
    flow = chip.get('option', 'flow')
    pdkname = chip.get('option', 'pdk')

    if mode == 'show':
        clobber = True
        option = "-no_init -gui"
    else:
        clobber = False
        option = "-no_init"

    script = 'sc_apr.tcl'

    # exit automatically in batch mode and not bkpt
    if (mode=='batch') and (step not in chip.get('option', 'bkpt')):
        option += " -exit"

    chip.set('tool', tool, 'exe', tool)
    chip.set('tool', tool, 'vswitch', '-version')
    chip.set('tool', tool, 'version', '>=v2.0-3394', clobber=clobber)
    chip.set('tool', tool, 'format', 'tcl', clobber=clobber)
    chip.set('tool', tool, 'option',  step, index, option, clobber=clobber)
    chip.set('tool', tool, 'refdir',  step, index, refdir, clobber=clobber)
    chip.set('tool', tool, 'script',  step, index, script, clobber=clobber)

    # normalizing thread count based on parallelism and local
    threads = os.cpu_count()
    if not chip.get('option', 'remote') and step in chip.getkeys('flowgraph', flow):
        np = len(chip.getkeys('flowgraph', flow, step))
        threads = int(math.ceil(os.cpu_count()/np))

    chip.set('tool', tool, 'threads', step, index, threads, clobber=clobber)

    # Input/Output requirements for default asicflow steps
    # TODO: long-term, we want to remove hard-coded step names from tool files.
    if step in ['floorplan', 'physyn', 'place', 'cts', 'route', 'dfm']:
        design = chip.top()
        if step == 'floorplan':
            if (not chip.valid('input', 'netlist') or
                not chip.get('input', 'netlist')):
                chip.add('tool', tool, 'input', step, index, design +'.vg')
        else:
            if (not chip.valid('input', 'def') or
                not chip.get('input', 'def')):
                chip.add('tool', tool, 'input', step, index, design +'.def')

        chip.add('tool', tool, 'output', step, index, design + '.sdc')
        chip.add('tool', tool, 'output', step, index, design + '.vg')
        chip.add('tool', tool, 'output', step, index, design + '.def')

    # openroad makes use of these parameters
    targetlibs = chip.get('asic', 'logiclib')
    stackup = chip.get('asic', 'stackup')
    if stackup and targetlibs:
        mainlib = targetlibs[0]
        macrolibs = chip.get('asic', 'macrolib')
        #Note: only one footprint supported in maainlib
        libtype = chip.get('library', mainlib, 'asic', 'libarch')

        chip.add('tool', tool, 'require', step, index, ",".join(['asic', 'logiclib']))
        chip.add('tool', tool, 'require', step, index, ",".join(['asic', 'stackup',]))
        # chip.add('tool', tool, 'require', step, index, ",".join(['library', mainlib, 'asic', 'footprint', libtype, 'symmetry']))
        # chip.add('tool', tool, 'require', step, index, ",".join(['library', mainlib, 'asic', 'footprint', libtype, 'size']))
        chip.add('tool', tool, 'require', step, index, ",".join(['pdk', pdkname, 'aprtech', 'openroad', stackup, libtype, 'lef']))
        if chip.valid('input', 'floorplan.def'):
            chip.set('tool', tool, 'require', step, index, ",".join(['input', 'floorplan.def']))

        for lib in (targetlibs + macrolibs):
            if 'nldm' in chip.getkeys('library', lib, 'model', 'timing'):
                for corner in chip.getkeys('library', lib, 'model', 'timing', 'nldm'):
                    chip.add('tool', tool, 'require', step, index, ",".join(['library', lib, 'model', 'timing', 'nldm', corner]))
            chip.add('tool', tool, 'require', step, index, ",".join(['library', lib, 'model', 'layout', 'lef', stackup]))
    else:
        chip.error(f'Stackup and logiclib parameters required for OpenROAD.')

    variables = (
        'place_density',
        'pad_global_place',
        'pad_detail_place',
        'macro_place_halo',
        'macro_place_channel'
    )
    for variable in variables:
        # For each OpenROAD tool variable, read default from PDK and write it
        # into schema. If PDK doesn't contain a default, the value must be set
        # by the user, so we add the variable keypath as a requirement.
        if chip.valid('pdk', pdkname, 'var', tool, stackup, variable):
            value = chip.get('pdk', pdkname, 'var', tool, stackup, variable)
            # Clobber needs to be False here, since a user might want to
            # overwrite these.
            chip.set('tool', tool, 'var', step, index, variable, value,
                     clobber=False)

        keypath = ','.join(['tool', tool, 'var', step, index, variable])
        chip.add('tool', tool, 'require', step, index, keypath)

    #for clock in chip.getkeys('clock'):
    #    chip.add('tool', tool, 'require', step, index, ','.join(['clock', clock, 'period']))
    #    chip.add('tool', tool, 'require', step, index, ','.join(['clock', clock, 'pin']))

    #for supply in chip.getkeys('supply'):
    #    chip.add('tool', tool, 'require', step, index, ','.join(['supply', supply, 'level']))
    #    chip.add('tool', tool, 'require', step, index, ','.join(['supply', supply, 'pin']))

    # basic warning and error grep check on logfile
    chip.set('tool', tool, 'regex', step, index, 'warnings', r'^\[WARNING', clobber=False)
    chip.set('tool', tool, 'regex', step, index, 'errors', r'ERROR', clobber=False)

    # reports
    logfile = f"{step}.log"
    for metric in (
        'cellarea', 'totalarea', 'utilization', 'setuptns', 'setupwns',
        'setupslack', 'wirelength', 'vias', 'peakpower', 'leakagepower'
    ):
        chip.set('tool', tool, 'report', step, index, metric, logfile)

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

    pieces = version.split('-')
    if len(pieces) > 1:
        # strip off the hash in the new version style
        return '-'.join(pieces[:-1])
    else:
        return pieces[0]

def normalize_version(version):
    if '.' in version:
        return version.lstrip('v')
    else:
        return '0'

def pre_process(chip):
    step = chip.get('arg', 'step')

    # Only do diearea inference if we're on floorplanning step and these
    # parameters are all unset.
    if (step != 'floorplan' or
        chip.get('asic', 'diearea') or
        chip.get('asic', 'corearea') or
        chip.valid('input', 'floorplan.def')):
        return

    r = _infer_diearea(chip)
    if r is None:
        return
    diearea, corearea = r

    # TODO: this feels like a hack: putting these here puts them in
    # sc_manifest.tcl, but they don't remain in the manifest in future steps.
    chip.set('asic', 'diearea', diearea)
    chip.set('asic', 'corearea', corearea)

################################
# Post_process (post executable)
################################

def post_process(chip):
    ''' Tool specific function to run after step execution
    '''

    #Check log file for errors and statistics
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool = 'openroad'
    logfile = f"{step}.log"

    # parsing log file
    metric = None

    with open(logfile) as f:
        for line in f:
            metricmatch = re.search(r'^SC_METRIC:\s+(\w+)', line)
            area = re.search(r'^Design area (\d+)\s+u\^2\s+(.*)\%\s+utilization', line)
            tns = re.search(r'^tns (.*)', line)
            wns = re.search(r'^wns (.*)', line)
            slack = re.search(r'^worst slack (.*)', line)
            vias = re.search(r'^Total number of vias = (.*).', line)
            wirelength = re.search(r'^Total wire length = (.*) um', line)
            power = re.search(r'^Total(.*)', line)
            if metricmatch:
                metric = metricmatch.group(1)
            elif area:
                #TODO: not sure the openroad utilization makes sense?
                cellarea = round(float(area.group(1)), 2)
                utilization = round(float(area.group(2)), 2)
                if utilization == 0:
                    totalarea = 0.0
                else:
                    totalarea = round(cellarea/(utilization/100), 2)
                chip.set('metric', step, index, 'cellarea', cellarea, clobber=True)
                chip.set('metric', step, index, 'totalarea', totalarea, clobber=True)
                chip.set('metric', step, index, 'utilization', utilization, clobber=True)
            elif tns:
                chip.set('metric', step, index, 'setuptns', round(float(tns.group(1)), 2), clobber=True)
            elif wns:
                chip.set('metric', step, index, 'setupwns', round(float(wns.group(1)), 2), clobber=True)
            elif slack:
                chip.set('metric', step, index, 'setupslack', round(float(slack.group(1)), 2), clobber=True)
            elif wirelength:
                chip.set('metric', step, index, 'wirelength', round(float(wirelength.group(1)), 2), clobber=True)
            elif vias:
                chip.set('metric', step, index, 'vias', int(vias.group(1)), clobber=True)
            elif metric == "power":
                if power:
                    powerlist = power.group(1).split()
                    leakage = powerlist[2]
                    total = powerlist[3]
                    chip.set('metric', step, index, 'peakpower', float(total), clobber=True)
                    chip.set('metric', step, index, 'leakagepower', float(leakage), clobber=True)

    #Temporary superhack!rm
    #Getting cell count and net number from the first available DEF file output (if any)
    out_def = ''
    out_files = []
    if chip.valid('tool', tool, 'output', step, index):
        out_files = chip.get('tool', tool, 'output', step, index)

    if out_files:
        for fn in out_files:
            if fn.endswith('.def'):
                out_def = fn
                break
    out_def_path = os.path.join('outputs', out_def)
    if out_def and os.path.isfile(out_def_path):
        with open(os.path.join('outputs', out_def)) as f:
            for line in f:
                cells = re.search(r'^COMPONENTS (\d+)', line)
                nets = re.search(r'^NETS (\d+)', line)
                pins = re.search(r'^PINS (\d+)', line)
                if cells:
                    chip.set('metric', step, index, 'cells', int(cells.group(1)), clobber=True)
                elif nets:
                    chip.set('metric', step, index, 'nets', int(nets.group(1)), clobber=True)
                elif pins:
                    chip.set('metric', step, index, 'pins', int(pins.group(1)), clobber=True)

##################################################
if __name__ == "__main__":

    chip = make_docs()
    chip.write_manifest("openroad.json")
