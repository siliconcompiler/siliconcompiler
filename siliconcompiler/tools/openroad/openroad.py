'''
OpenROAD is an automated physical design platform for
integrated circuit design with a complete set of features
needed to translate a synthesized netlist to a tapeout ready
GDSII.

Documentation: https://openroad.readthedocs.io/

Sources: https://github.com/The-OpenROAD-Project/OpenROAD

Installation: https://github.com/The-OpenROAD-Project/OpenROAD
'''

import math
import os
import json
from jinja2 import Template


####################################################################
# Make Docs
####################################################################
def make_docs(chip):
    chip.load_target("asap7_demo")


################################
# Setup Tool (pre executable)
################################
def setup_tool(chip, exit=True, clobber=True):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = chip._get_tool_task(step, index)

    chip.set('tool', tool, 'exe', tool)
    chip.set('tool', tool, 'vswitch', '-version')
    chip.set('tool', tool, 'version', '>=v2.0-10370', clobber=clobber)
    chip.set('tool', tool, 'format', 'tcl', clobber=clobber)

    # exit automatically in batch mode and not breakpoint
    option = ''
    if exit and not chip.get('option', 'breakpoint', step=step, index=index):
        option += " -exit"

    option += " -metrics reports/metrics.json"
    chip.set('tool', tool, 'task', task, 'option', option, step=step, index=index, clobber=clobber)


