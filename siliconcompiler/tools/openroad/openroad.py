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
    chip.set('tool', tool, 'version', '>=v2.0-7761', clobber=clobber)
    chip.set('tool', tool, 'format', 'tcl', clobber=clobber)

    # exit automatically in batch mode and not breakpoint
    option = ''
    if exit and not chip.get('option', 'breakpoint', step=step, index=index):
        option += " -exit"

    option += " -metrics reports/metrics.json"
    chip.set('tool', tool, 'task', task, 'option', option, step=step, index=index, clobber=clobber)


def setup(chip, mode='batch'):

    # default tool settings, note, not additive!

    tool = 'openroad'
    script = 'sc_apr.tcl'
    refdir = 'tools/' + tool

    design = chip.top()

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    flow = chip.get('option', 'flow')
    task = chip._get_task(step, index)
    pdkname = chip.get('option', 'pdk')
    targetlibs = chip.get('asic', 'logiclib', step=step, index=index)
    mainlib = targetlibs[0]
    macrolibs = chip.get('asic', 'macrolib', step=step, index=index)
    stackup = chip.get('option', 'stackup')
    delaymodel = chip.get('asic', 'delaymodel', step=step, index=index)
    libtype = chip.get('library', mainlib, 'asic', 'libarch', step=step, index=index)

    is_screenshot = mode == 'screenshot' or task == 'screenshot'
    is_show_screenshot = mode == 'show' or task == 'show' or is_screenshot

    if is_show_screenshot:
        mode = 'show'
        clobber = True
    else:
        clobber = False

    # Fixed for tool
    setup_tool(chip, exit=(mode == 'batch' or is_screenshot), clobber=clobber)

    # normalizing thread count based on parallelism and local
    threads = os.cpu_count()
    if not chip.get('option', 'remote') and step in chip.getkeys('flowgraph', flow):
        np = len(chip.getkeys('flowgraph', flow, step))
        threads = int(math.ceil(os.cpu_count() / np))

    # Input/Output requirements for default asicflow steps

    chip.set('tool', tool, 'task', task, 'refdir', refdir, step=step, index=index, clobber=clobber)
    chip.set('tool', tool, 'task', task, 'script', script, step=step, index=index, clobber=clobber)
    chip.set('tool', tool, 'task', task, 'threads', threads, step=step, index=index, clobber=clobber)

    chip.add('tool', tool, 'task', task, 'output', design + '.sdc', step=step, index=index)
    chip.add('tool', tool, 'task', task, 'output', design + '.vg', step=step, index=index)
    chip.add('tool', tool, 'task', task, 'output', design + '.def', step=step, index=index)
    chip.add('tool', tool, 'task', task, 'output', design + '.odb', step=step, index=index)

    if chip.get('option', 'nodisplay'):
        # Tells QT to use the offscreen platform if nodisplay is used
        chip.set('tool', tool, 'task', task, 'env', 'QT_QPA_PLATFORM', 'offscreen', step=step, index=index)

    if delaymodel != 'nldm':
        chip.logger.error(f'{delaymodel} delay model is not supported by {tool}, only nldm')

    if stackup and targetlibs:
        # Note: only one footprint supported in mainlib
        chip.add('tool', tool, 'task', task, 'require', ",".join(['asic', 'logiclib']), step=step, index=index)
        chip.add('tool', tool, 'task', task, 'require', ",".join(['option', 'stackup']), step=step, index=index)
        chip.add('tool', tool, 'task', task, 'require', ",".join(['library', mainlib, 'asic', 'site', libtype]), step=step, index=index)
        chip.add('tool', tool, 'task', task, 'require', ",".join(['pdk', pdkname, 'aprtech', 'openroad', stackup, libtype, 'lef']), step=step, index=index)

        # set tapcell file
        tapfile = None
        if chip.valid('library', mainlib, 'option', 'file', 'openroad_tapcells'):
            tapfile = chip.find_files('library', mainlib, 'option', 'file', 'openroad_tapcells')
        elif chip.valid('pdk', pdkname, 'aprtech', tool, stackup, libtype, 'tapcells'):
            tapfile = chip.find_files('pdk', pdkname, 'aprtech', tool, stackup, libtype, 'tapcells')
        if tapfile:
            chip.set('tool', tool, 'task', task, 'file', 'ifp_tapcell', tapfile, step=step, index=index, clobber=False)
        chip.set('tool', tool, 'task', task, 'file', 'ifp_tapcell', 'tap cell insertion script', field='help')

        corners = get_corners(chip)
        for lib in targetlibs:
            for corner in corners:
                chip.add('tool', tool, 'task', task, 'require', ",".join(['library', lib, 'output', corner, delaymodel]), step=step, index=index)
            chip.add('tool', tool, 'task', task, 'require', ",".join(['library', lib, 'output', stackup, 'lef']), step=step, index=index)
        for lib in macrolibs:
            for corner in corners:
                if chip.valid('library', lib, 'output', corner, delaymodel):
                    chip.add('tool', tool, 'task', task, 'require', ",".join(['library', lib, 'output', corner, delaymodel]), step=step, index=index)
            chip.add('tool', tool, 'task', task, 'require', ",".join(['library', lib, 'output', stackup, 'lef']), step=step, index=index)
    else:
        chip.error('Stackup and logiclib parameters required for OpenROAD.')

    chip.set('tool', tool, 'task', task, 'var', 'timing_corners', sorted(get_corners(chip)), step=step, index=index, clobber=False)
    chip.set('tool', tool, 'task', task, 'var', 'timing_corners', 'list of timing corners to use', field='help')
    chip.set('tool', tool, 'task', task, 'var', 'pex_corners', get_pex_corners(chip), step=step, index=index, clobber=False)
    chip.set('tool', tool, 'task', task, 'var', 'pex_corners', 'list of parasitic extraction corners to use', field='help')
    chip.set('tool', tool, 'task', task, 'var', 'power_corner', get_power_corner(chip), step=step, index=index, clobber=False)
    chip.set('tool', tool, 'task', task, 'var', 'power_corner', 'corner to use for power analysis', field='help')
    chip.set('tool', tool, 'task', task, 'file', 'parasitics', os.path.join(chip._getworkdir(step=step, index=index), 'inputs', 'sc_parasitics.tcl'), step=step, index=index, clobber=True)
    chip.set('tool', tool, 'task', task, 'file', 'parasitics', 'file used to specify the parasitics for estimation', field='help')

    for var0, var1 in [('openroad_tiehigh_cell', 'openroad_tiehigh_port'), ('openroad_tiehigh_cell', 'openroad_tiehigh_port')]:
        key0 = ['library', mainlib, 'option', 'var', tool, var0]
        key1 = ['library', mainlib, 'option', 'var', tool, var1]
        if chip.valid(*key0):
            chip.add('tool', tool, 'task', task, 'require', ",".join(key1), step=step, index=index)
        if chip.valid(*key1):
            chip.add('tool', tool, 'task', task, 'require', ",".join(key0), step=step, index=index)

    chip.add('tool', tool, 'task', task, 'require', ",".join(['pdk', pdkname, 'var', 'openroad', 'rclayer_signal', stackup]), step=step, index=index)
    chip.add('tool', tool, 'task', task, 'require', ",".join(['pdk', pdkname, 'var', 'openroad', 'rclayer_clock', stackup]), step=step, index=index)
    chip.add('tool', tool, 'task', task, 'require', ",".join(['pdk', pdkname, 'var', 'openroad', 'pin_layer_horizontal', stackup]), step=step, index=index)
    chip.add('tool', tool, 'task', task, 'require', ",".join(['pdk', pdkname, 'var', 'openroad', 'pin_layer_vertical', stackup]), step=step, index=index)

    variables = (
        'place_density',
        'pad_global_place',
        'pad_detail_place',
        'macro_place_halo',
        'macro_place_channel'
    )
    for variable in variables:
        # For each OpenROAD tool variable, read default from main library and write it
        # into schema. If PDK doesn't contain a default, the value must be set
        # by the user, so we add the variable keypath as a requirement.
        var_key = ['library', mainlib, 'option', 'var', f'openroad_{variable}']
        if chip.valid(*var_key):
            value = chip.get(*var_key)
            # Clobber needs to be False here, since a user might want to
            # overwrite these.
            chip.set('tool', tool, 'task', task, 'var', variable, value,
                     step=step, index=index, clobber=False)

            keypath = ','.join(var_key)
            chip.add('tool', tool, 'task', task, 'require', keypath, step=step, index=index)

        chip.add('tool', tool, 'task', task, 'require', ",".join(['tool', tool, 'task', task, 'var', variable]), step=step, index=index)
    chip.set('tool', tool, 'task', task, 'var', 'place_density', 'global placement density (0.0 - 1.0)', field='help')
    chip.set('tool', tool, 'task', task, 'var', 'pad_global_place', 'global placement cell padding in number of sites', field='help')
    chip.set('tool', tool, 'task', task, 'var', 'pad_detail_place', 'detailed placement cell padding in number of sites', field='help')
    chip.set('tool', tool, 'task', task, 'var', 'macro_place_halo', 'macro halo to use when performing automated macro placement ([x, y] in microns)', field='help')
    chip.set('tool', tool, 'task', task, 'var', 'macro_place_channel', 'macro channel to use when performing automated macro placement ([x, y] in microns)', field='help')

    # Copy values from PDK if set
    for variable in ('detailed_route_default_via',
                     'detailed_route_unidirectional_layer'):
        if chip.valid('pdk', pdkname, 'var', tool, stackup, variable):
            value = chip.get('pdk', pdkname, 'var', tool, stackup, variable)
            chip.set('tool', tool, 'task', task, 'var', variable, value,
                     step=step, index=index, clobber=False)
    chip.set('tool', tool, 'task', task, 'var', 'detailed_route_default_via', 'list of default vias to use for detail routing', field='help')
    chip.set('tool', tool, 'task', task, 'var', 'detailed_route_unidirectional_layer', 'list of layers to treat as unidirectional regardless of what the tech lef specifies', field='help')

    # set default values for openroad
    for variable, value, helptext in [
        ('ifp_tie_separation', '0', 'maximum distance between tie high/low cells in microns'),
        ('ifp_snap_strategy', 'site', 'Snapping strategy to use when placing macros. Allowed values: none, site, manufacturing_grid'),
        ('pdn_enable', 'true', 'true/false, when true enables power grid generation'),
        ('gpl_routability_driven', 'true', 'true/false, when true global placement will consider the routability of the design'),
        ('gpl_timing_driven', 'true', 'true/false, when true global placement will consider the timing performance of the design'),
        ('dpo_enable', 'true', 'true/false, when true the detailed placement optimization will be performed'),
        ('dpo_max_displacement', '0', 'maximum cell movement in detailed placement optimization in microns, 0 will result in the tool default maximum displacement'),
        ('dpl_max_displacement', '0', 'maximum cell movement in detailed placement in microns, 0 will result in the tool default maximum displacement'),
        ('cts_distance_between_buffers', '100', 'maximum distance between buffers during clock tree synthesis in microns'),
        ('cts_cluster_diameter', '100', 'clusting distance to use during clock tree synthesis in microns'),
        ('cts_cluster_size', '30', 'number of instances in a cluster to use during clock tree synthesis'),
        ('cts_balance_levels', 'true', 'perform level balancing in clock tree synthesis'),
        ('ant_iterations', '3', 'maximum number of repair iterations to use during antenna repairs'),
        ('ant_margin', '0', 'adds a margin to the antenna ratios (0 - 100)'),
        ('grt_use_pin_access', 'false', 'true, false, when true perform pin access before global routing'),
        ('grt_overflow_iter', '100', 'maximum number of iterations to use in flobal routing when attempting to solve overflow'),
        ('grt_macro_extension', '2', 'macro extension distance in number of gcells, this can be useful when the detailed router needs additional space to avoid DRCs'),
        ('grt_allow_congestion', 'false', 'true/false, when true allow global routing to finish with congestion'),
        ('grt_allow_overflow', 'false', 'true/false, when true allow global routing to finish with overflow'),
        ('grt_signal_min_layer', chip.get('pdk', pdkname, 'minlayer', stackup), 'minimum layer to use for global routing of signals'),
        ('grt_signal_max_layer', chip.get('pdk', pdkname, 'maxlayer', stackup), 'maximum layer to use for global routing of signals'),
        ('grt_clock_min_layer', chip.get('pdk', pdkname, 'minlayer', stackup), 'minimum layer to use for global routing of clock nets'),
        ('grt_clock_max_layer', chip.get('pdk', pdkname, 'maxlayer', stackup), 'maximum layer to use for global routing of clock nets'),
        ('drt_disable_via_gen', 'false', 'true/false, when true turns off via generation in detailed router and only uses the specified tech vias'),
        ('drt_process_node', 'false', 'false or value, when set this specifies to the detailed router the specific process node'),
        ('drt_via_in_pin_bottom_layer', 'false', 'false or value, TODO'),
        ('drt_via_in_pin_top_layer', 'false', 'false or value, TODO'),
        ('drt_repair_pdn_vias', 'false', 'false or value, TODO'),
        ('drt_via_repair_post_route', 'false', 'true/false, when true performs a via ripup step after detailed routing to remove power vias that are causing DRC violations'),
        ('rsz_setup_slack_margin', '0.0', 'specifies the margin to apply when performing setup repair in library timing units'),
        ('rsz_hold_slack_margin', '0.0', 'specifies the margin to apply when performing hold repair in library timing units'),
        ('rsz_slew_margin', '0.0', 'specifies the amount of margin to apply to max slew repairs in percent (0 - 100)'),
        ('rsz_cap_margin', '0.0', 'specifies the amount of margin to apply to max capacitance repairs in percent (0 - 100)'),
        ('rsz_buffer_inputs', 'false', 'true/false, when true enables adding buffers to the input ports'),
        ('rsz_buffer_outputs', 'false', 'true/false, when true enables adding buffers to the output ports'),
        ('sta_early_timing_derate', '0.0', 'timing derating factor to use for hold corners'),
        ('sta_late_timing_derate', '0.0', 'timing derating factor to use for setup corners'),
        ('fin_add_fill', 'true', 'true/false, when true enables adding fill, if enabled by the PDK, to the design'),
        ('psm_enable', 'true', 'true/false, when true enables IR drop analysis'),
        ('debug_level', None, 'list of "tool key level" to enable debugging of OpenROAD'),
        ('sdc_buffer', None, 'Buffer cell to use when auto generating timing constraints')
    ]:
        if value:
            chip.set('tool', tool, 'task', task, 'var', variable, value, step=step, index=index, clobber=False)
        if helptext:
            chip.set('tool', tool, 'task', task, 'var', variable, helptext, field='help')

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
                    chip.add('tool', tool, 'task', task, 'file', openroadvar, vfile, step=step, index=index)
    chip.set('tool', tool, 'task', task, 'file', 'pdn_config', 'list of files to use for power grid generation', field='help')
    chip.set('tool', tool, 'task', task, 'file', 'global_connect', 'list of files to use for specifying global connections', field='help')
    chip.set('tool', tool, 'task', task, 'file', 'padring', 'script to generate a padring using ICeWall in OpenROAD', field='help')
    chip.set('tool', tool, 'task', task, 'file', 'ppl_constraints', 'script constrain pin placement', field='help')

    # basic warning and error grep check on logfile
    chip.set('tool', tool, 'task', task, 'regex', 'warnings', r'^\[WARNING|^Warning', step=step, index=index, clobber=False)
    chip.set('tool', tool, 'task', task, 'regex', 'errors', r'^\[ERROR', step=step, index=index, clobber=False)


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


