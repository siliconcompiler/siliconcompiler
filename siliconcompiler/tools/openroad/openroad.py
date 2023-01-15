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

    is_screenshot = mode == 'screenshot' or step == 'screenshot'
    is_show_screenshot = mode == 'show' or step == 'show' or is_screenshot
    if is_show_screenshot:
        mode = 'show'
        clobber = True
        option = "-no_init -gui"
    else:
        clobber = False
        option = "-no_init"

    script = 'sc_apr.tcl'

    # exit automatically in batch mode and not bkpt
    if (mode=='batch' or is_screenshot) and (step not in chip.get('option', 'bkpt')):
        option += " -exit"

    option += " -metrics reports/metrics.json"

    chip.set('tool', tool, 'exe', tool)
    chip.set('tool', tool, 'vswitch', '-version')
    chip.set('tool', tool, 'version', '>=v2.0-6445', clobber=clobber)
    chip.set('tool', tool, 'format', 'tcl', clobber=clobber)
    chip.set('tool', tool, 'option',  step, index, option, clobber=clobber)
    chip.set('tool', tool, 'refdir',  step, index, refdir, clobber=clobber)
    chip.set('tool', tool, 'script',  step, index, script, clobber=clobber)

    design = chip.top()

    # normalizing thread count based on parallelism and local
    threads = os.cpu_count()
    if not chip.get('option', 'remote') and step in chip.getkeys('flowgraph', flow):
        np = len(chip.getkeys('flowgraph', flow, step))
        threads = int(math.ceil(os.cpu_count()/np))

    chip.set('tool', tool, 'threads', step, index, threads, clobber=clobber)

    # Input/Output requirements for default asicflow steps
    # TODO: long-term, we want to remove hard-coded step names from tool files.
    if step in ['floorplan', 'physyn', 'place', 'cts', 'route', 'dfm']:
        if step == 'floorplan':
            if (not chip.valid('input', 'netlist', 'verilog') or
                not chip.get('input', 'netlist', 'verilog')):
                chip.add('tool', tool, 'input', step, index, design +'.vg')
        else:
            if (not chip.valid('input', 'layout', 'def') or
                not chip.get('input', 'layout', 'def')):
                chip.add('tool', tool, 'input', step, index, design +'.def')

        chip.add('tool', tool, 'output', step, index, design + '.sdc')
        chip.add('tool', tool, 'output', step, index, design + '.vg')
        chip.add('tool', tool, 'output', step, index, design + '.def')
        chip.add('tool', tool, 'output', step, index, design + '.odb')
        chip.add('tool', tool, 'output', step, index, design + '.lef')
    elif is_show_screenshot:
        if chip.valid('tool', tool, 'var', step, index, 'show_filepath'):
            chip.add('tool', tool, 'require', step, index, ",".join(['tool', tool, 'var', step, index, 'show_filepath']))
        else:
            incoming_ext = find_incoming_ext(chip)
            chip.set('tool', tool, 'var', step, index, 'show_filetype', incoming_ext)
            chip.add('tool', tool, 'input', step, index, f'{design}.{incoming_ext}')
        chip.set('tool', tool, 'var', step, index, 'show_exit', 'true' if is_screenshot else 'false', clobber=False)
        if is_screenshot:
            chip.add('tool', tool, 'output', step, index, design + '.png')
            chip.set('tool', tool, 'var', step, index, 'show_vertical_resolution', '1024', clobber=False)

    if chip.get('option', 'nodisplay'):
        # Tells QT to use the offscreen platform if nodisplay is used
        chip.set('tool', tool, 'env', step, index, 'QT_QPA_PLATFORM', 'offscreen')

    # openroad makes use of these parameters
    targetlibs = chip.get('asic', 'logiclib')
    mainlib = targetlibs[0]
    macrolibs = chip.get('asic', 'macrolib')
    stackup = chip.get('asic', 'stackup')
    delaymodel = chip.get('asic', 'delaymodel')
    if delaymodel != 'nldm':
        chip.logger.error(f'{delaymodel} delay model is not supported by {tool}, only nldm')

    if stackup and targetlibs:
        #Note: only one footprint supported in mainlib
        libtype = chip.get('library', mainlib, 'asic', 'libarch')

        chip.add('tool', tool, 'require', step, index, ",".join(['asic', 'logiclib']))
        chip.add('tool', tool, 'require', step, index, ",".join(['asic', 'stackup',]))
        # chip.add('tool', tool, 'require', step, index, ",".join(['library', mainlib, 'asic', 'footprint', libtype, 'symmetry']))
        # chip.add('tool', tool, 'require', step, index, ",".join(['library', mainlib, 'asic', 'footprint', libtype, 'size']))
        chip.add('tool', tool, 'require', step, index, ",".join(['pdk', pdkname, 'aprtech', 'openroad', stackup, libtype, 'lef']))
        if chip.valid('input', 'layout', 'floorplan.def'):
            chip.add('tool', tool, 'require', step, index, ",".join(['input', 'layout', 'floorplan.def']))

        # set tapcell file
        tapfile = None
        if chip.valid('library', mainlib, 'asic', 'file', tool, 'tapcells'):
            tapfile = chip.find_files('library', mainlib, 'asic', 'file', tool, 'tapcells')
        elif chip.valid('pdk', pdkname, 'aprtech', tool, stackup, libtype, 'tapcells'):
            tapfile = chip.find_files('pdk', pdkname, 'aprtech', tool, stackup, libtype, 'tapcells')
        if tapfile:
            chip.set('tool', tool, 'var', step, index, 'ifp_tapcell', tapfile, clobber=False)

        corners = get_corners(chip)
        for lib in targetlibs:
            for corner in corners:
                chip.add('tool', tool, 'require', step, index, ",".join(['library', lib, 'output', corner, delaymodel]))
            chip.add('tool', tool, 'require', step, index, ",".join(['library', lib, 'output', stackup, 'lef']))
        for lib in macrolibs:
            for corner in corners:
                if chip.valid('library', lib, 'output', corner, delaymodel):
                    chip.add('tool', tool, 'require', step, index, ",".join(['library', lib, 'output', corner, delaymodel]))
            chip.add('tool', tool, 'require', step, index, ",".join(['library', lib, 'output', stackup, 'lef']))
    else:
        chip.error(f'Stackup and logiclib parameters required for OpenROAD.')

    chip.set('tool', tool, 'var', step, index, 'timing_corners', get_corners(chip), clobber=False)
    chip.set('tool', tool, 'var', step, index, 'power_corner', get_power_corner(chip), clobber=False)
    chip.set('tool', tool, 'var', step, index, 'parasitics', "inputs/sc_parasitics.tcl", clobber=True)

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
        if chip.valid('library', mainlib, 'asic', 'var', tool, variable):
            value = chip.get('library', mainlib, 'asic', 'var', tool, variable)
            # Clobber needs to be False here, since a user might want to
            # overwrite these.
            chip.set('tool', tool, 'var', step, index, variable, value,
                     clobber=False)

            keypath = ','.join(['library', mainlib, 'asic', 'var', tool, variable])
            chip.add('tool', tool, 'require', step, index, keypath)

        chip.add('tool', tool, 'require', step, index, ",".join(['tool', tool, 'var', step, index, variable]))

    # Copy values from PDK if set
    for variable in ('detailed_route_default_via',
                     'detailed_route_unidirectional_layer'):
        if chip.valid('pdk', pdkname, 'var', tool, stackup, variable):
            value = chip.get('pdk', pdkname, 'var', tool, stackup, variable)
            chip.set('tool', tool, 'var', step, index, variable, value,
                     clobber=False)

    # set default values for openroad
    for variable, value in [('ifp_tie_separation', '0'),
                            ('pdn_enable', 'True'),
                            ('gpl_routability_driven', 'True'),
                            ('gpl_timing_driven', 'True'),
                            ('dpo_enable', 'True'),
                            ('dpo_max_displacement', '0'),
                            ('dpl_max_displacement', '0'),
                            ('cts_distance_between_buffers', '100'),
                            ('cts_cluster_diameter', '100'),
                            ('cts_cluster_size', '30'),
                            ('cts_balance_levels', 'True'),
                            ('grt_use_pin_access', 'False'),
                            ('grt_overflow_iter', '100'),
                            ('grt_macro_extension', '2'),
                            ('grt_allow_congestion', 'False'),
                            ('grt_allow_overflow', 'False'),
                            ('grt_signal_min_layer', chip.get('asic', 'minlayer')),
                            ('grt_signal_max_layer', chip.get('asic', 'maxlayer')),
                            ('grt_clock_min_layer', chip.get('asic', 'minlayer')),
                            ('grt_clock_max_layer', chip.get('asic', 'maxlayer')),
                            ('drt_disable_via_gen', 'False'),
                            ('drt_process_node', 'False'),
                            ('drt_via_in_pin_bottom_layer', 'False'),
                            ('drt_via_in_pin_top_layer', 'False'),
                            ('drt_repair_pdn_vias', 'False'),
                            ('drt_via_repair_post_route', 'False'),
                            ('rsz_setup_slack_margin', '0.0'),
                            ('rsz_hold_slack_margin', '0.0'),
                            ('rsz_slew_margin', '0.0'),
                            ('rsz_cap_margin', '0.0'),
                            ('rsz_buffer_inputs', 'False'),
                            ('rsz_buffer_outputs', 'False'),
                            ('sta_early_timing_derate', '0.0'),
                            ('sta_late_timing_derate', '0.0'),
                            ('fin_add_fill', 'True'),
                            ('psm_enable', 'True')
                            ]:
        chip.set('tool', tool, 'var', step, index, variable, value, clobber=False)

    for libvar, openroadvar in [('pdngen', 'pdn_config'),
                                ('global_connect', 'global_connect')]:
        if chip.valid('tool', tool, 'var', step, index, openroadvar) and \
           not chip.get('tool', tool, 'var', step, index, openroadvar):
            # value already set
            continue

        # copy from libs
        for lib in targetlibs + macrolibs:
            if chip.valid('library', lib, 'asic', 'file', tool, libvar):
                for pdn_config in chip.find_files('library', lib, 'asic', 'file', tool, libvar):
                    chip.add('tool', tool, 'var', step, index, openroadvar, pdn_config)

    # basic warning and error grep check on logfile
    chip.set('tool', tool, 'regex', step, index, 'warnings', r'^\[WARNING|^Warning', clobber=False)
    chip.set('tool', tool, 'regex', step, index, 'errors', r'^\[ERROR', clobber=False)

    # reports
    for metric in ('vias', 'wirelength', 'cellarea', 'totalarea', 'utilization', 'setuptns', 'holdtns', 
                   'setupslack', 'holdslack', 'setuppaths', 'holdpaths', 'unconstrained', 'peakpower', 
                   'leakagepower', 'pins', 'cells', 'macros', 'nets', 'registers', 'buffers', 'drvs',
                   'setupwns', 'holdwns'):
        chip.set('tool', tool, 'report', step, index, metric, "reports/metrics.json")

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
# Pre_process (pre executable)
################################

