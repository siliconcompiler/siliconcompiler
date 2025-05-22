import os
import json
from siliconcompiler import sc_open
from siliconcompiler import utils
from siliconcompiler.tools._common import input_provides, add_common_file, \
    get_tool_task, record_metric
from siliconcompiler.tools._common.asic import get_mainlib, set_tool_task_var, get_libraries, \
    CellArea, set_tool_task_lib_var
from siliconcompiler.tools.openroad import setup as tool_setup


def setup(chip, exit=True):
    tool_setup(chip, exit=exit)

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)

    chip.set('tool', tool, 'task', task, 'threads', utils.get_cores(chip),
             step=step, index=index)

    pdkname = chip.get('option', 'pdk')
    targetlibs = get_libraries(chip, 'logic')
    mainlib = get_mainlib(chip)
    macrolibs = get_libraries(chip, 'macro')
    stackup = chip.get('option', 'stackup')
    delaymodel = chip.get('asic', 'delaymodel', step=step, index=index)
    libtype = chip.get('library', mainlib, 'asic', 'libarch', step=step, index=index)

    if delaymodel != 'nldm':
        chip.error(f'{delaymodel} delay model is not supported by {tool}, only nldm')

    if not stackup or not targetlibs:
        chip.error('Stackup and logiclib parameters required for OpenROAD.')

    # Setup general required
    chip.add('tool', tool, 'task', task, 'require', 'asic,logiclib',
             step=step, index=index)
    if chip.get('asic', 'macrolib', step=step, index=index):
        chip.add('tool', tool, 'task', task, 'require', 'asic,macrolib',
                 step=step, index=index)
    if chip.get('option', 'library', step=step, index=index):
        chip.add('tool', tool, 'task', task, 'require', 'option,library',
                 step=step, index=index)
    chip.add('tool', tool, 'task', task, 'require', 'asic,delaymodel',
             step=step, index=index)
    chip.add('tool', tool, 'task', task, 'require', 'option,stackup',
             step=step, index=index)
    chip.add('tool', tool, 'task', task, 'require', f'library,{mainlib},asic,libarch',
             step=step, index=index)
    chip.add('tool', tool, 'task', task, 'require', f'library,{mainlib},asic,site,{libtype}',
             step=step, index=index)
    chip.add('tool', tool, 'task', task, 'require',
             f'pdk,{pdkname},aprtech,openroad,{stackup},{libtype},lef',
             step=step, index=index)

    # Add library requirements
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


