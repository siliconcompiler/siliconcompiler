import re

from siliconcompiler import sc_open

from siliconcompiler.tools.magic import MagicTask


class DRCTask(MagicTask):
    def task(self):
        return "drc"

    def setup(self):
        super().setup()

        self.add_output_file(ext="drc.mag")

    def post_process(self):
        report_path = f'reports/{self.design_topmodule}.drc'
        drcs = 0
        with sc_open(report_path) as f:
            for line in f:
                errors = re.search(r'^\[INFO\]: COUNT: (\d+)', line)

                if errors:
                    drcs = errors.group(1)
        self.record_metric('drcs', drcs, report_path)
