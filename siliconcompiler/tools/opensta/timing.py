import os
import re
from siliconcompiler import utils
from siliconcompiler import sc_open, SiliconCompilerError
from siliconcompiler.tools.opensta import setup as tool_setup
from siliconcompiler.tools.opensta import runtime_options as tool_runtime_options
from siliconcompiler.tools._common import input_provides, add_common_file, \
    get_tool_task, record_metric
from siliconcompiler.tools._common.asic import set_tool_task_var, get_timing_modes


def setup(chip):
    '''
    Generate a static timing reports.
    '''

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)

    tool_setup(chip)

    chip.set('tool', tool, 'task', task, 'script', 'sc_timing.tcl',
             step=step, index=index, clobber=False)

    chip.set('tool', tool, 'task', task, 'threads', utils.get_cores(chip),
             step=step, index=index)

    design = chip.top()
    if f'{design}.vg' in input_provides(chip, step, index):
        chip.set('tool', tool, 'task', task, 'input', f'{design}.vg',
                 step=step, index=index)
    else:
        chip.set('tool', tool, 'task', task, 'require', 'input,netlist,verilog',
                 step=step, index=index)

    if f'{design}.sdc' in input_provides(chip, step, index):
        chip.set('tool', tool, 'task', task, 'input', f'{design}.sdc',
                 step=step, index=index)
    elif chip.valid('input', 'constraint', 'sdc') and \
            chip.get('input', 'constraint', 'sdc', step=step, index=index):
        chip.add('tool', tool, 'task', task, 'require', 'input,constraint,sdc',
                 step=step, index=index)

    set_tool_task_var(chip, param_key='top_n_paths',
                      default_value='10',
                      schelp='number of paths to report timing for')
    set_tool_task_var(chip, param_key='unique_path_groups_per_clock',
                      default_value=False,
                      skip=['pdk', 'lib'],
                      schelp='true/false, if true will generate separate path groups per clock')

    modes = get_timing_modes(chip)

    set_tool_task_var(chip, param_key='timing_mode',
                      default_value=modes[0],
                      schelp='timing mode to use')

    timing_mode = chip.get('tool', tool, 'task', task, 'var', 'timing_mode',
                           step=step, index=index)[0]
    if timing_mode not in modes:
        raise SiliconCompilerError(
            f'{timing_mode} mode is not present in timing constraints', chip=chip)

    for scenario in chip.getkeys('constraint', 'timing'):
        if chip.get('constraint', 'timing', scenario, 'mode',
                    step=step, index=index) != timing_mode:
            continue
        if chip.get('constraint', 'timing', scenario, 'file', step=step, index=index):
            chip.add('tool', tool, 'task', task, 'require', f'constraint,timing,{scenario},file',
                     step=step, index=index)

    # Add the SPEF or SDF files as inputs if provided.
    spef_files = [f for f in input_provides(chip, step, index) if f.endswith(".spef")]
    sdf_files = [f for f in input_provides(chip, step, index) if f.endswith(".sdf")]
    if spef_files and sdf_files:
        # If both SPEF and SDF files are provided, only use the SPEF files.
        chip.add('tool', tool, 'task', task, 'input', spef_files, step=step, index=index)
    elif spef_files:
        chip.add('tool', tool, 'task', task, 'input', spef_files, step=step, index=index)
    elif sdf_files:
        chip.add('tool', tool, 'task', task, 'input', sdf_files, step=step, index=index)

    add_common_file(chip, 'opensta_generic_sdc', 'sdc/sc_constraints.sdc')


def __report_map(chip, metric, basefile):
    corners = chip.getkeys('constraint', 'timing')
    mapping = {
        "power": [f"reports/power.{corner}.rpt" for corner in corners],
        "unconstrained": ["reports/unconstrained.rpt", "reports/unconstrained.topN.rpt"],
        "setuppaths": ["reports/setup.rpt", "reports/setup.topN.rpt"],
        "holdpaths": ["reports/hold.rpt", "reports/hold.topN.rpt"],
        "holdslack": ["reports/hold.rpt", "reports/hold.topN.rpt"],
        "setupslack": ["reports/setup.rpt", "reports/setup.topN.rpt"],
        "setuptns": ["reports/setup.rpt", "reports/setup.topN.rpt"],
        "holdtns": ["reports/hold.rpt", "reports/hold.topN.rpt"],
        "setupskew": ["reports/skew.setup.rpt", "reports/setup.rpt", "reports/setup.topN.rpt"],
        "holdskew": ["reports/skew.hold.rpt", "reports/hold.rpt", "reports/hold.topN.rpt"]
    }

    if metric in mapping:
        paths = [basefile]
        for path in mapping[metric]:
            if os.path.exists(path):
                paths.append(path)
        return paths
    return [basefile]