################################
# Post_process (post executable)
################################
def post_process(chip):
    ''' Tool specific function to run after step execution
    '''

    # Check log file for errors and statistics
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')

    # parsing log file
    with open("reports/metrics.json", 'r') as f:
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
                    chip._record_metric(step, index, metric, value, "reports/metrics.json", source_unit=or_unit)

        # setup wns and hold wns can be computed from setup slack and hold slack
        if 'sc__metric__timing__setup__ws' in metrics and has_timing:
            wns = min(0.0, chip.get('metric', 'setupslack', step=step, index=index))
            chip._record_metric(step, index, 'setupwns', wns, "reports/metrics.json", source_unit=or_units['time'])

        if 'sc__metric__timing__hold__ws' in metrics and has_timing:
            wns = min(0.0, chip.get('metric', 'holdslack', step=step, index=index))
            chip._record_metric(step, index, 'holdwns', wns, "reports/metrics.json", source_unit=or_units['time'])

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
            chip._record_metric(step, index, 'drvs', drvs, "reports/metrics.json")


######
def get_pex_corners(chip):

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')

    corners = set()
    for constraint in chip.getkeys('constraint', 'timing'):
        pexcorner = chip.get('constraint', 'timing', constraint, 'pexcorner', step=step, index=index)
        if pexcorner:
            corners.add(pexcorner)

    return list(corners)