def extract_metrics(chip):
    '''
    Extract metrics
    '''

    # Check log file for errors and statistics
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')

    metric_reports = {
        "setuptns": [
            "timing/total_negative_slack.rpt",
            "timing/setup.rpt",
            "timing/setup.histogram.rpt",
            "images/timing/setup.histogram.png"
        ],
        "setupslack": [
            "timing/worst_slack.setup.rpt",
            "timing/setup.rpt",
            "timing/setup.topN.rpt",
            "timing/setup.histogram.rpt",
            "images/timing/setup.histogram.png"
        ],
        "setupskew": [
            "timing/skew.setup.rpt",
            "timing/worst_slack.setup.rpt",
            "timing/setup.rpt",
            "timing/setup.topN.rpt"
        ],
        "setuppaths": [
            "timing/setup.rpt",
            "timing/setup.topN.rpt",
            "timing/setup.histogram.rpt",
            "images/timing/setup.histogram.png"
        ],
        "holdslack": [
            "timing/worst_slack.hold.rpt",
            "timing/hold.rpt",
            "timing/hold.topN.rpt",
            "timing/hold.histogram.rpt",
            "images/timing/hold.histogram.png"
        ],
        "holdskew": [
            "timing/skew.hold.rpt",
            "timing/worst_slack.hold.rpt",
            "timing/hold.rpt",
            "timing/hold.topN.rpt"
        ],
        "holdpaths": [
            "timing/hold.rpt",
            "timing/hold.topN.rpt",
            "timing/hold.histogram.rpt",
            "images/timing/hold.histogram.png"
        ],
        "unconstrained": [
            "timing/unconstrained.rpt",
            "timing/unconstrained.topN.rpt"
        ],
        "peakpower": [
            *[f"power/{corner}.rpt" for corner in chip.getkeys('constraint', 'timing')],
            *[f"images/heatmap/power_density/{corner}.png"
              for corner in chip.getkeys('constraint', 'timing')]
        ],
        "drvs": [
            "timing/drv_violators.rpt",
            "floating_nets.rpt",
            "overdriven_nets.rpt",
            "overdriven_nets_with_parallel.rpt",
            f"{chip.design}_antenna.rpt",
            f"{chip.design}_antenna_post_repair.rpt"
        ],
        "drcs": [
            f"{chip.design}_drc.rpt",
            f"markers/{chip.design}.drc.rpt",
            f"markers/{chip.design}.drc.json",
            f"images/markers/{chip.design}.DRC.png"
        ],
        "utilization": [
            "images/heatmap/placement_density.png"
        ],
        "wirelength": [
            f"images/{chip.design}.routing.png"
        ]
    }
    metric_reports["leakagepower"] = metric_reports["peakpower"]

    metrics_file = "reports/metrics.json"

    if not os.path.exists(metrics_file):
        chip.logger.warning("OpenROAD metrics file is missing")
        return

    def get_metric_sources(metric):
        metric_sources = [metrics_file]
        if metric in metric_reports:
            for metric_file in metric_reports[metric]:
                metric_path = f'reports/{metric_file}'
                if os.path.exists(metric_path):
                    metric_sources.append(metric_path)
        return metric_sources

    # parsing log file
    with sc_open(metrics_file) as f:
        try:
            metrics = json.load(f)
        except json.decoder.JSONDecodeError as e:
            chip.logger.error(f'Unable to parse metrics from OpenROAD: {e}')
            metrics = {}

        _generate_cell_area_report(chip.top(), metrics)

        or_units = {}
        for unit, or_unit in [
                ('time', 'run__flow__platform__time_units'),
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
            ('vias', 'sc__step__global_route__vias', True, None),
            ('vias', 'sc__step__route__vias', True, None),
            ('wirelength', 'sc__step__global_route__wirelength', True, 'distance'),
            ('wirelength', 'sc__step__route__wirelength', True, 'distance'),
            ('cellarea', 'sc__metric__design__instance__area', True, 'area'),
            ('stdcellarea', 'sc__metric__design__instance__area__stdcell', True, 'area'),
            ('macroarea', 'sc__metric__design__instance__area__macros', True, 'area'),
            ('padcellarea', 'sc__metric__design__instance__area__padcells', True, 'area'),
            ('totalarea', 'sc__metric__design__die__area', True, 'area'),
            ('utilization', 'sc__metric__design__instance__utilization', True, 100.0),
            ('setuptns', 'sc__metric__timing__setup__tns', has_timing, 'time'),
            ('holdtns', 'sc__metric__timing__hold__tns', has_timing, 'time'),
            ('setupslack', 'sc__metric__timing__setup__ws', has_timing, 'time'),
            ('holdslack', 'sc__metric__timing__hold__ws', has_timing, 'time'),
            ('setupskew', 'sc__metric__clock__skew__setup', has_timing, 'time'),
            ('holdskew', 'sc__metric__clock__skew__hold', has_timing, 'time'),
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
            ('inverters', 'sc__metric__design__inverters', True, None),
            ('buffers', 'sc__metric__design__buffers', True, None),
            ('logicdepth', 'sc__metric__design__logic__depth', True, None)
        ]:
            if or_metric in metrics:
                value = metrics[or_metric]

                # Check for INF timing
                if or_unit == 'time' and abs(value) > 1e24:
                    or_use = False

                if or_unit:
                    if or_unit in or_units:
                        or_unit = or_units[or_unit]
                    else:
                        value *= or_unit
                        or_unit = None

                if or_use:
                    record_metric(chip, step, index, metric, value,
                                  get_metric_sources(metric),
                                  source_unit=or_unit)

        ir_drop = None
        for or_metric, value in metrics.items():
            if or_metric.startswith("sc__step__design_powergrid__drop__worst__net") or \
               or_metric.startswith("sc__image__design_powergrid__drop__worst__net"):
                if not ir_drop:
                    ir_drop = value
                else:
                    ir_drop = max(value, ir_drop)

        if ir_drop is not None:
            record_metric(chip, step, index, 'irdrop', ir_drop,
                          get_metric_sources('irdrop'),
                          source_unit='V')

        # setup wns and hold wns can be computed from setup slack and hold slack
        if 'sc__metric__timing__setup__ws' in metrics and \
           has_timing and \
           chip.get('metric', 'setupslack', step=step, index=index) is not None:
            wns = min(0.0, chip.get('metric', 'setupslack', step=step, index=index))
            wns_units = chip.get('metric', 'setupslack', field='unit')
            record_metric(chip, step, index, 'setupwns', wns,
                          get_metric_sources('setupslack'),
                          source_unit=wns_units)

        if 'sc__metric__timing__hold__ws' in metrics and \
           has_timing and \
           chip.get('metric', 'holdslack', step=step, index=index) is not None:
            wns = min(0.0, chip.get('metric', 'holdslack', step=step, index=index))
            wns_units = chip.get('metric', 'holdslack', field='unit')
            record_metric(chip, step, index, 'holdwns', wns,
                          get_metric_sources('holdslack'),
                          source_unit=wns_units)

        drvs = None
        for metric in [
                'sc__metric__timing__drv__max_slew',
                'sc__metric__timing__drv__max_cap',
                'sc__metric__timing__drv__max_fanout',
                'sc__metric__timing__drv__max_fanout',
                'sc__metric__timing__drv__floating__nets',
                'sc__metric__timing__drv__floating__pins',
                'sc__metric__timing__drv__overdriven__nets',
                'sc__metric__antenna__violating__nets',
                'sc__metric__antenna__violating__pins']:
            if metric in metrics:
                if drvs is None:
                    drvs = int(metrics[metric])
                else:
                    drvs += int(metrics[metric])

        if drvs is not None:
            record_metric(chip, step, index, 'drvs', drvs, get_metric_sources('drvs'))

        if 'sc__step__route__drc_errors' in metrics:
            drcs = int(metrics['sc__step__route__drc_errors'])
            record_metric(chip, step, index, 'drcs', drcs, get_metric_sources('drcs'))


