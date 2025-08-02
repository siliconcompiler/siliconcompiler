'''
Vivado is an FPGA programming tool suite from Xilinx used to
program Xilinx devices.

Documentation: https://www.amd.com/en/products/software/adaptive-socs-and-fpgas/vivado.html
'''

import json
import os
import re
from siliconcompiler import utils
from siliconcompiler import sc_open
from siliconcompiler.tools._common import record_metric
from siliconcompiler.tools._common import get_tool_task


def make_docs(chip):
    from siliconcompiler.targets import fpgaflow_demo
    chip.set('fpga', 'partname', 'ice40up5k-sg48')
    chip.use(fpgaflow_demo)


tool = 'vivado'


def setup(chip):
    vendor = 'xilinx'

    chip.set('tool', tool, 'exe', tool)
    chip.set('tool', tool, 'vendor', vendor)
    chip.set('tool', tool, 'vswitch', '-version')
    chip.set('tool', tool, 'format', 'tcl')

    # report_design_analysis -json flag requires Vivado 2021 or greater
    chip.set('tool', tool, 'version', '>=2021', clobber=False)


def setup_task(chip, task):
    setup(chip)

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')

    script = 'sc_run.tcl'

    refdir = f'tools/{tool}/scripts'
    option = ['-nolog', '-nojournal', '-mode', 'batch', '-source']

    chip.set('tool', tool, 'task', task, 'refdir', refdir, step=step, index=index,
             package='siliconcompiler', clobber=False)
    chip.set('tool', tool, 'task', task, 'script', script, step=step, index=index, clobber=False)
    chip.set('tool', tool, 'task', task, 'threads', utils.get_cores(chip),
             step=step, index=index, clobber=False)
    chip.set('tool', tool, 'task', task, 'option', option, step=step, index=index, clobber=False)

    chip.set('tool', tool, 'task', task, 'regex', 'errors', r'^ERROR:',
             step=step, index=index, clobber=False)
    chip.set('tool', tool, 'task', task, 'regex', 'warnings', r'^(CRITICAL )?WARNING:',
             step=step, index=index, clobber=False)

    chip.set('tool', tool, 'task', task, 'var', 'metric_luts', 'true',
             step=step, index=index, clobber=False)


def parse_version(stdout):
    # Vivado v2021.2 (64-bit)
    return stdout.split()[1]


def normalize_version(version):
    return version.lstrip('v')


def _parse_qor_summary(chip, step, index):
    if not os.path.isfile('reports/qor_summary.json'):
        return

    with sc_open('reports/qor_summary.json') as f:
        data = json.load(f)

        # Data is organized as list of tasks that Vivado has completed, with
        # metrics associated with each. The tasks appear to be in chronological
        # order, so we pull metrics from the last one.
        task = data['Design QoR Summary'][-1]
        setup_wns = None
        for metric in ('Wns(ns)', 'WNS(ns)'):
            if metric in task:
                setup_wns = task[metric]
                break
        setup_tns = None
        for metric in ('Tns(ns)', 'TNS(ns)'):
            if metric in task:
                setup_tns = task[metric]
                break
        hold_wns = None
        for metric in ('Whs(ns)', 'WHS(ns)'):
            if metric in task:
                hold_wns = task[metric]
                break
        hold_tns = None
        for metric in ('Ths(ns)', 'THS(ns)'):
            if metric in task:
                hold_tns = task[metric]
                break

        if setup_wns:
            record_metric(chip, step, index, 'setupwns', setup_wns,
                          'reports/qor_summary.json',
                          source_unit='ns')
        if setup_tns:
            record_metric(chip, step, index, 'setuptns', setup_tns,
                          'reports/qor_summary.json',
                          source_unit='ns')
        if hold_wns:
            record_metric(chip, step, index, 'holdwns', hold_wns,
                          'reports/qor_summary.json',
                          source_unit='ns')
        if hold_tns:
            record_metric(chip, step, index, 'holdtns', hold_tns,
                          'reports/qor_summary.json',
                          source_unit='ns')


def _parse_utilization(chip, step, index):
    if not os.path.isfile('reports/total_utilization.rpt'):
        return

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)

    with sc_open('reports/total_utilization.rpt') as f:
        regexes = {
            'luts': (re.compile(r'(?:CLB|Slice) LUTs\*?\s+\|\s+(\d+)'), int),
            'lut6': (re.compile(r'LUT6\*?\s+\|\s+(\d+)'), int),
            'lut5': (re.compile(r'LUT5\*?\s+\|\s+(\d+)'), int),
            'lut4': (re.compile(r'LUT4\*?\s+\|\s+(\d+)'), int),
            'lut3': (re.compile(r'LUT3\*?\s+\|\s+(\d+)'), int),
            'lut2': (re.compile(r'LUT2\*?\s+\|\s+(\d+)'), int),
            'lut1': (re.compile(r'LUT1\*?\s+\|\s+(\d+)'), int),
            'f7mux': (re.compile(r'MUXF7\*?\s+\|\s+(\d+)'), int),
            'f8mux': (re.compile(r'MUXF8\*?\s+\|\s+(\d+)'), int),
            'dsps': (re.compile(r'DSPs\*?\s+\|\s+(\d+)'), int),
            'regs': (re.compile(r'(?:CLB|Slice) Registers\s+\|\s+(\d+)'), int),
            'bram': (re.compile(r'Block RAM Tile\s+\|\s+(\d+(.\d+)?)'), float),
            # TODO: should URAM be float?
            'uram': (re.compile(r'URAM\s+\|\s+(\d+(.\d+)?)'), float)
        }
        vals = {}

        for line in f:
            for metric, (regex, datatype) in regexes.items():
                if metric in vals:
                    continue
                match = regex.search(line)
                if match:
                    vals[metric] = datatype(match.group(1))
                    continue

        lut_cnt = 0
        if chip.get('tool', tool, 'task', task, 'var', 'metric_luts', step=step, index=index)[0] \
                == 'true':
            lut_cnt = vals.get('luts', 0)
        else:
            lut_cnt = sum([cnt for name, cnt in vals.items() if name.startswith('lut')])
            lut_cnt -= vals.get('luts', 0)  # avoid double counting
            if "f7mux" in vals:
                lut_cnt += vals["f7mux"]
            if "f8mux" in vals:
                lut_cnt -= vals["f8mux"]

        if lut_cnt != 0:
            record_metric(chip, step, index, 'luts', lut_cnt,
                          'reports/total_utilization.rpt')
        if 'regs' in vals:
            record_metric(chip, step, index, 'registers', vals['regs'],
                          'reports/total_utilization.rpt')

        total_bram = 0
        if 'bram' in vals:
            total_bram += vals['bram']
        if 'uram' in vals:
            total_bram += vals['uram']
        if 'bram' in vals or 'uram' in vals:
            record_metric(chip, step, index, 'brams', total_bram,
                          'reports/total_utilization.rpt')

        if 'dsps' in vals:
            record_metric(chip, step, index, 'dsps', vals['dsps'],
                          'reports/total_utilization.rpt')


def post_process(chip):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')

    _parse_qor_summary(chip, step, index)
    _parse_utilization(chip, step, index)
