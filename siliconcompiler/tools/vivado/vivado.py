'''
Vivado is an FPGA programming tool suite from Xilinx used to
program Xilinx devices.

Documentation: https://www.xilinx.com/products/design-tools/vivado.html
'''

import json
import os
import re

import siliconcompiler

####################################################################
# Make Docs
####################################################################
def make_docs(chip):
    chip.set('fpga', 'partname', 'ice40up5k-sg48')
    chip.load_target("fpgaflow_demo")

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

    chip.set('tool', tool, 'task', task, 'refdir', refdir, step=step, index=index, clobber=False)
    chip.set('tool', tool, 'task', task, 'script', script, step=step, index=index, clobber=False)
    chip.set('tool', tool, 'task', task, 'threads', os.cpu_count(), step=step, index=index, clobber=False)
    chip.set('tool', tool, 'task', task, 'option', option, step=step, index=index, clobber=False)

    for metric in ('setupwns', 'setuptns', 'holdwns', 'holdtns'):
        chip.set('tool', tool, 'task', task, 'report', metric, 'reports/timing_summary.rpt', step=step, index=index)

    for metric in ('luts', 'registers', 'bram', 'uram'):
        chip.set('tool', tool, 'task', task, 'report', metric, 'reports/total_utilization.rpt', step=step, index=index)

    chip.set('tool', tool, 'task', task, 'regex', 'errors', r'^ERROR:', step=step, index=index, clobber=False)
    chip.set('tool', tool, 'task', task, 'regex', 'warnings', r'^(CRITICAL )?WARNING:', step=step, index=index, clobber=False)

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
            chip.set('metric', 'setupwns', setup_wns, step=step, index=index)
        if setup_tns:
            chip.set('metric', 'setuptns', setup_tns, step=step, index=index)
        if hold_wns:
            chip.set('metric', 'holdwns', hold_wns, step=step, index=index)
        if hold_tns:
            chip.set('metric', 'holdtns', hold_tns, step=step, index=index)

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
            chip.set('metric', 'luts', vals['luts'], step=step, index=index)
        if 'regs' in vals:
            chip.set('metric', 'registers', vals['regs'], step=step, index=index)

        total_bram = 0
        if 'bram' in vals: total_bram += vals['bram']
        if 'uram' in vals: total_bram += vals['uram']
        if 'bram' in vals or 'uram' in vals:
            chip.set('metric', 'brams', total_bram, step=step, index=index)

def post_process(chip):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')

    _parse_qor_summary(chip, step, index)
    _parse_utilization(chip, step, index)