def _generate_cell_area_report(design, ord_metrics):
    cellarea_report = CellArea()

    prefix = "sc__cellarea__design__instance"

    filtered_data = {}
    for key, value in ord_metrics.items():
        if key.startswith(prefix):
            filtered_data[key[len(prefix)+2:]] = value

    modules = set()
    modules.add("")
    for key in filtered_data.keys():
        if "__in_module:" in key:
            module = key[key.find("__in_module:"):]
            modules.add(module)

    def process_cell(group):
        data = {}
        for key, value in filtered_data.items():
            if (group != "" and key.endswith(group)):
                key = key[:key.find("__in_module:")]
                data[key] = value
            elif (group == "" and "__in_module" not in key):
                data[key] = value

        cell_type = None
        cell_name = None

        if not group:
            cell_type = design
            cell_name = design
        else:
            cell_type = group[len("__in_module:"):]

        cellarea = None
        cellcount = None

        macroarea = None
        macrocount = None

        stdcell_types = (
            'tie_cell',
            'standard_cell',
            'buffer',
            'clock_buffer',
            'timing_repair_buffer',
            'inverter',
            'clock_inverter',
            'timing_Repair_inverter',
            'clock_gate_cell',
            'level_shifter_cell',
            'sequential_cell',
            'multi_input_combinational_cell',
            'other'
            )

        stdcell_info_area = []
        stdcell_info_count = []
        stdcellarea = None
        stdcellcount = None

        for key, value in data.items():
            if key == 'name':
                cell_name = value
            elif key == 'count':
                cellcount = value
            elif key == 'area':
                cellarea = value
            elif key.startswith('count__class'):
                _, cell_class = key.split(':')
                if cell_class == 'macro':
                    macrocount = value
                elif cell_class in stdcell_types:
                    stdcell_info_count.append(value)
            elif key.startswith('area__class'):
                _, cell_class = key.split(':')
                if cell_class == 'macro':
                    macroarea = value
                elif cell_class in stdcell_types:
                    stdcell_info_area.append(value)

        if stdcell_info_count:
            stdcellcount = sum(stdcell_info_count)
        if stdcell_info_area:
            stdcellarea = sum(stdcell_info_area)

        cellarea_report.add_cell(
            name=cell_name,
            module=cell_type,
            cellarea=cellarea,
            cellcount=cellcount,
            macroarea=macroarea,
            macrocount=macrocount,
            stdcellarea=stdcellarea,
            stdcellcount=stdcellcount)

        if filtered_data:
            return True
        return False

    for module in modules:
        process_cell(module)

    if cellarea_report.size() > 0:
        cellarea_report.write_report("reports/hierarchical_cell_area.json")


def define_tapcell_params(chip):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)

    # Files
    chip.set('tool', tool, 'task', task, 'file', 'ifp_tapcell',
             'tap cell insertion script',
             field='help')


def define_tapcell_files(chip):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)

    pdkname = chip.get('option', 'pdk')
    mainlib = get_mainlib(chip)
    stackup = chip.get('option', 'stackup')
    libtype = chip.get('library', mainlib, 'asic', 'libarch',
                       step=step, index=index)

    # set tapcell file
    tapfile = None
    if chip.valid('library', mainlib, 'option', 'file', 'openroad_tapcells'):
        tapfile = chip.find_files('library', mainlib, 'option', 'file', 'openroad_tapcells')
    elif chip.valid('pdk', pdkname, 'aprtech', tool, stackup, libtype, 'tapcells'):
        tapfile = chip.find_files('pdk', pdkname, 'aprtech', tool, stackup, libtype, 'tapcells')
    if tapfile:
        chip.set('tool', tool, 'task', task, 'file', 'ifp_tapcell', tapfile,
                 step=step, index=index, clobber=False)


def define_tiecell_params(chip):
    set_tool_task_var(chip, param_key='ifp_tie_separation',
                      default_value='0',
                      schelp='maximum distance between tie high/low cells in microns')

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)

    mainlib = get_mainlib(chip)

    # Set required keys
    for var0, var1 in [('openroad_tielow_cell', 'openroad_tielow_port'),
                       ('openroad_tiehigh_cell', 'openroad_tiehigh_port')]:
        key0 = ['library', mainlib, 'option', 'var', tool, var0]
        key1 = ['library', mainlib, 'option', 'var', tool, var1]
        if chip.valid(*key0):
            chip.add('tool', tool, 'task', task, 'require', ",".join(key1),
                     step=step, index=index)
        if chip.valid(*key1):
            chip.add('tool', tool, 'task', task, 'require', ",".join(key0),
                     step=step, index=index)


