import math
import os
import shutil
import json
from jinja2 import Template

import siliconcompiler

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
    step = '<step>'
    index = '<index>'
    chip.set('arg', 'step', step)
    chip.set('arg', 'index', index)
    # TODO: how to make it clear in docs that certain settings are
    # target-dependent?
    chip.load_target('freepdk45_demo')
    chip.set('flowgraph', chip.get('option', 'flow'), step, index, 'task', '<task>')
    setup(chip)

    return chip

################################
# Setup Tool (pre executable)
################################

def setup(chip, mode='batch'):

    # default tool settings, note, not additive!

    tool = 'openroad'
    script = 'sc_apr.tcl'
    refdir = 'tools/'+tool

    design = chip.top()

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    flow = chip.get('option', 'flow')
    task = chip._get_task(step, index)
    pdkname = chip.get('option', 'pdk')
    targetlibs = chip.get('asic', 'logiclib')
    mainlib = targetlibs[0]
    macrolibs = chip.get('asic', 'macrolib')
    stackup = chip.get('option', 'stackup')
    delaymodel = chip.get('asic', 'delaymodel')
    libtype = chip.get('library', mainlib, 'asic', 'libarch')

    is_screenshot = mode == 'screenshot' or task == 'screenshot'
    is_show_screenshot = mode == 'show' or task == 'show' or is_screenshot

    if is_show_screenshot:
        mode = 'show'
        clobber = True
    else:
        clobber = False

    # exit automatically in batch mode and not breakpoint
    option = ''
    if (mode=='batch' or is_screenshot) and not chip.get('option', 'breakpoint', step=step, index=index):
        option += " -exit"

    option += " -metrics reports/metrics.json"

    # Fixed for tool
    chip.set('tool', tool, 'exe', tool)
    chip.set('tool', tool, 'vswitch', '-version')
    chip.set('tool', tool, 'version', '>=v2.0-6445', clobber=clobber)
    chip.set('tool', tool, 'format', 'tcl', clobber=clobber)

    # normalizing thread count based on parallelism and local
    threads = os.cpu_count()
    if not chip.get('option', 'remote') and step in chip.getkeys('flowgraph', flow):
        np = len(chip.getkeys('flowgraph', flow, step))
        threads = int(math.ceil(os.cpu_count()/np))

    # Input/Output requirements for default asicflow steps

    chip.set('tool', tool, 'task', task, 'option',  step, index, option, clobber=clobber)
    chip.set('tool', tool, 'task', task, 'refdir',  step, index, refdir, clobber=clobber)
    chip.set('tool', tool, 'task', task, 'script',  step, index, script, clobber=clobber)
    chip.set('tool', tool, 'task', task, 'threads', step, index, threads, clobber=clobber)

    chip.add('tool', tool, 'task', task, 'output', step, index, design + '.sdc')
    chip.add('tool', tool, 'task', task, 'output', step, index, design + '.vg')
    chip.add('tool', tool, 'task', task, 'output', step, index, design + '.def')
    chip.add('tool', tool, 'task', task, 'output', step, index, design + '.odb')
    chip.add('tool', tool, 'task', task, 'output', step, index, design + '.lef')

    if chip.get('option', 'nodisplay'):
        # Tells QT to use the offscreen platform if nodisplay is used
        chip.set('tool', tool, 'task', task, 'env', step, index, 'QT_QPA_PLATFORM', 'offscreen')

    if delaymodel != 'nldm':
        chip.logger.error(f'{delaymodel} delay model is not supported by {tool}, only nldm')

    if stackup and targetlibs:
        #Note: only one footprint supported in mainlib
        chip.add('tool', tool, 'task', task, 'require', step, index, ",".join(['asic', 'logiclib']))
        chip.add('tool', tool, 'task', task, 'require', step, index, ",".join(['option', 'stackup',]))
        chip.add('tool', tool, 'task', task, 'require', step, index, ",".join(['library', mainlib, 'asic', 'site', libtype]))
        chip.add('tool', tool, 'task', task, 'require', step, index, ",".join(['pdk', pdkname, 'aprtech', 'openroad', stackup, libtype, 'lef']))

        # set tapcell file
        tapfile = None
        if chip.valid('library', mainlib, 'option', 'file', 'openroad_tapcells'):
            tapfile = chip.find_files('library', mainlib, 'option', 'file', 'openroad_tapcells')
        elif chip.valid('pdk', pdkname, 'aprtech', tool, stackup, libtype, 'tapcells'):
            tapfile = chip.find_files('pdk', pdkname, 'aprtech', tool, stackup, libtype, 'tapcells')
        if tapfile:
            chip.set('tool', tool, 'task', task, 'var', step, index, 'ifp_tapcell', tapfile, clobber=False)

        corners = get_corners(chip)
        for lib in targetlibs:
            for corner in corners:
                chip.add('tool', tool, 'task', task, 'require', step, index, ",".join(['library', lib, 'output', corner, delaymodel]))
            chip.add('tool', tool, 'task', task, 'require', step, index, ",".join(['library', lib, 'output', stackup, 'lef']))
        for lib in macrolibs:
            for corner in corners:
                if chip.valid('library', lib, 'output', corner, delaymodel):
                    chip.add('tool', tool, 'task', task, 'require', step, index, ",".join(['library', lib, 'output', corner, delaymodel]))
            chip.add('tool', tool, 'task', task, 'require', step, index, ",".join(['library', lib, 'output', stackup, 'lef']))
    else:
        chip.error(f'Stackup and logiclib parameters required for OpenROAD.')

    chip.set('tool', tool, 'task', task, 'var', step, index, 'timing_corners', get_corners(chip), clobber=False)
    chip.set('tool', tool, 'task', task, 'var', step, index, 'power_corner', get_power_corner(chip), clobber=False)
    chip.set('tool', tool, 'task', task, 'var', step, index, 'parasitics', "inputs/sc_parasitics.tcl", clobber=True)

    for var0, var1 in [('openroad_tiehigh_cell', 'openroad_tiehigh_port'), ('openroad_tiehigh_cell', 'openroad_tiehigh_port')]:
        key0 = ['library', mainlib, 'option', 'var', tool, var0]
        key1 = ['library', mainlib, 'option', 'var', tool, var1]
        if chip.valid(*key0):
            chip.add('tool', tool, 'task', task, 'require', step, index, ",".join(key1))
        if chip.valid(*key1):
            chip.add('tool', tool, 'task', task, 'require', step, index, ",".join(key0))

    chip.add('tool', tool, 'task', task, 'require', step, index, ",".join(['pdk', pdkname, 'var', 'openroad', 'rclayer_signal', stackup]))
    chip.add('tool', tool, 'task', task, 'require', step, index, ",".join(['pdk', pdkname, 'var', 'openroad', 'rclayer_clock', stackup]))
    chip.add('tool', tool, 'task', task, 'require', step, index, ",".join(['pdk', pdkname, 'var', 'openroad', 'pin_layer_horizontal', stackup]))
    chip.add('tool', tool, 'task', task, 'require', step, index, ",".join(['pdk', pdkname, 'var', 'openroad', 'pin_layer_vertical', stackup]))

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
            chip.set('tool', tool, 'task', task, 'var', step, index, variable, value,
                     clobber=False)

            keypath = ','.join(var_key)
            chip.add('tool', tool, 'task', task, 'require', step, index, keypath)

        chip.add('tool', tool, 'task', task, 'require', step, index, ",".join(['tool', tool, 'task', task, 'var', step, index, variable]))

    # Copy values from PDK if set
    for variable in ('detailed_route_default_via',
                     'detailed_route_unidirectional_layer'):
        if chip.valid('pdk', pdkname, 'var', tool, stackup, variable):
            value = chip.get('pdk', pdkname, 'var', tool, stackup, variable)
            chip.set('tool', tool, 'task', task, 'var', step, index, variable, value,
                     clobber=False)

    # set default values for openroad
    for variable, value in [('ifp_tie_separation', '0'),
                            ('pdn_enable', 'true'),
                            ('gpl_routability_driven', 'true'),
                            ('gpl_timing_driven', 'true'),
                            ('dpo_enable', 'true'),
                            ('dpo_max_displacement', '0'),
                            ('dpl_max_displacement', '0'),
                            ('cts_distance_between_buffers', '100'),
                            ('cts_cluster_diameter', '100'),
                            ('cts_cluster_size', '30'),
                            ('cts_balance_levels', 'true'),
                            ('ant_iterations', '3'),
                            ('ant_margin', '0'),
                            ('grt_use_pin_access', 'false'),
                            ('grt_overflow_iter', '100'),
                            ('grt_macro_extension', '2'),
                            ('grt_allow_congestion', 'false'),
                            ('grt_allow_overflow', 'false'),
                            ('grt_signal_min_layer', chip.get('pdk', pdkname, 'minlayer', stackup)),
                            ('grt_signal_max_layer', chip.get('pdk', pdkname, 'maxlayer', stackup)),
                            ('grt_clock_min_layer', chip.get('pdk', pdkname, 'minlayer', stackup)),
                            ('grt_clock_max_layer', chip.get('pdk', pdkname, 'maxlayer', stackup)),
                            ('drt_disable_via_gen', 'false'),
                            ('drt_process_node', 'false'),
                            ('drt_via_in_pin_bottom_layer', 'false'),
                            ('drt_via_in_pin_top_layer', 'false'),
                            ('drt_repair_pdn_vias', 'false'),
                            ('drt_via_repair_post_route', 'false'),
                            ('rsz_setup_slack_margin', '0.0'),
                            ('rsz_hold_slack_margin', '0.0'),
                            ('rsz_slew_margin', '0.0'),
                            ('rsz_cap_margin', '0.0'),
                            ('rsz_buffer_inputs', 'false'),
                            ('rsz_buffer_outputs', 'false'),
                            ('sta_early_timing_derate', '0.0'),
                            ('sta_late_timing_derate', '0.0'),
                            ('fin_add_fill', 'true'),
                            ('psm_enable', 'true')
                            ]:
        chip.set('tool', tool, 'task', task, 'var', step, index, variable, value, clobber=False)

    for libvar, openroadvar in [('openroad_pdngen', 'pdn_config'),
                                ('openroad_global_connect', 'global_connect')]:
        if chip.valid('tool', tool, 'task', task, 'var', step, index, openroadvar) and \
           not chip.get('tool', tool, 'task', task, 'var', step, index, openroadvar):
            # value already set
            continue

        # copy from libs
        for lib in targetlibs + macrolibs:
            if chip.valid('library', lib, 'option', 'file', libvar):
                for pdn_config in chip.find_files('library', lib, 'option', 'file', libvar):
                    chip.add('tool', tool, 'task', task, 'var', step, index, openroadvar, pdn_config)

    # basic warning and error grep check on logfile
    chip.set('tool', tool, 'task', task, 'regex', step, index, 'warnings', r'^\[WARNING|^Warning', clobber=False)
    chip.set('tool', tool, 'task', task, 'regex', step, index, 'errors', r'^\[ERROR', clobber=False)

    # reports
    for metric in ('vias', 'wirelength', 'cellarea', 'totalarea', 'utilization', 'setuptns', 'holdtns',
                   'setupslack', 'holdslack', 'setuppaths', 'holdpaths', 'unconstrained', 'peakpower',
                   'leakagepower', 'pins', 'cells', 'macros', 'nets', 'registers', 'buffers', 'drvs',
                   'setupwns', 'holdwns'):
        chip.set('tool', tool, 'task', task, 'report', step, index, metric, "reports/metrics.json")

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

    #Check log file for errors and statistics
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool = 'openroad'

    # parsing log file
    with open("reports/metrics.json", 'r') as f:
        metrics = json.load(f)

        for metric, openroad_metric in [('vias', 'sc__step__route__vias'),
                                        ('wirelength', 'sc__step__route__wirelength'),
                                        ('cellarea', 'sc__metric__design__instance__area'),
                                        ('totalarea', 'sc__metric__design__core__area'),
                                        ('utilization', 'sc__metric__design__instance__utilization'),
                                        ('setuptns', 'sc__metric__timing__setup__tns'),
                                        ('holdtns', 'sc__metric__timing__hold__tns'),
                                        ('setupslack', 'sc__metric__timing__setup__ws'),
                                        ('holdslack', 'sc__metric__timing__hold__ws'),
                                        ('setuppaths', 'sc__metric__timing__drv__setup_violation_count'),
                                        ('holdpaths', 'sc__metric__timing__drv__hold_violation_count'),
                                        ('unconstrained', 'sc__metric__timing__unconstrained'),
                                        ('peakpower', 'sc__metric__power__total'),
                                        ('leakagepower', 'sc__metric__power__leakage__total'),
                                        ('pins', 'sc__metric__design__io'),
                                        ('cells', 'sc__metric__design__instance__count'),
                                        ('macros', 'sc__metric__design__instance__count__macros'),
                                        ('nets', 'sc__metric__design__nets'),
                                        ('registers', 'sc__metric__design__registers'),
                                        ('buffers', 'sc__metric__design__buffers')]:
            if openroad_metric in metrics:
                chip.set('metric', metric, metrics[openroad_metric], clobber=True, step=step, index=index)

        # setup wns and hold wns can be computed from setup slack and hold slack
        if 'sc__metric__timing__setup__ws' in metrics:
            wns = min(0.0, float(metrics['sc__metric__timing__setup__ws']))
            chip.set('metric', 'setupwns', wns, clobber=True, step=step, index=index)

        if 'sc__metric__timing__hold__ws' in metrics:
            wns = min(0.0, float(metrics['sc__metric__timing__hold__ws']))
            chip.set('metric', 'holdwns', wns, clobber=True, step=step, index=index)

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
            chip.set('metric', 'drvs', str(drvs), clobber=True, step=step, index=index)

