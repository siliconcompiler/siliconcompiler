'''
Vivado is an FPGA programming tool suite from Xilinx used to
program Xilinx devices.

Documentation: https://www.xilinx.com/products/design-tools/vivado.html
'''

import json
import os
import re
from siliconcompiler import sc_open
from siliconcompiler.tools._common import record_metric
from siliconcompiler.targets import fpgaflow_demo


def make_docs(chip):
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
    chip.set('tool', tool, 'task', task, 'threads', os.cpu_count(),
             step=step, index=index, clobber=False)
    chip.set('tool', tool, 'task', task, 'option', option, step=step, index=index, clobber=False)

    chip.set('tool', tool, 'task', task, 'regex', 'errors', r'^ERROR:',
             step=step, index=index, clobber=False)
    chip.set('tool', tool, 'task', task, 'regex', 'warnings', r'^(CRITICAL )?WARNING:',
             step=step, index=index, clobber=False)


def parse_version(stdout):
    # Vivado v2021.2 (64-bit)
    return stdout.split()[1]


def normalize_version(version):
    return version.lstrip('v')


def _parse_qor_summary(chip, step, index):
    if not os.path.isfile('qor_summary.json'):
        return

    with sc_open('qor_summary.json') as f:
        data = json.load(f)

        # Data is organized as list of tasks that Vivado has completed, with
        # metrics associated with each. The tasks appear to be in chronological
        # order, so we pull metrics from the last one.
        task = data['Design QoR Summary'][-1]
        setup_wns = task['Wns(ns)']
        setup_tns = task['Tns(ns)']
        hold_wns = task['Whs(ns)']
        hold_tns = task['Ths(ns)']

        if setup_wns:
            record_metric(chip, step, index, 'setupwns', setup_wns,
                          'qor_summary.json',
                          source_unit='ns')
        if setup_tns:
            record_metric(chip, step, index, 'setuptns', setup_tns,
                          'qor_summary.json',
                          source_unit='ns')
        if hold_wns:
            record_metric(chip, step, index, 'holdwns', hold_wns,
                          'qor_summary.json',
                          source_unit='ns')
        if hold_tns:
            record_metric(chip, step, index, 'holdtns', hold_tns,
                          'qor_summary.json',
                          source_unit='ns')


def _parse_utilization(chip, step, index):
    if not os.path.isfile('reports/total_utilization.rpt'):
        return

    with sc_open('reports/total_utilization.rpt') as f:
        regexes = {
            'luts': (re.compile(r'(?:CLB|Slice) LUTs\*?\s+\|\s+(\d+)'), int),
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

        if 'luts' in vals:
            record_metric(chip, step, index, 'luts', vals['luts'],
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


def post_process(chip):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')

    _parse_qor_summary(chip, step, index)
    _parse_utilization(chip, step, index)