def define_ppl_params(chip):
    set_tool_task_var(chip, param_key='ppl_arguments',
                      default_value=[],
                      schelp='additional arguments to pass along to the pin placer.')

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)

    chip.set('tool', tool, 'task', task, 'file', 'ppl_constraints',
             'pin placement constraints script',
             field='help')

    pdkname = chip.get('option', 'pdk')
    stackup = chip.get('option', 'stackup')

    for key in (['pdk', pdkname, 'var', 'openroad', 'pin_layer_horizontal', stackup],
                ['pdk', pdkname, 'var', 'openroad', 'pin_layer_vertical', stackup]):
        chip.add('tool', tool, 'task', task, 'require', ",".join(key),
                 step=step, index=index)
    if chip.get('tool', tool, 'task', task, 'file', 'ppl_constraints', step=step, index=index):
        chip.add('tool', tool, 'task', task, 'require',
                 ",".join(['tool', tool, 'task', task, 'file', 'ppl_constraints']),
                 step=step, index=index)


def define_pdn_params(chip):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)

    set_tool_task_var(chip, param_key='pdn_enable',
                      default_value='true',
                      schelp='true/false, when true enables power grid generation')

    # Files
    chip.set('tool', tool, 'task', task, 'file', 'pdn_config',
             'list of files to use for power grid generation',
             field='help')


def define_pdn_files(chip):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)

    targetlibs = get_libraries(chip, 'logic')
    macrolibs = get_libraries(chip, 'macro')

    for libvar, openroadvar in [('openroad_pdngen', 'pdn_config')]:
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


def define_pad_params(chip):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)

    chip.set('tool', tool, 'task', task, 'file', 'padring',
             'script to generate a padring using ICeWall in OpenROAD',
             field='help')

    if chip.get('tool', tool, 'task', task, 'file', 'padring', step=step, index=index):
        chip.add('tool', tool, 'task', task, 'require',
                 ",".join(['tool', tool, 'task', task, 'file', 'padring']),
                 step=step, index=index)


def define_rsz_params(chip):
    set_tool_task_var(chip, param_key='rsz_skip_drv_repair',
                      default_value=False,
                      schelp='skip design rule violation repair')
    set_tool_task_var(chip, param_key='rsz_skip_setup_repair',
                      default_value=False,
                      schelp='skip setup timing repair')
    set_tool_task_var(chip, param_key='rsz_setup_slack_margin',
                      default_value='0.0',
                      schelp='specifies the margin to apply when performing setup repair '
                             'in library timing units')
    set_tool_task_var(chip, param_key='rsz_skip_hold_repair',
                      default_value=False,
                      schelp='skip hold timing repair')
    set_tool_task_var(chip, param_key='rsz_hold_slack_margin',
                      default_value='0.0',
                      schelp='specifies the margin to apply when performing setup repair '
                             'in library timing units')
    set_tool_task_var(chip, param_key='rsz_slew_margin',
                      default_value='0.0',
                      schelp='specifies the amount of margin to apply to max slew repairs '
                             'in percent (0 - 100)')
    set_tool_task_var(chip, param_key='rsz_cap_margin',
                      default_value='0.0',
                      schelp='specifies the amount of margin to apply to max capacitance repairs '
                             'in percent (0 - 100)')
    set_tool_task_var(chip, param_key='rsz_buffer_inputs',
                      default_value='false',
                      schelp='true/false, when true enables adding buffers to the input ports')
    set_tool_task_var(chip, param_key='rsz_buffer_outputs',
                      default_value='false',
                      schelp='true/false, when true enables adding buffers to the output ports')

    set_tool_task_var(chip, param_key='rsz_skip_pin_swap',
                      default_value='true',
                      schelp='true/false, skip pin swap optimization')
    set_tool_task_var(chip, param_key='rsz_skip_gate_cloning',
                      default_value='true',
                      schelp='true/false, skip gate cloning optimization')
    set_tool_task_var(chip, param_key='rsz_repair_tns',
                      default_value='100',
                      schelp='percentage of violating nets to attempt to repair (0 - 100)')

    set_tool_task_var(chip, param_key='rsz_skip_recover_power',
                      default_value=False,
                      schelp='skip power recovery')
    set_tool_task_var(chip, param_key='rsz_recover_power',
                      default_value=100,
                      schelp='percentage of paths to attempt to recover power (0 - 100)')

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)

    pdkname = chip.get('option', 'pdk')
    stackup = chip.get('option', 'stackup')

    # Set required keys
    for key in (['pdk', pdkname, 'var', 'openroad', 'rclayer_signal', stackup],
                ['pdk', pdkname, 'var', 'openroad', 'rclayer_clock', stackup]):
        chip.add('tool', tool, 'task', task, 'require', ",".join(key),
                 step=step, index=index)