def setup(chip):

    # default tool settings, note, not additive!

    tool = 'openroad'
    script = 'sc_apr.tcl'
    refdir = os.path.join('tools', tool, 'scripts')

    design = chip.top()

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    flow = chip.get('option', 'flow')
    task = chip._get_task(step, index)
    pdkname = chip.get('option', 'pdk')
    targetlibs = chip.get('asic', 'logiclib', step=step, index=index)
    mainlib = _get_mainlib(chip)
    macrolibs = chip.get('asic', 'macrolib', step=step, index=index)
    stackup = chip.get('option', 'stackup')
    delaymodel = chip.get('asic', 'delaymodel', step=step, index=index)
    libtype = chip.get('library', mainlib, 'asic', 'libarch', step=step, index=index)

    is_screenshot = task == 'screenshot'
    is_show_screenshot = task == 'show' or is_screenshot

    if is_show_screenshot:
        clobber = True
    else:
        clobber = False

    # Fixed for tool
    setup_tool(chip, exit=task != 'show', clobber=clobber)

    # normalizing thread count based on parallelism and local
    threads = os.cpu_count()
    if not chip.get('option', 'remote') and step in chip.getkeys('flowgraph', flow):
        np = len(chip.getkeys('flowgraph', flow, step))
        threads = int(math.ceil(os.cpu_count() / np))

    # Input/Output requirements for default asicflow steps

    chip.set('tool', tool, 'task', task, 'refdir', refdir,
             step=step, index=index, clobber=clobber)
    chip.set('tool', tool, 'task', task, 'script', script,
             step=step, index=index, clobber=clobber)
    chip.set('tool', tool, 'task', task, 'threads', threads,
             step=step, index=index, clobber=clobber)

    chip.add('tool', tool, 'task', task, 'output', design + '.sdc', step=step, index=index)
    chip.add('tool', tool, 'task', task, 'output', design + '.vg', step=step, index=index)
    chip.add('tool', tool, 'task', task, 'output', design + '.def', step=step, index=index)
    chip.add('tool', tool, 'task', task, 'output', design + '.odb', step=step, index=index)

    if chip.get('option', 'nodisplay'):
        # Tells QT to use the offscreen platform if nodisplay is used
        chip.set('tool', tool, 'task', task, 'env', 'QT_QPA_PLATFORM', 'offscreen',
                 step=step, index=index)

    if delaymodel != 'nldm':
        chip.logger.error(f'{delaymodel} delay model is not supported by {tool}, only nldm')

    if stackup and targetlibs:
        # Note: only one footprint supported in mainlib
        chip.add('tool', tool, 'task', task, 'require',
                 ",".join(['asic', 'logiclib']),
                 step=step, index=index)
        chip.add('tool', tool, 'task', task, 'require',
                 ",".join(['option', 'stackup']),
                 step=step, index=index)
        chip.add('tool', tool, 'task', task, 'require',
                 ",".join(['library', mainlib, 'asic', 'site', libtype]),
                 step=step, index=index)
        chip.add('tool', tool, 'task', task, 'require',
                 ",".join(['pdk', pdkname, 'aprtech', 'openroad', stackup, libtype, 'lef']),
                 step=step, index=index)

        for lib in targetlibs:
            for timing_key in get_library_timing_keypaths(chip, lib).values():
                chip.add('tool', tool, 'task', task, 'require', ",".join(timing_key),
                         step=step, index=index)
            chip.add('tool', tool, 'task', task, 'require',
                     ",".join(['library', lib, 'output', stackup, 'lef']),
                     step=step, index=index)
        for lib in macrolibs:
            for timing_key in get_library_timing_keypaths(chip, lib).values():
                if chip.valid(*timing_key):
                    chip.add('tool', tool, 'task', task, 'require', ",".join(timing_key),
                             step=step, index=index)
            chip.add('tool', tool, 'task', task, 'require',
                     ",".join(['library', lib, 'output', stackup, 'lef']),
                     step=step, index=index)
    else:
        chip.error('Stackup and logiclib parameters required for OpenROAD.')

    # Set required keys
    for var0, var1 in [('openroad_tiehigh_cell', 'openroad_tiehigh_port'),
                       ('openroad_tiehigh_cell', 'openroad_tiehigh_port')]:
        key0 = ['library', mainlib, 'option', 'var', tool, var0]
        key1 = ['library', mainlib, 'option', 'var', tool, var1]
        if chip.valid(*key0):
            chip.add('tool', tool, 'task', task, 'require', ",".join(key1), step=step, index=index)
        if chip.valid(*key1):
            chip.add('tool', tool, 'task', task, 'require', ",".join(key0), step=step, index=index)

    for key in (['pdk', pdkname, 'var', 'openroad', 'rclayer_signal', stackup],
                ['pdk', pdkname, 'var', 'openroad', 'rclayer_clock', stackup],
                ['pdk', pdkname, 'var', 'openroad', 'pin_layer_horizontal', stackup],
                ['pdk', pdkname, 'var', 'openroad', 'pin_layer_vertical', stackup]):
        chip.add('tool', tool, 'task', task, 'require',
                 ",".join(key),
                 step=step, index=index)

    # set default values for openroad
    _define_ord_params(chip)
    _define_sta_params(chip)
    _define_sdc_params(chip)
    _define_ifp_params(chip)
    _define_pad_params(chip)
    _define_ppl_params(chip)
    _define_mpl_params(chip)
    _define_pdn_params(chip)
    _define_psm_params(chip)
    _define_gpl_params(chip)
    _define_dpl_params(chip)
    _define_dpo_params(chip)
    _define_cts_params(chip)
    _define_rsz_params(chip)
    _define_grt_params(chip)
    _define_ant_params(chip)
    _define_drt_params(chip)
    _define_fin_params(chip)
    _define_pex_params(chip)

    # basic warning and error grep check on logfile
    chip.set('tool', tool, 'task', task, 'regex', 'warnings', r'^\[WARNING|^Warning',
             step=step, index=index, clobber=False)
    chip.set('tool', tool, 'task', task, 'regex', 'errors', r'^\[ERROR',
             step=step, index=index, clobber=False)


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
    index = chip.get('arg', 'index')
    tool, task = chip._get_tool_task(step, index)
    pdkname = chip.get('option', 'pdk')
    targetlibs = chip.get('asic', 'logiclib', step=step, index=index)
    macrolibs = chip.get('asic', 'macrolib', step=step, index=index)
    mainlib = _get_mainlib(chip)
    stackup = chip.get('option', 'stackup')
    libtype = chip.get('library', mainlib, 'asic', 'libarch', step=step, index=index)

    # set tapcell file
    tapfile = None
    if chip.valid('library', mainlib, 'option', 'file', 'openroad_tapcells'):
        tapfile = chip.find_files('library', mainlib, 'option', 'file', 'openroad_tapcells')
    elif chip.valid('pdk', pdkname, 'aprtech', tool, stackup, libtype, 'tapcells'):
        tapfile = chip.find_files('pdk', pdkname, 'aprtech', tool, stackup, libtype, 'tapcells')
    if tapfile:
        chip.set('tool', tool, 'task', task, 'file', 'ifp_tapcell', tapfile,
                 step=step, index=index, clobber=False)

    for libvar, openroadvar in [('openroad_pdngen', 'pdn_config'),
                                ('openroad_global_connect', 'global_connect')]:
        if chip.valid('tool', tool, 'task', task, 'file', openroadvar) and \
           chip.get('tool', tool, 'task', task, 'file', openroadvar, step=step, index=index):
            # value already set
            continue

        # copy from libs
        for lib in targetlibs + macrolibs:
            if chip.valid('library', lib, 'option', 'file', libvar):
                for vfile in chip.find_files('library', lib, 'option', 'file', libvar):
                    chip.add('tool', tool, 'task', task, 'file', openroadvar, vfile,
                             step=step, index=index)