################################
# Post_process (post executable)
################################
def post_process(chip):
    '''
    Tool specific function to run after step execution
    '''

    # Check log file for errors and statistics
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    logfile = f"{step}.log"

    peakpower = []
    leakagepower = []
    skews = {}
    # parsing log file
    with sc_open(logfile) as f:
        timescale = "s"
        metric = None
        for line in f:
            metricmatch = re.search(r'^SC_METRIC:\s+(\w+)', line)
            value = re.search(r'(\d*\.?\d)*', line)
            fmax = re.search(r'fmax = (\d*\.?\d*)', line)
            tns = re.search(r'^tns (.*)', line)
            slack = re.search(r'^worst slack (.*)', line)
            skew = re.search(r'^\s*(.*)\s+(.*) skew', line)
            power = re.search(r'^Total(.*)', line)
            if metricmatch:
                metric = metricmatch.group(1)
                continue

            if metric:
                if metric == 'timeunit':
                    timescale = f'{line.strip()}s'
                    metric = None
                if metric == 'fmax':
                    if fmax:
                        record_metric(chip, step, index, 'fmax', float(fmax.group(1)),
                                      __report_map(chip, 'fmax', logfile),
                                      source_unit='MHz')
                        metric = None
                elif metric == 'power':
                    if power:
                        powerlist = power.group(1).split()
                        leakage = powerlist[2]
                        total = powerlist[3]

                        peakpower.append(float(total))
                        leakagepower.append(float(leakage))

                        metric = None
                elif metric == 'cellarea':
                    record_metric(chip, step, index, 'cellarea', float(value.group(0)),
                                  __report_map(chip, 'cellarea', logfile),
                                  source_unit='um^2')
                    metric = None
                elif metric in ('logicdepth',
                                'cells',
                                'nets',
                                'buffers',
                                'inverters',
                                'registers',
                                'unconstrained',
                                'pins',
                                'setuppaths',
                                'holdpaths'):
                    record_metric(chip, step, index, metric, int(value.group(0)),
                                  __report_map(chip, metric, logfile))
                    metric = None
                elif metric in ('holdslack', 'setupslack'):
                    if slack:
                        record_metric(chip, step, index, metric, float(slack.group(1).split()[-1]),
                                      __report_map(chip, metric, logfile),
                                      source_unit=timescale)
                        metric = None
                elif metric in ('setuptns', 'holdtns'):
                    if tns:
                        record_metric(chip, step, index, metric, float(tns.group(1).split()[-1]),
                                      __report_map(chip, metric, logfile),
                                      source_unit=timescale)
                        metric = None
                elif metric in ('setupskew', 'holdskew'):
                    if skew:
                        skews.setdefault(skew.group(2), []).append(float(skew.group(1)))
                else:
                    metric = None

    if peakpower:
        record_metric(chip, step, index, 'peakpower', max(peakpower),
                      __report_map(chip, 'peakpower', logfile),
                      source_unit='W')
    if leakagepower:
        record_metric(chip, step, index, 'leakagepower', max(leakagepower),
                      __report_map(chip, 'leakagepower', logfile),
                      source_unit='W')
    if skews:
        for skewtype, values in skews.items():
            skew = f'{skewtype}skew'
            record_metric(chip, step, index, skew, max(values),
                          __report_map(chip, skew, logfile),
                          source_unit=timescale)

    drv_report = "reports/drv_violators.rpt"
    if os.path.exists(drv_report):
        drv_count = 0
        with sc_open(drv_report) as f:
            for line in f:
                if re.search(r'\(VIOLATED\)$', line):
                    drv_count += 1

        record_metric(chip, step, index, 'drvs', drv_count,
                      [drv_report, logfile])


################################
# Runtime options
################################
def runtime_options(chip):
    return tool_runtime_options(chip)