def define_gpl_params(chip):
    set_tool_task_var(chip, param_key='place_density',
                      require=['key'],
                      schelp='global placement density (0.0 - 1.0)')
    set_tool_task_var(chip, param_key='pad_global_place',
                      require=['key'],
                      schelp='global placement cell padding in number of sites')

    set_tool_task_var(chip, param_key='gpl_routability_driven',
                      default_value='true',
                      schelp='true/false, when true global placement will consider the '
                             'routability of the design')
    set_tool_task_var(chip, param_key='gpl_timing_driven',
                      default_value='true',
                      schelp='true/false, when true global placement will consider the '
                             'timing performance of the design')
    set_tool_task_var(chip, param_key='gpl_uniform_placement_adjustment',
                      default_value='0.00',
                      schelp='percent of remaining area density to apply above '
                             'uniform density (0.00 - 0.99)')
    set_tool_task_var(chip, param_key='gpl_enable_skip_io',
                      default_value='true',
                      schelp='true/false, when enabled a global placement is performed without '
                             'considering the impact of the pin placements')


def define_dpo_params(chip):
    set_tool_task_var(chip, param_key='dpo_enable',
                      default_value='true',
                      schelp='true/false, when true the detailed placement optimization '
                             'will be performed')
    set_tool_task_var(chip, param_key='dpo_max_displacement',
                      default_value='0',
                      schelp='maximum cell movement in detailed placement optimization in microns, '
                             '0 will result in the tool default maximum displacement')


def define_dpl_params(chip):
    set_tool_task_var(chip, param_key='pad_detail_place',
                      require=['key'],
                      schelp='detailed placement cell padding in number of sites')

    set_tool_task_var(chip, param_key='dpl_max_displacement',
                      default_value='0',
                      schelp='maximum cell movement in detailed placement in microns, '
                             '0 will result in the tool default maximum displacement')
    set_tool_task_var(chip, param_key='dpl_disallow_one_site',
                      default_value='false',
                      schelp='true/false, disallow single site gaps in detail placement')

    set_tool_task_var(chip, param_key='dpl_use_decap_fillers',
                      default_value='true',
                      schelp='true/false, use decap fillers along with non-decap fillers')


def define_cts_params(chip):
    set_tool_task_var(chip, param_key='cts_distance_between_buffers',
                      default_value='100',
                      schelp='maximum distance between buffers during clock tree synthesis '
                             'in microns')
    set_tool_task_var(chip, param_key='cts_cluster_diameter',
                      default_value='100',
                      schelp='clustering distance to use during clock tree synthesis in microns')
    set_tool_task_var(chip, param_key='cts_cluster_size',
                      default_value='30',
                      schelp='number of instances in a cluster to use during clock tree synthesis')
    set_tool_task_var(chip, param_key='cts_balance_levels',
                      default_value='true',
                      schelp='perform level balancing in clock tree synthesis')
    set_tool_task_var(chip, param_key='cts_obstruction_aware',
                      default_value='true',
                      schelp='make clock tree synthesis aware of obstructions')


def define_grt_params(chip, load_all=False):
    pdkname = chip.get('option', 'pdk')
    stackup = chip.get('option', 'stackup')

    pdk_min_layer = chip.get('pdk', pdkname, 'minlayer', stackup)
    pdk_max_layer = chip.get('pdk', pdkname, 'maxlayer', stackup)

    set_tool_task_var(chip, param_key='grt_setup',
                      default_value='true',
                      schelp='true/false, when true global route is setup')
    set_tool_task_var(chip, param_key='grt_signal_min_layer',
                      default_value=pdk_min_layer,
                      schelp='minimum layer to use for global routing of signals')
    set_tool_task_var(chip, param_key='grt_signal_max_layer',
                      default_value=pdk_max_layer,
                      schelp='maximum layer to use for global routing of signals')
    set_tool_task_var(chip, param_key='grt_clock_min_layer',
                      default_value=pdk_min_layer,
                      schelp='minimum layer to use for global routing of clock nets')
    set_tool_task_var(chip, param_key='grt_clock_max_layer',
                      default_value=pdk_max_layer,
                      schelp='maximum layer to use for global routing of clock nets')
    set_tool_task_var(chip, param_key='grt_macro_extension',
                      default_value='0',
                      schelp='macro extension distance in number of gcells, this can be useful '
                             'when the detailed router needs additional space to avoid DRCs')

    if load_all:
        set_tool_task_var(chip, param_key='grt_use_pin_access',
                          default_value='false',
                          schelp='true/false, when true perform pin access before global routing')
        set_tool_task_var(chip, param_key='grt_overflow_iter',
                          default_value='100',
                          schelp='maximum number of iterations to use in global routing when '
                                 'attempting to solve overflow')
        set_tool_task_var(chip, param_key='grt_allow_congestion',
                          default_value='false',
                          schelp='true/false, when true allow global routing to finish '
                                 'with congestion')
        set_tool_task_var(chip, param_key='grt_allow_overflow',
                          default_value='false',
                          schelp='true/false, when true allow global routing to finish '
                                 'with overflow')