################################
# Post_process (post executable)
################################
def post_process(chip):
    ''' Tool specific function to run after step execution
    '''

    # Check log file for errors and statistics
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = chip._get_tool_task(step, index)

    metric_reports = {
        "setuptns": ["timing/total_negative_slack.rpt"],
        "setupslack": ["timing/worst_slack.setup.rpt", "timing/setup.rpt", "timing/setup.topN.rpt"],
        "setuppaths": ["timing/setup.topN.rpt"],
        "holdslack": ["timing/worst_slack.hold.rpt", "timing/hold.rpt", "timing/hold.topN.rpt"],
        "holdpaths": ["timing/hold.topN.rpt"],
        "unconstrained": ["timing/unconstrained.topN.rpt"],
        "peakpower": [f"power/{corner}.rpt" for corner in chip.get('tool', tool, 'task', task,
                                                                   'var', 'timing_corners',
                                                                   step=step, index=index)],
        "drvs": ["timing/drv_violators.rpt",
                 "floating_nets.rpt",
                 f"{chip.design}_antenna.rpt",
                 f"{chip.design}_antenna_post_repair.rpt",
                 f"{chip.design}_drc.rpt"]
    }
    metric_reports["leakagepower"] = metric_reports["peakpower"]

    metrics_file = "reports/metrics.json"

    def get_metric_sources(metric):
        metric_sources = [metrics_file]
        if metric in metric_reports:
            for metric_file in metric_reports[metric]:
                metric_path = f'reports/{metric_file}'
                if os.path.exists(metric_path):
                    metric_sources.append(metric_path)
        return metric_sources

    # parsing log file
    with open(metrics_file, 'r') as f:
        metrics = json.load(f)

        or_units = {}
        for unit, or_unit in [('time', 'run__flow__platform__time_units'),
                              ('capacitance', 'run__flow__platform__capacitance_units'),
                              ('resistance', 'run__flow__platform__resistance_units'),
                              ('volt', 'run__flow__platform__voltage_units'),
                              ('amp', 'run__flow__platform__current_units'),
                              ('power', 'run__flow__platform__power_units'),
                              ('distance', 'run__flow__platform__distance_units')]:
            if or_unit in metrics:
                # Remove first digit
                metric_unit = metrics[or_unit][1:]
                or_units[unit] = metric_unit

        or_units['distance'] = 'um'  # always microns
        or_units['power'] = 'W'  # always watts
        or_units['area'] = f"{or_units['distance']}^2"
        or_units['frequency'] = 'Hz'  # always hertz

        has_timing = True
        if 'sc__metric__timing__clocks' in metrics:
            has_timing = metrics['sc__metric__timing__clocks'] > 0

        for metric, or_metric, or_use, or_unit in [
            ('vias', 'sc__step__route__vias', True, None),
            ('wirelength', 'sc__step__route__wirelength', True, 'distance'),
            ('cellarea', 'sc__metric__design__instance__area', True, 'area'),
            ('totalarea', 'sc__metric__design__core__area', True, 'area'),
            ('utilization', 'sc__metric__design__instance__utilization', True, 100.0),
            ('setuptns', 'sc__metric__timing__setup__tns', has_timing, 'time'),
            ('holdtns', 'sc__metric__timing__hold__tns', has_timing, 'time'),
            ('setupslack', 'sc__metric__timing__setup__ws', has_timing, 'time'),
            ('holdslack', 'sc__metric__timing__hold__ws', has_timing, 'time'),
            ('fmax', 'sc__metric__timing__fmax', has_timing, 'frequency'),
            ('setuppaths', 'sc__metric__timing__drv__setup_violation_count', True, None),
            ('holdpaths', 'sc__metric__timing__drv__hold_violation_count', True, None),
            ('unconstrained', 'sc__metric__timing__unconstrained', True, None),
            ('peakpower', 'sc__metric__power__total', True, 'power'),
            ('leakagepower', 'sc__metric__power__leakage__total', True, 'power'),
            ('pins', 'sc__metric__design__io', True, None),
            ('cells', 'sc__metric__design__instance__count', True, None),
            ('macros', 'sc__metric__design__instance__count__macros', True, None),
            ('nets', 'sc__metric__design__nets', True, None),
            ('registers', 'sc__metric__design__registers', True, None),
            ('buffers', 'sc__metric__design__buffers', True, None)
        ]:
            if or_metric in metrics:
                value = metrics[or_metric]

                # Check for INF timing
                if or_unit == 'time' and value > 1e38:
                    or_use = False

                if or_unit:
                    if or_unit in or_units:
                        or_unit = or_units[or_unit]
                    else:
                        value *= or_unit
                        or_unit = None

                if or_use:
                    chip._record_metric(step, index, metric, value,
                                        get_metric_sources(metric),
                                        source_unit=or_unit)

        # setup wns and hold wns can be computed from setup slack and hold slack
        if 'sc__metric__timing__setup__ws' in metrics and \
           has_timing and \
           chip.get('metric', 'setupslack', step=step, index=index) is not None:
            wns = min(0.0, chip.get('metric', 'setupslack', step=step, index=index))
            wns_units = chip.get('metric', 'setupslack', field='unit')
            chip._record_metric(step, index, 'setupwns', wns,
                                get_metric_sources('setupslack'),
                                source_unit=wns_units)

        if 'sc__metric__timing__hold__ws' in metrics and \
           has_timing and \
           chip.get('metric', 'holdslack', step=step, index=index) is not None:
            wns = min(0.0, chip.get('metric', 'holdslack', step=step, index=index))
            wns_units = chip.get('metric', 'holdslack', field='unit')
            chip._record_metric(step, index, 'holdwns', wns,
                                get_metric_sources('holdslack'),
                                source_unit=wns_units)

        drvs = None
        for metric in ['sc__metric__timing__drv__max_slew',
                       'sc__metric__timing__drv__max_cap',
                       'sc__metric__timing__drv__max_fanout',
                       'sc__step__route__drc_errors',
                       'sc__metric__antenna__violating__nets',
                       'sc__metric__antenna__violating__pins']:
            if metric in metrics:
                if drvs is None:
                    drvs = int(metrics[metric])
                else:
                    drvs += int(metrics[metric])

        if drvs is not None:
            chip._record_metric(step, index, 'drvs', drvs, get_metric_sources('drv'))