def get_corners(chip):

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')

    corners = set()
    for constraint in chip.getkeys('constraint', 'timing'):
        libcorner = chip.get('constraint', 'timing', constraint, 'libcorner', step=step, index=index)
        if libcorner:
            corners.update(libcorner)

    return list(corners)


def get_corner_by_check(chip, check):

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')

    for constraint in chip.getkeys('constraint', 'timing'):
        if check not in chip.get('constraint', 'timing', constraint, 'check', step=step, index=index):
            continue

        libcorner = chip.get('constraint', 'timing', constraint, 'libcorner', step=step, index=index)
        if libcorner:
            return libcorner[0]

    # if not specified, just pick the first corner available
    return get_corners(chip)[0]


def get_power_corner(chip):

    return get_corner_by_check(chip, "power")


def get_setup_corner(chip):

    return get_corner_by_check(chip, "setup")


def build_pex_corners(chip):

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool = 'openroad'

    task = chip._get_task(step, index)

    pdkname = chip.get('option', 'pdk')
    stackup = chip.get('option', 'stackup')

    corners = {}
    for constraint in chip.getkeys('constraint', 'timing'):
        libcorner = chip.get('constraint', 'timing', constraint, 'libcorner', step=step, index=index)
        pexcorner = chip.get('constraint', 'timing', constraint, 'pexcorner', step=step, index=index)

        if not libcorner or not pexcorner:
            continue
        corners[libcorner[0]] = pexcorner

    default_corner = get_setup_corner(chip)
    if default_corner in corners:
        corners[None] = corners[default_corner]

    with open(chip.get('tool', tool, 'task', task, 'file', 'parasitics', step=step, index=index)[0], 'w') as f:
        for libcorner, pexcorner in corners.items():
            if chip.valid('pdk', pdkname, 'pexmodel', tool, stackup, pexcorner):
                pex_source_file = chip.find_files('pdk', pdkname, 'pexmodel', tool, stackup, pexcorner)[0]
                if not pex_source_file:
                    continue

                pex_template = None
                with open(pex_source_file, 'r') as pex_f:
                    pex_template = Template(pex_f.read())

                if not pex_template:
                    continue

                if libcorner is None:
                    libcorner = "default"
                    corner_specification = ""
                else:
                    corner_specification = f"-corner {libcorner}"

                f.write("{0}\n".format(64 * "#"))
                f.write(f"# Library corner \"{libcorner}\" -> PEX corner \"{pexcorner}\"\n")
                f.write(f"# Source file: {pex_source_file}\n")
                f.write("{0}\n".format(64 * "#"))

                f.write(pex_template.render({"corner": corner_specification}))

                f.write("\n")
                f.write("{0}\n\n".format(64 * "#"))


##################################################
if __name__ == "__main__":

    chip = make_docs()
    chip.write_manifest("openroad.json")