######

def get_corners(chip):

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool = 'openroad'

    corners = set()
    for constraint in chip.getkeys('constraint', 'timing'):
        if chip.valid('constraint', 'timing', constraint, 'libcorner'):
            corners.add(chip.get('constraint', 'timing', constraint, 'libcorner')[0])

    return list(corners)

def get_corner_by_check(chip, check):

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool = 'openroad'

    for constraint in chip.getkeys('constraint', 'timing'):
        if not chip.valid('constraint', 'timing', constraint, 'libcorner'):
            continue

        if chip.valid('constraint', 'timing', constraint, 'check'):
            if check in chip.get('constraint', 'timing', constraint, 'check'):
                return chip.get('constraint', 'timing', constraint, 'libcorner')[0]

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
        libcorner = None
        if chip.valid('constraint', 'timing', constraint, 'libcorner'):
            libcorner = chip.get('constraint', 'timing', constraint, 'libcorner')[0]

        pexcorner = None
        if chip.valid('constraint', 'timing', constraint, 'pexcorner'):
            pexcorner = chip.get('constraint', 'timing', constraint, 'pexcorner')

        if not libcorner or not pexcorner:
            continue
        corners[libcorner] = pexcorner

    default_corner = get_setup_corner(chip)
    if default_corner in corners:
        corners[None] = corners[default_corner]

    with open(chip.get('tool', tool, 'task', task, 'var', step, index, 'parasitics')[0], 'w') as f:
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