def define_ant_params(chip):
    set_tool_task_var(chip, param_key='ant_iterations',
                      default_value='3',
                      schelp='maximum number of repair iterations to use during antenna repairs')
    set_tool_task_var(chip, param_key='ant_margin',
                      default_value='0',
                      schelp='adds a margin to the antenna ratios (0 - 100)')
    set_tool_task_var(chip, param_key='ant_check',
                      default_value='true',
                      schelp='true/false, flag to indicate whether to check for antenna violations')
    set_tool_task_var(chip, param_key='ant_repair',
                      default_value='true',
                      schelp='true/false, flag to indicate whether to repair antenna violations')


def define_drt_params(chip):
    set_tool_task_var(chip, param_key='drt_disable_via_gen',
                      default_value='false',
                      schelp='true/false, when true turns off via generation in detailed router '
                             'and only uses the specified tech vias')
    set_tool_task_var(chip, param_key='drt_process_node',
                      schelp='when set this specifies to the detailed router the '
                             'specific process node')
    set_tool_task_var(chip, param_key='drt_via_in_pin_bottom_layer',
                      schelp='TODO')
    set_tool_task_var(chip, param_key='drt_via_in_pin_top_layer',
                      schelp='TODO')
    set_tool_task_var(chip, param_key='drt_repair_pdn_vias',
                      schelp='TODO')
    # TODO: This parameter maybe deprecated in favor of drt_repair_pdn_vias
    set_tool_task_var(chip, param_key='drt_via_repair_post_route',
                      default_value='false',
                      schelp='true/false, when true performs a via ripup step after detailed '
                             'routing to remove power vias that are causing DRC violations')

    set_tool_task_var(chip, param_key='detailed_route_default_via',
                      schelp='list of default vias to use for detail routing')
    set_tool_task_var(chip, param_key='detailed_route_unidirectional_layer',
                      schelp='list of layers to treat as unidirectional regardless of '
                             'what the tech lef specifies')

    set_tool_task_var(chip, param_key='drt_report_interval',
                      default_value=5,
                      schelp='reporting interval in steps for generating a DRC report.')


def define_sta_params(chip):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)

    set_tool_task_var(chip, param_key='sta_early_timing_derate',
                      default_value='0.0',
                      schelp='timing derating factor to use for hold corners')
    set_tool_task_var(chip, param_key='sta_late_timing_derate',
                      default_value='0.0',
                      schelp='timing derating factor to use for setup corners')
    set_tool_task_var(chip, param_key='sta_top_n_paths',
                      default_value='10',
                      schelp='number of paths to report timing for')
    set_tool_task_var(chip, param_key='sta_define_path_groups',
                      default_value=True,
                      skip=['pdk', 'lib'],
                      schelp='true/false, if true will generate path groups for timing reporting')
    set_tool_task_var(chip, param_key='sta_unique_path_groups_per_clock',
                      default_value=False,
                      skip=['pdk', 'lib'],
                      schelp='true/false, if true will generate separate path groups per clock')

    chip.set('tool', tool, 'task', task, 'var', 'power_corner', get_power_corner(chip),
             step=step, index=index, clobber=False)
    chip.add('tool', tool, 'task', task, 'require',
             ','.join(['tool', tool, 'task', task, 'var', 'power_corner']),
             step=step, index=index)
    chip.set('tool', tool, 'task', task, 'var', 'power_corner',
             'corner to use for power analysis',
             field='help')

    add_common_file(chip, 'opensta_generic_sdc', 'sdc/sc_constraints.sdc')


def define_sdc_params(chip):
    set_tool_task_var(chip, param_key='sdc_buffer',
                      schelp='buffer cell to use when auto generating timing constraints')


def define_psm_params(chip):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)

    set_tool_task_var(chip, param_key='psm_enable',
                      default_value='true',
                      schelp='true/false, when true enables IR drop analysis')

    chip.set('tool', tool, 'task', task, 'var', 'psm_skip_nets',
             'list of nets to skip power grid analysis on',
             field='help')

    chip.set('tool', tool, 'task', task, 'var', 'psm_allow_missing_terminal_nets',
             'list of nets where a missing terminal is acceptable',
             field='help')


def define_fin_params(chip):
    set_tool_task_var(chip, param_key='fin_add_fill',
                      default_value='true',
                      schelp='true/false, when true enables adding fill, '
                             'if enabled by the PDK, to the design')