######
def get_library_timing_keypaths(chip, lib):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')

    delaymodel = chip.get('asic', 'delaymodel', step=step, index=index)
    keypaths = {}
    for constraint in chip.getkeys('constraint', 'timing'):
        corners = chip.get('constraint', 'timing', constraint, 'libcorner', step=step, index=index)
        for corner in corners:
            if chip.valid('library', lib, 'output', corner, delaymodel):
                keypaths[constraint] = ('library', lib, 'output', corner, delaymodel)

        if constraint not in keypaths:
            keypaths[constraint] = ('library', lib, 'output', corners[0], delaymodel)
    return keypaths


def get_pex_corners(chip):

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')

    corners = set()
    for constraint in chip.getkeys('constraint', 'timing'):
        pexcorner = chip.get('constraint', 'timing', constraint, 'pexcorner',
                             step=step, index=index)
        if pexcorner:
            corners.add(pexcorner)

    return list(corners)


def get_constraint_by_check(chip, check):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')

    for constraint in chip.getkeys('constraint', 'timing'):
        if check in chip.get('constraint', 'timing', constraint, 'check',
                             step=step, index=index):
            return constraint

    # if not specified, just pick the first constraint available
    return chip.getkeys('constraint', 'timing')[0]


def get_power_corner(chip):
    return get_constraint_by_check(chip, "power")


def get_setup_corner(chip):
    return get_constraint_by_check(chip, "setup")


def build_pex_corners(chip):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = chip._get_tool_task(step, index)

    pdkname = chip.get('option', 'pdk')
    stackup = chip.get('option', 'stackup')

    corners = {}
    for constraint in chip.getkeys('constraint', 'timing'):
        pexcorner = chip.get('constraint', 'timing', constraint, 'pexcorner',
                             step=step, index=index)

        if not pexcorner:
            continue
        corners[constraint] = pexcorner

    default_corner = get_setup_corner(chip)
    if default_corner in corners:
        corners[None] = corners[default_corner]

    with open(chip.get('tool', tool, 'task', task, 'file', 'parasitics',
                       step=step, index=index)[0], 'w') as f:
        for constraint, pexcorner in corners.items():
            if chip.valid('pdk', pdkname, 'pexmodel', tool, stackup, pexcorner):
                pex_source_file = chip.find_files('pdk', pdkname,
                                                  'pexmodel',
                                                  tool,
                                                  stackup,
                                                  pexcorner)[0]
                if not pex_source_file:
                    continue

                pex_template = None
                with open(pex_source_file, 'r') as pex_f:
                    pex_template = Template(pex_f.read())

                if not pex_template:
                    continue

                if constraint is None:
                    constraint = "default"
                    corner_specification = ""
                else:
                    corner_specification = f"-corner {constraint}"

                f.write("{0}\n".format(64 * "#"))
                f.write(f"# Constraint \"{constraint}\" -> PEX corner \"{pexcorner}\"\n")
                f.write(f"# Source file: {pex_source_file}\n")
                f.write("{0}\n".format(64 * "#"))

                f.write(pex_template.render({"corner": corner_specification}))

                f.write("\n")
                f.write("{0}\n\n".format(64 * "#"))


