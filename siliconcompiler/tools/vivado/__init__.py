'''
Vivado is an FPGA programming tool suite from Xilinx used to
program Xilinx devices.

Documentation: https://www.amd.com/en/products/software/adaptive-socs-and-fpgas/vivado.html
'''

import json
import re

import os.path

from siliconcompiler import sc_open

from siliconcompiler import Task


class VivadoTask(Task):
    def __init__(self):
        super().__init__()

    def tool(self):
        return "vivado"

    def parse_version(self, stdout):
        # Vivado v2021.2 (64-bit)
        return stdout.split()[1]

    def normalize_version(self, version):
        return version.lstrip('v')

    def setup(self):
        super().setup()

        self.set_exe("vivado", vswitch="-version", format="tcl")
        self.add_version(">=2021")

        self.set_threads()

        self.set_dataroot("vivado", __file__)
        with self.active_dataroot("vivado"):
            self.set_refdir("scripts")

        self.set_script("sc_run.tcl")
        self.add_commandline_option(['-nolog', '-nojournal', '-mode', 'batch', '-source'])

        self.add_regex("warnings", r'^(CRITICAL )?WARNING:')
        self.add_regex("errors", r'^ERROR:')

    def post_process(self):
        super().post_process()
        self._parse_qor_summary()
        self._parse_utilization()

    def _parse_qor_summary(self):
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
                self.record_metric('setupwns', setup_wns, 'reports/qor_summary.json',
                                   source_unit='ns')
            if setup_tns:
                self.record_metric('setuptns', setup_tns, 'reports/qor_summary.json',
                                   source_unit='ns')
            if hold_wns:
                self.record_metric('holdwns', hold_wns, 'reports/qor_summary.json',
                                   source_unit='ns')
            if hold_tns:
                self.record_metric('holdtns', hold_tns, 'reports/qor_summary.json',
                                   source_unit='ns')

    def _parse_utilization(self):
        if not os.path.isfile('reports/total_utilization.rpt'):
            return

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

            lut_cnt_normal = vals.get('luts', 0)
            lut_cnt_detailed = sum([cnt for name, cnt in vals.items() if name.startswith('lut')])
            lut_cnt_detailed -= vals.get('luts', 0)  # avoid double counting
            lut_cnt_detailed += vals.get("f7mux", 0)
            lut_cnt_detailed -= vals.get("f8mux", 0)

            self.record_metric("luts", lut_cnt_normal, 'reports/total_utilization.rpt')
            self.record_metric("lutsdetailed", lut_cnt_normal, 'reports/total_utilization.rpt',
                               quiet=True)

            if 'regs' in vals:
                self.record_metric('registers', vals['regs'], 'reports/total_utilization.rpt')

            total_bram = 0
            if 'bram' in vals:
                total_bram += vals['bram']
            if 'uram' in vals:
                total_bram += vals['uram']
            if 'bram' in vals or 'uram' in vals:
                self.record_metric('brams', total_bram, 'reports/total_utilization.rpt')

            if 'dsps' in vals:
                self.record_metric('dsps', vals['dsps'], 'reports/total_utilization.rpt')