def pre_process(chip):

    step = chip.get('arg', 'step')
    if (step == "show" or step == "screenshot"):
        copy_show_files(chip)
    
    # Build estimate PEX
    build_pex_corners(chip)

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
                chip.set('metric', step, index, metric, metrics[openroad_metric], clobber=True)

        # setup wns and hold wns can be computed from setup slack and hold slack
        if 'sc__metric__timing__setup__ws' in metrics:
            wns = min(0.0, float(metrics['sc__metric__timing__setup__ws']))
            chip.set('metric', step, index, 'setupwns', wns, clobber=True)

        if 'sc__metric__timing__hold__ws' in metrics:
            wns = min(0.0, float(metrics['sc__metric__timing__hold__ws']))
            chip.set('metric', step, index, 'holdwns', wns, clobber=True)

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
            chip.set('metric', step, index, 'drvs', str(drvs), clobber=True)

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

    pdkname = chip.get('option', 'pdk')
    stackup = chip.get('asic', 'stackup')

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

    with open(chip.get('tool', tool, 'var', step, index, 'parasitics')[0], 'w') as f:
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

    if chip.valid('tool', tool, 'var', step, index, 'show_filepath'):
        show_file = chip.get('tool', tool, 'var', step, index, 'show_filepath')[0]
        show_type = chip.get('tool', tool, 'var', step, index, 'show_filetype')[0]
        dst_file = "inputs/"+chip.top()+"."+show_type
        shutil.copy2(show_file, dst_file)
        sdc_file = os.path.dirname(show_file)+"/"+chip.top()+".sdc"
        if os.path.exists(sdc_file):
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