def _get_mainlib(chip):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    targetlibs = chip.get('asic', 'logiclib', step=step, index=index)
    return targetlibs[0]


def _set_parameter(chip,
                   param_key,
                   default_value=None,
                   schelp=None,
                   option_key=None,
                   pdk_key=None,
                   lib_key=None,
                   require=None):
    '''
    Set parameter from PDK -> main library -> option -> default_value
    '''
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = chip._get_tool_task(step, index)
    pdkname = chip.get('option', 'pdk')
    stackup = chip.get('option', 'stackup')
    mainlib = _get_mainlib(chip)

    value = default_value
    if not require:
        require = []

    check_keys = []
    if not pdk_key:
        pdk_key = param_key
    check_keys.append(['pdk', pdkname, 'var', tool, stackup, pdk_key])
    if 'pdk' in require:
        chip.add('tool', tool, 'task', task, 'require',
                 ','.join(check_keys[-1]),
                 step=step, index=index)

    if not lib_key:
        lib_key = f'{tool}_{param_key}'
    check_keys.append(['library', mainlib, 'option', 'var', lib_key])
    if 'lib' in require:
        chip.add('tool', tool, 'task', task, 'require',
                 ','.join(check_keys[-1]),
                 step=step, index=index)

    if not option_key:
        option_key = f'{tool}_{param_key}'
    check_keys.append(['option', 'var', option_key])
    if 'option' in require:
        chip.add('tool', tool, 'task', task, 'require',
                 ','.join(check_keys[-1]),
                 step=step, index=index)

    require_key = None
    for key in reversed(check_keys):
        if chip.valid(*key):
            check_step = step
            check_index = index

            if chip.get(*key, field='pernode') == 'never':
                check_step = None
                check_index = None

            check_value = chip.get(*key, step=check_step, index=check_index)
            if check_value:
                value = check_value
                require_key = key
                break

    if value:
        chip.set('tool', tool, 'task', task, 'var', param_key, value,
                 step=step, index=index, clobber=False)

        if require_key:
            chip.add('tool', tool, 'task', task, 'require',
                     ','.join(require_key),
                     step=step, index=index)

    if value or 'key' in require:
        chip.add('tool', tool, 'task', task, 'require',
                 ','.join(['tool', tool, 'task', task, 'var', param_key]),
                 step=step, index=index)

    if schelp:
        chip.set('tool', tool, 'task', task, 'var', param_key,
                 schelp, field='help')


def _define_ifp_params(chip):
    tool, task = chip._get_tool_task(chip.get('arg', 'step'),
                                     chip.get('arg', 'index'))
    _set_parameter(chip, param_key='ifp_tie_separation',
                   default_value='0',
                   schelp='maximum distance between tie high/low cells in microns')
    _set_parameter(chip, param_key='ifp_snap_strategy',
                   default_value='site',
                   schelp='Snapping strategy to use when placing macros. '
                          'Allowed values: none, site, manufacturing_grid')

    # Files
    chip.set('tool', tool, 'task', task, 'file', 'ifp_tapcell',
             'tap cell insertion script',
             field='help')


def _define_ppl_params(chip):
    _set_parameter(chip, param_key='ppl_arguments',
                   default_value='',
                   schelp='additional arguments to pass along to the pin placer.')

    tool, task = chip._get_tool_task(chip.get('arg', 'step'),
                                     chip.get('arg', 'index'))
    chip.set('tool', tool, 'task', task, 'file', 'ppl_constraints',
             'script constrain pin placement',
             field='help')


