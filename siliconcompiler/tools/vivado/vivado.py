import json
import os
import re

import siliconcompiler

####################################################################
# Make Docs
####################################################################

def make_docs():
    '''
    Vivado is an FPGA programming tool suite from Xilinx used to
    program Xilinx devices.

    Documentation: https://www.xilinx.com/products/design-tools/vivado.html

    '''

    chip = siliconcompiler.Chip('<design>')
    chip.set('arg','step', 'compile')
    chip.set('arg','index', '<index>')
    setup(chip)
    return chip


################################
# Setup Tool (pre executable)
################################

def setup(chip):

    # default tool settings, note, not additive!
    tool = 'vivado'
    vendor = 'xilinx'
    refdir = 'tools/'+tool
    script = 'compile.tcl'
    step = chip.get('arg','step')
    index = chip.get('arg','index')
    #TODO: fix below
    task = step

    option = "-nolog -nojournal -mode batch -source"

    # General settings
    chip.set('tool', tool, 'exe', tool)
    chip.set('tool', tool, 'vendor', vendor)
    chip.set('tool', tool, 'vswitch', '-version', clobber=False)
    chip.set('tool', tool, 'format', 'tcl', clobber=False)

    chip.set('tool', tool, 'task', task, 'refdir', step, index, refdir, clobber=False)
    chip.set('tool', tool, 'task', task, 'script', step, index, script, clobber=False)
    chip.set('tool', tool, 'task', task, 'threads', step, index, os.cpu_count(), clobber=False)
    chip.set('tool', tool, 'task', task, 'option', step, index, option, clobber=False)

    for metric in ('setupwns', 'setuptns', 'holdwns', 'holdtns'):
        chip.set('tool', tool, 'task', task, 'report', step, index, metric, 'reports/timing_summary.rpt')

    for metric in ('luts', 'registers', 'bram', 'uram'):
        chip.set('tool', tool, 'task', task, 'report', step, index, metric, 'reports/total_utilization.rpt')

    chip.set('tool', tool, 'task', task, 'regex', step, index, 'errors', r'^ERROR:', clobber=False)
    chip.set('tool', tool, 'task', task, 'regex', step, index, 'warnings', r'^(CRITICAL )?WARNING:', clobber=False)

def parse_version(stdout):
    # Vivado v2021.2 (64-bit)
    return stdout.split()[1]

def normalize_version(version):
    return version.lstrip('v')

def _parse_qor_summary(chip, step, index):
    if not os.path.isfile('qor_summary.json'):
        return

    with open('qor_summary.json', 'r') as f:
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
            chip.set('metric', step, index, 'setupwns', setup_wns)
        if setup_tns:
            chip.set('metric', step, index, 'setuptns', setup_tns)
        if hold_wns:
            chip.set('metric', step, index, 'holdwns', hold_wns)
        if hold_tns:
            chip.set('metric', step, index, 'holdtns', hold_tns)

def _parse_utilization(chip, step, index):
    if not os.path.isfile('reports/total_utilization.rpt'):
        return

    with open('reports/total_utilization.rpt', 'r') as f:
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
            chip.set('metric', step, index, 'luts', vals['luts'])
        if 'regs' in vals:
            chip.set('metric', step, index, 'registers', vals['regs'])

        total_bram = 0
        if 'bram' in vals: total_bram += vals['bram']
        if 'uram' in vals: total_bram += vals['uram']
        if 'bram' in vals or 'uram' in vals:
            chip.set('metric', step, index, 'brams', total_bram)

def post_process(chip):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')

    _parse_qor_summary(chip, step, index)
    _parse_utilization(chip, step, index)