def define_mpl_params(chip):
    set_tool_task_var(chip, param_key='macro_place_halo',
                      require=['key'],
                      schelp='macro halo to use when performing automated '
                             'macro placement ([x, y] in microns)')
    set_tool_task_var(chip, param_key='macro_place_channel',
                      require=['key'],
                      schelp='macro channel to use when performing automated '
                             'macro placement ([x, y] in microns)')

    set_tool_task_var(chip, param_key='rtlmp_min_instances',
                      schelp='minimum number of instances to use while clustering for '
                             'macro placement')
    set_tool_task_var(chip, param_key='rtlmp_max_instances',
                      schelp='maximum number of instances to use while clustering for '
                             'macro placement')
    set_tool_task_var(chip, param_key='rtlmp_min_macros',
                      schelp='minimum number of macros to use while clustering for macro placement')
    set_tool_task_var(chip, param_key='rtlmp_max_macros',
                      schelp='maximum number of macros to use while clustering for macro placement')
    set_tool_task_var(chip, param_key='rtlmp_max_levels',
                      schelp='maximum depth of physical hierarchical tree')
    set_tool_task_var(chip, param_key='rtlmp_min_aspect_ratio',
                      schelp='Specifies the minimum aspect ratio of its width to height of a '
                             'standard cell cluster')
    set_tool_task_var(chip, param_key='rtlmp_fence',
                      schelp='Defines the global fence bounding box coordinates '
                             '(llx, lly, urx, ury)')
    set_tool_task_var(chip, param_key='rtlmp_bus_planning',
                      schelp='Flag to enable bus planning')
    set_tool_task_var(chip, param_key='rtlmp_target_dead_space',
                      schelp='Specifies the target dead space percentage, which influences '
                             'the utilization of standard cell clusters')

    set_tool_task_var(chip, param_key='rtlmp_area_weight',
                      schelp='Weight for the area of current floorplan')
    set_tool_task_var(chip, param_key='rtlmp_outline_weight',
                      schelp='Weight for violating the fixed outline constraint, meaning that all '
                             'clusters should be placed within the shape of their parent cluster')
    set_tool_task_var(chip, param_key='rtlmp_wirelength_weight',
                      schelp='Weight for half-perimeter wirelength')
    set_tool_task_var(chip, param_key='rtlmp_guidance_weight',
                      schelp='Weight for guidance cost or clusters being placed near specified '
                             'regions if users provide such constraints')
    set_tool_task_var(chip, param_key='rtlmp_fence_weight',
                      schelp='Weight for fence cost, or how far the macro is from zero '
                             'fence violation')
    set_tool_task_var(chip, param_key='rtlmp_boundary_weight',
                      schelp='Weight for the boundary, or how far the hard macro clusters are from '
                             'boundaries. Note that mixed macro clusters are not pushed, thus not '
                             'considered in this cost.')
    set_tool_task_var(chip, param_key='rtlmp_blockage_weight',
                      schelp='Weight for the boundary, or how far the hard macro clusters are '
                             'from boundaries')
    set_tool_task_var(chip, param_key='rtlmp_notch_weight',
                      schelp='Weight for the notch, or the existence of dead space that cannot be '
                             'used for placement & routing')
    set_tool_task_var(chip, param_key='rtlmp_macro_blockage_weight',
                      schelp='Weight for macro blockage, or the overlapping instances of the macro')


def define_ord_params(chip):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)

    chip.set('tool', tool, 'task', task, 'file', 'global_connect',
             'list of files to use for specifying global connections',
             field='help')

    set_tool_task_var(chip, param_key='ord_abstract_lef_bloat_factor',
                      default_value='10',
                      require=['key'],
                      schelp='Factor to apply when writing the abstract lef')

    set_tool_task_var(chip, param_key='ord_abstract_lef_bloat_layers',
                      default_value='true',
                      require=['key'],
                      schelp='true/false, fill all layers when writing the abstract lef')

    set_tool_task_var(chip, param_key='ord_enable_images',
                      default_value='true',
                      require=['key'],
                      schelp='true/false, enable generating images of the design at the '
                             'end of the task')

    set_tool_task_var(chip, param_key='ord_heatmap_bins_x',
                      default_value='16',
                      require=['key'],
                      schelp='number of X bins to use for heatmap image generation')
    set_tool_task_var(chip, param_key='ord_heatmap_bins_y',
                      default_value='16',
                      require=['key'],
                      schelp='number of Y bins to use for heatmap image generation')

    set_tool_task_lib_var(chip, param_key='scan_chain_cells',
                          default_value=None,
                          schelp='cells to use for scan chain insertion')

    set_tool_task_lib_var(chip, param_key='multibit_ff_cells',
                          default_value=None,
                          schelp='multibit flipflop cells')


def define_ord_files(chip):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)
    targetlibs = get_libraries(chip, 'logic')
    macrolibs = get_libraries(chip, 'macro')

    for libvar, openroadvar in [('openroad_global_connect', 'global_connect')]:
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


def define_pex_params(chip):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)

    chip.set('tool', tool, 'task', task, 'var', 'pex_corners', get_pex_corners(chip),
             step=step, index=index, clobber=False)
    chip.set('tool', tool, 'task', task, 'var', 'pex_corners',
             'list of parasitic extraction corners to use',
             field='help')

    # Auto generated file
    chip.set('tool', tool, 'task', task, 'file', 'parasitics',
             'file used to specify the parasitics for estimation',
             field='help')