def _define_pdn_params(chip):
    tool, task = chip._get_tool_task(chip.get('arg', 'step'),
                                     chip.get('arg', 'index'))
    _set_parameter(chip, param_key='pdn_enable',
                   default_value='true',
                   schelp='true/false, when true enables power grid generation')

    # Files
    chip.set('tool', tool, 'task', task, 'file', 'pdn_config',
             'list of files to use for power grid generation',
             field='help')


def _define_pad_params(chip):
    tool, task = chip._get_tool_task(chip.get('arg', 'step'),
                                     chip.get('arg', 'index'))
    chip.set('tool', tool, 'task', task, 'file', 'padring',
             'script to generate a padring using ICeWall in OpenROAD',
             field='help')


def _define_rsz_params(chip):
    _set_parameter(chip, param_key='rsz_setup_slack_margin',
                   default_value='0.0',
                   schelp='specifies the margin to apply when performing setup repair '
                          'in library timing units')
    _set_parameter(chip, param_key='rsz_hold_slack_margin',
                   default_value='0.0',
                   schelp='specifies the margin to apply when performing setup repair '
                          'in library timing units')
    _set_parameter(chip, param_key='rsz_slew_margin',
                   default_value='0.0',
                   schelp='specifies the amount of margin to apply to max slew repairs '
                          'in percent (0 - 100)')
    _set_parameter(chip, param_key='rsz_cap_margin',
                   default_value='0.0',
                   schelp='specifies the amount of margin to apply to max capacitance repairs '
                          'in percent (0 - 100)')
    _set_parameter(chip, param_key='rsz_buffer_inputs',
                   default_value='false',
                   schelp='true/false, when true enables adding buffers to the input ports')
    _set_parameter(chip, param_key='rsz_buffer_outputs',
                   default_value='false',
                   schelp='true/false, when true enables adding buffers to the output ports')

    _set_parameter(chip, param_key='rsz_skip_pin_swap',
                   default_value='true',
                   schelp='true/false, skip pin swap optimization')
    _set_parameter(chip, param_key='rsz_skip_gate_cloning',
                   default_value='true',
                   schelp='true/false, skip gate cloning optimization')
    _set_parameter(chip, param_key='rsz_repair_tns',
                   default_value='100',
                   schelp='percentage of violating nets to attempt to repair (0 - 100)')


def _define_gpl_params(chip):
    _set_parameter(chip, param_key='place_density',
                   require=['key'],
                   schelp='global placement density (0.0 - 1.0)')
    _set_parameter(chip, param_key='pad_global_place',
                   require=['key'],
                   schelp='global placement cell padding in number of sites')

    _set_parameter(chip, param_key='gpl_routability_driven',
                   default_value='true',
                   schelp='true/false, when true global placement will consider the '
                          'routability of the design')
    _set_parameter(chip, param_key='gpl_timing_driven',
                   default_value='true',
                   schelp='true/false, when true global placement will consider the '
                          'timing performance of the design')
    _set_parameter(chip, param_key='gpl_uniform_placement_adjustment',
                   default_value='0.00',
                   schelp='percent of remaining area density to apply above '
                          'uniform density (0.00 - 0.99)')
    _set_parameter(chip, param_key='gpl_enable_skip_io',
                   default_value='true',
                   schelp='true/false, when enabled a global placement is performed without '
                          'considering the impact of the pin placements')


def _define_dpo_params(chip):
    _set_parameter(chip, param_key='dpo_enable',
                   default_value='true',
                   schelp='true/false, when true the detailed placement optimization '
                          'will be performed')
    _set_parameter(chip, param_key='dpo_max_displacement',
                   default_value='0',
                   schelp='maximum cell movement in detailed placement optimization in microns, '
                          '0 will result in the tool default maximum displacement')


def _define_dpl_params(chip):
    _set_parameter(chip, param_key='pad_detail_place',
                   require=['key'],
                   schelp='detailed placement cell padding in number of sites')

    _set_parameter(chip, param_key='dpl_max_displacement',
                   default_value='0',
                   schelp='maximum cell movement in detailed placement in microns, '
                          '0 will result in the tool default maximum displacement')
    _set_parameter(chip, param_key='dpl_disallow_one_site',
                   default_value='false',
                   schelp='true/false, disallow single site gaps in detail placement')


