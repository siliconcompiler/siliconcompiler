import shlex

import os.path

from xml.etree import ElementTree

from siliconcompiler.tools.klayout import KLayoutTask
from siliconcompiler.asic import ASICTask


class DRCTask(KLayoutTask):
    def __init__(self):
        super().__init__()

        self.add_parameter("drc_name", "str", "name of the DRC deck to run")

    def task(self):
        return "drc"

    def setup(self):
        super().setup()

        self.add_commandline_option(['-z', '-nc', '-rx'], clobber=True)

        if f"{self.design_topmodule}.gds" in self.get_files_from_input_nodes():
            self.add_input_file(ext="gds")
        else:
            # Mark required
            for lib, fileset in self.project.get_filesets():
                if lib.has_file(fileset=fileset, filetype="gds"):
                    self.add_required_key(lib, "fileset", fileset, "file", "gds")

        self.add_output_file(ext="lyrdb")

        self.add_required_key("var", "drc_name")

    def runtime_options(self):
        options = ASICTask.runtime_options(self)

        layout = None
        for file in [f'inputs/{self.design_topmodule}.gds', f'inputs/{self.design_topmodule}.oas']:
            if os.path.isfile(file):
                layout = file
                break
        if not layout:
            for lib, fileset in self.project.get_filesets():
                if lib.has_file(fileset=fileset, filetype="gds"):
                    layout = lib.get_file(fileset, filetype="gds")[0]

        drc_name = self.get("var", "drc_name")

        runset = None
        for fileset in self.pdk.get("pdk", "drc", "runsetfileset", "klayout", drc_name):
            files = self.pdk.get_file(fileset, "drc")
            if files:
                runset = files[0]
                break

        params_lookup = {
            "<topcell>": self.design_topmodule,
            "<report>": shlex.quote(os.path.abspath(f"outputs/{self.design_topmodule}.lyrdb")),
            "<threads>": self.get_threads(),
            "<input>": shlex.quote(layout)
        }

        options.extend(['-r', runset])

        for deck, param in self.pdk.get("tool", "klayout", "drc_params"):
            if deck != drc_name:
                continue

            for lookup, value in params_lookup.items():
                param = param.replace(lookup, str(value))
            options.extend(
                ['-rd', param]
            )

        return options

    def post_process(self):
        drc_db = f"outputs/{self.design_topmodule}.lyrdb"

        drc_report = None
        if os.path.isfile(drc_db):
            with open(drc_db, "r") as f:
                drc_report = ElementTree.fromstring(f.read())
        if drc_report is None:
            drc_db = []

        violation_count = 0
        if drc_report:
            violations = drc_report.find('items')
            if violations:
                violation_count = len(violations.findall('item'))

        self.record_metric("drcs", violation_count, drc_db)