def set_reports(chip, reports):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)

    # supported reports
    supported = (
        "setup",
        "hold",
        "unconstrained",
        "clock_skew",
        "drv_violations",
        "fmax",
        "power",
        "check_setup",
        "placement_density",
        "routing_congestion",
        "power_density",
        "ir_drop",
        "clock_placement",
        "clock_trees",
        "optimization_placement",
        "module_view"
    )

    chip.set('tool', tool, 'task', task, 'var', 'reports',
             'list of reports and images to generate',
             field='help')

    chip.set('tool', tool, 'task', task, 'var', 'reports', [],
             step=step, index=index)

    def check_enabled(type):
        for key in (('tool', tool, 'task', task, 'var', f'skip_{type}'),
                    ('option', 'var', f'openroad_skip_{type}')):
            if chip.valid(*key):
                if chip.get(*key, field='pernode').is_never():
                    if chip.get(*key) == ["true"]:
                        return False
                    elif chip.get(*key, step=step, index=index) == ["true"]:
                        return False
        return True

    for report in reports:
        if report not in supported:
            raise ValueError(f'{report} is not supported')
        if check_enabled(report):
            chip.add('tool', tool, 'task', task, 'var', 'reports', report,
                     step=step, index=index)


def set_pnr_inputs(chip):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)

    design = chip.top()

    # clear
    chip.set('tool', tool, 'task', task, 'input', [], step=step, index=index)
    if f'{design}.sdc' in input_provides(chip, step, index):
        chip.add('tool', tool, 'task', task, 'input', design + '.sdc',
                 step=step, index=index)
    elif chip.valid('input', 'constraint', 'sdc') and \
            chip.get('input', 'constraint', 'sdc', step=step, index=index):
        chip.add('tool', tool, 'task', task, 'require', 'input,constraint,sdc',
                 step=step, index=index)

    if f'{design}.odb' in input_provides(chip, step, index):
        chip.add('tool', tool, 'task', task, 'input', design + '.odb',
                 step=step, index=index)
    elif f'{design}.def' in input_provides(chip, step, index):
        chip.add('tool', tool, 'task', task, 'input', design + '.def',
                 step=step, index=index)
    elif chip.valid('input', 'layout', 'def') and \
            chip.get('input', 'layout', 'def', step=step, index=index):
        chip.add('tool', tool, 'task', task, 'require', 'input,layout,def',
                 step=step, index=index)


def set_pnr_outputs(chip):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)

    design = chip.top()

    # clear
    chip.set('tool', tool, 'task', task, 'output', [], step=step, index=index)

    chip.add('tool', tool, 'task', task, 'output', design + '.sdc', step=step, index=index)
    chip.add('tool', tool, 'task', task, 'output', design + '.vg', step=step, index=index)
    chip.add('tool', tool, 'task', task, 'output', design + '.def', step=step, index=index)
    chip.add('tool', tool, 'task', task, 'output', design + '.odb', step=step, index=index)


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


def _get_constraint_by_check(chip, check):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')

    for constraint in chip.getkeys('constraint', 'timing'):
        if check in chip.get('constraint', 'timing', constraint, 'check',
                             step=step, index=index):
            return constraint

    # if not specified, just pick the first constraint available
    return chip.getkeys('constraint', 'timing')[0]


def get_power_corner(chip):
    return _get_constraint_by_check(chip, "power")


def get_setup_corner(chip):
    return _get_constraint_by_check(chip, "setup")


def build_pex_corners(chip):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)

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

    chip.set('tool', tool, 'task', task, 'file', 'parasitics',
             os.path.join(chip.getworkdir(step=step, index=index),
                          'inputs',
                          'sc_parasitics.tcl'),
             step=step, index=index, clobber=True)
    chip.set('tool', tool, 'task', task, 'file', 'parasitics', False, field='copy')

    with open(chip.get('tool', tool, 'task', task, 'file', 'parasitics',
                       step=step, index=index)[0], 'w') as f:
        for constraint, pexcorner in corners.items():
            if chip.valid('pdk', pdkname, 'pexmodel', tool, stackup, pexcorner):
                pex_source_file = chip.find_files(
                    'pdk',
                    pdkname,
                    'pexmodel',
                    tool,
                    stackup,
                    pexcorner)[0]
                if not pex_source_file:
                    continue

                corner_pex_template = utils.get_file_template(pex_source_file)
                pex_template = utils.get_file_template(
                    'pex.tcl',
                    root=os.path.join(os.path.dirname(__file__),
                                      'templates'))

                if not pex_template:
                    continue

                if constraint is None:
                    constraint = "default"
                    corner_specification = ""
                else:
                    corner_specification = f"-corner {constraint}"

                f.write(pex_template.render(
                    constraint=constraint,
                    pexcorner=pexcorner,
                    source=pex_source_file,
                    pex=corner_pex_template.render({"corner": corner_specification})
                ))
                f.write('\n')