def _define_cts_params(chip):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    mainlib = _get_mainlib(chip)

    _set_parameter(chip, param_key='cts_clock_buffer',
                   default_value=chip.get('library', mainlib, 'asic', 'cells', 'clkbuf',
                                          step=step, index=index)[-1],
                   schelp='buffer to use during clock tree synthesis')
    _set_parameter(chip, param_key='cts_distance_between_buffers',
                   default_value='100',
                   schelp='maximum distance between buffers during clock tree synthesis in microns')
    _set_parameter(chip, param_key='cts_cluster_diameter',
                   default_value='100',
                   schelp='clustering distance to use during clock tree synthesis in microns')
    _set_parameter(chip, param_key='cts_cluster_size',
                   default_value='30',
                   schelp='number of instances in a cluster to use during clock tree synthesis')
    _set_parameter(chip, param_key='cts_balance_levels',
                   default_value='true',
                   schelp='perform level balancing in clock tree synthesis')


def _define_grt_params(chip):
    pdkname = chip.get('option', 'pdk')
    stackup = chip.get('option', 'stackup')

    pdk_min_layer = chip.get('pdk', pdkname, 'minlayer', stackup)
    pdk_max_layer = chip.get('pdk', pdkname, 'maxlayer', stackup)

    _set_parameter(chip, param_key='grt_use_pin_access',
                   default_value='false',
                   schelp='true/false, when true perform pin access before global routing')
    _set_parameter(chip, param_key='grt_overflow_iter',
                   default_value='100',
                   schelp='maximum number of iterations to use in global routing when '
                          'attempting to solve overflow')
    _set_parameter(chip, param_key='grt_macro_extension',
                   default_value='0',
                   schelp='macro extension distance in number of gcells, this can be useful '
                          'when the detailed router needs additional space to avoid DRCs')
    _set_parameter(chip, param_key='grt_allow_congestion',
                   default_value='false',
                   schelp='true/false, when true allow global routing to finish with congestion')
    _set_parameter(chip, param_key='grt_allow_overflow',
                   default_value='false',
                   schelp='true/false, when true allow global routing to finish with overflow')
    _set_parameter(chip, param_key='grt_signal_min_layer',
                   default_value=pdk_min_layer,
                   schelp='minimum layer to use for global routing of signals')
    _set_parameter(chip, param_key='grt_signal_max_layer',
                   default_value=pdk_max_layer,
                   schelp='maximum layer to use for global routing of signals')
    _set_parameter(chip, param_key='grt_clock_min_layer',
                   default_value=pdk_min_layer,
                   schelp='minimum layer to use for global routing of clock nets')
    _set_parameter(chip, param_key='grt_clock_max_layer',
                   default_value=pdk_max_layer,
                   schelp='maximum layer to use for global routing of clock nets')


def _define_ant_params(chip):
    _set_parameter(chip, param_key='ant_iterations',
                   default_value='3',
                   schelp='maximum number of repair iterations to use during antenna repairs')
    _set_parameter(chip, param_key='ant_margin',
                   default_value='0',
                   schelp='adds a margin to the antenna ratios (0 - 100)')
    _set_parameter(chip, param_key='ant_check',
                   default_value='true',
                   schelp='true/false, flag to indicate whether to check for antenna violations')
    _set_parameter(chip, param_key='ant_repair',
                   default_value='true',
                   schelp='true/false, flag to indicate whether to repair antenna violations')


def _define_drt_params(chip):
    _set_parameter(chip, param_key='drt_disable_via_gen',
                   default_value='false',
                   schelp='true/false, when true turns off via generation in detailed router '
                          'and only uses the specified tech vias')
    _set_parameter(chip, param_key='drt_process_node',
                   schelp='when set this specifies to the detailed router the '
                          'specific process node')
    _set_parameter(chip, param_key='drt_via_in_pin_bottom_layer',
                   schelp='TODO')
    _set_parameter(chip, param_key='drt_via_in_pin_top_layer',
                   schelp='TODO')
    _set_parameter(chip, param_key='drt_repair_pdn_vias',
                   schelp='TODO')
    # TODO: This parameter maybe deprecated in favor of drt_repair_pdn_vias
    _set_parameter(chip, param_key='drt_via_repair_post_route',
                   default_value='false',
                   schelp='true/false, when true performs a via ripup step after detailed '
                          'routing to remove power vias that are causing DRC violations')

    _set_parameter(chip, param_key='detailed_route_default_via',
                   schelp='list of default vias to use for detail routing')
    _set_parameter(chip, param_key='detailed_route_unidirectional_layer',
                   schelp='list of layers to treat as unidirectional regardless of '
                          'what the tech lef specifies')


