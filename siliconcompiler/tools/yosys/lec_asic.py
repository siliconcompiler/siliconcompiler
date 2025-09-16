import re

from siliconcompiler import sc_open

from siliconcompiler.tools.yosys.syn_asic import _ASICTask


class ASICLECTask(_ASICTask):
    '''
    Perform logical equivalence checks
    '''
    def __init__(self):
        super().__init__()

        self.add_parameter("induction_steps", "int",
                           "Number of induction steps for yosys equivalence checking", defvalue=10)

    def task(self):
        return "lec_asic"

    def setup(self):
        super().setup()

        self.set_script("sc_lec.tcl")

        self.add_required_key("var", "induction_steps")

        if f"{self.design_topmodule}.lec.vg" in self.get_files_from_input_nodes():
            self.add_input_file(ext="lec.vg")
            if f"{self.design_topmodule}.vg" in self.get_files_from_input_nodes():
                self.add_input_file(ext="vg")
            else:
                self.add_input_file(ext="v")
        else:
            self.add_input_file(ext="vg")
            self.add_input_file(ext="v")

    def post_process(self):
        super().post_process()

        with sc_open(self.get_logpath("exe")) as f:
            for line in f:
                if line.endswith('Equivalence successfully proven!\n'):
                    self.record_metric("drvs", 0, self.get_logpath("exe"))
                    continue

                errors = re.search(r'Found a total of (\d+) unproven \$equiv cells.', line)
                if errors is not None:
                    num_errors = int(errors.group(1))
                    self.record_metric("drvs", num_errors, self.get_logpath("exe"))