def copy_show_files(chip):

    tool = 'openroad'
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    task = chip._get_task(step, index)

    if chip.valid('tool', tool, 'task', task, 'var', step, index, 'show_filepath'):
        show_file = chip.get('tool', tool, 'task', task, 'var', step, index, 'show_filepath')[0]
        show_type = chip.get('tool', tool, 'task', task, 'var', step, index, 'show_filetype')[0]
        show_job = chip.get('tool', tool, 'task', task, 'var', step, index, 'show_job')[0]
        show_step = chip.get('tool', tool, 'task', task, 'var', step, index, 'show_step')[0]
        show_index = chip.get('tool', tool, 'task', task, 'var', step, index, 'show_index')[0]

        # copy source in to keep sc_apr.tcl simple
        dst_file = "inputs/"+chip.top()+"."+show_type
        shutil.copy2(show_file, dst_file)
        sdc_file = chip.find_result('sdc', show_step, jobname=show_job, index=show_index)
        if sdc_file and os.path.exists(sdc_file):
            shutil.copy2(sdc_file, "inputs/"+chip.top()+".sdc")

def find_incoming_ext(chip):

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    flow = chip.get('option', 'flow')

    supported_ext = ('odb', 'def')

    for input_step, input_index in chip.get('flowgraph', flow, step, index, 'input'):
        for ext in supported_ext:
            show_file = chip.find_result(ext, step=input_step, index=input_index)
            if show_file:
                return ext

    # Nothing found, just add last one
    return supported_ext[-1]

##################################################
if __name__ == "__main__":

    chip = make_docs()
    chip.write_manifest("openroad.json")