def _define_sta_params(chip):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = chip._get_tool_task(step, index)

    _set_parameter(chip, param_key='sta_early_timing_derate',
                   default_value='0.0',
                   schelp='timing derating factor to use for hold corners')
    _set_parameter(chip, param_key='sta_late_timing_derate',
                   default_value='0.0',
                   schelp='timing derating factor to use for setup corners')
    _set_parameter(chip, param_key='sta_top_n_paths',
                   default_value='10',
                   schelp='number of paths to report timing for')

    chip.set('tool', tool, 'task', task, 'var', 'power_corner', get_power_corner(chip),
             step=step, index=index, clobber=False)
    chip.set('tool', tool, 'task', task, 'var', 'power_corner',
             'corner to use for power analysis',
             field='help')


def _define_sdc_params(chip):
    _set_parameter(chip, param_key='sdc_buffer',
                   schelp='buffer cell to use when auto generating timing constraints')


def _define_psm_params(chip):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = chip._get_tool_task(step, index)

    _set_parameter(chip, param_key='psm_enable',
                   default_value='true',
                   schelp='true/false, when true enables IR drop analysis')

    chip.set('tool', tool, 'task', task, 'var', 'psm_skip_nets',
             'list of nets to skip power grid analysis on',
             field='help')


def _define_fin_params(chip):
    _set_parameter(chip, param_key='fin_add_fill',
                   default_value='true',
                   schelp='true/false, when true enables adding fill, '
                          'if enabled by the PDK, to the design')


def _define_mpl_params(chip):
    _set_parameter(chip, param_key='macro_place_halo',
                   require=['key'],
                   schelp='macro halo to use when performing automated '
                          'macro placement ([x, y] in microns)')
    _set_parameter(chip, param_key='macro_place_channel',
                   require=['key'],
                   schelp='macro channel to use when performing automated '
                          'macro placement ([x, y] in microns)')

    _set_parameter(chip, param_key='rtlmp_enable',
                   default_value='false',
                   schelp='true/false, enables the RTLMP macro placement')
    _set_parameter(chip, param_key='rtlmp_min_instances',
                   schelp='minimum number of instances to use while clustering for macro placement')
    _set_parameter(chip, param_key='rtlmp_max_instances',
                   schelp='maximum number of instances to use while clustering for macro placement')
    _set_parameter(chip, param_key='rtlmp_min_macros',
                   schelp='minimum number of macros to use while clustering for macro placement')
    _set_parameter(chip, param_key='rtlmp_max_macros',
                   schelp='maximum number of macros to use while clustering for macro placement')


def _define_ord_params(chip):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = chip._get_tool_task(step, index)

    # Parameters without pdk/lib dependencies
    chip.set('tool', tool, 'task', task, 'var', 'debug_level',
             'list of "tool key level" to enable debugging of OpenROAD',
             field='help')

    chip.set('tool', tool, 'task', task, 'file', 'global_connect',
             'list of files to use for specifying global connections',
             field='help')

    _set_parameter(chip, param_key='ord_abstract_lef_bloat_factor',
                   default_value='10',
                   require=['key'],
                   schelp='Factor to apply when writing the abstract lef')

    _set_parameter(chip, param_key='ord_abstract_lef_bloat_layers',
                   default_value='true',
                   require=['key'],
                   schelp='true/false, fill all layers when writing the abstract lef')

    _set_parameter(chip, param_key='ord_enable_images',
                   default_value='true',
                   require=['key'],
                   schelp='true/false, enable generating images of the design at the '
                          'end of the task')

    _set_parameter(chip, param_key='ord_heatmap_bins_x',
                   default_value='16',
                   require=['key'],
                   schelp='number of X bins to use for heatmap image generation')
    _set_parameter(chip, param_key='ord_heatmap_bins_y',
                   default_value='16',
                   require=['key'],
                   schelp='number of Y bins to use for heatmap image generation')


def _define_pex_params(chip):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = chip._get_tool_task(step, index)

    chip.set('tool', tool, 'task', task, 'var', 'pex_corners', get_pex_corners(chip),
             step=step, index=index, clobber=False)
    chip.set('tool', tool, 'task', task, 'var', 'pex_corners',
             'list of parasitic extraction corners to use',
             field='help')

    # Auto generated file
    chip.set('tool', tool, 'task', task, 'file', 'parasitics',
             'file used to specify the parasitics for estimation',
             field='help')
    chip.set('tool', tool, 'task', task, 'file', 'parasitics',
             os.path.join(chip._getworkdir(step=step, index=index), 'inputs', 'sc_parasitics.tcl'),
             step=step, index=index, clobber=True)


##################################################
if __name__ == "__main__":

    chip = make_docs()
    chip.write_manifest("openroad.json")
