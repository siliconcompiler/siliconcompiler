from siliconcompiler.tools._common.cocotb.cocotb_task import CocotbTask
from siliconcompiler.tools.execute.exec_input import ExecInputTask


class CocotbExecTask(CocotbTask, ExecInputTask):

    def __init__(self):
        super().__init__()

    def tool(self):
        return "verilator"

    def task(self):
        return super().task()

    def setup(self):
        super().setup()

    def runtime_options(self):
        options = super().runtime_options()

        # Add trace options if tracing is enabled
        if self.get("var", "trace"):
            options.append("--trace")

            trace_type = self.get("var", "trace_type")
            if trace_type == "vcd":
                ext = "vcd"
            elif trace_type == "fst":
                ext = "fst"
            else:
                ext = "vcd"  # Default to VCD

            trace_file = f"reports/{self.design_topmodule}.{ext}"
            options.extend(["--trace-file", trace_file])

        return options

    def post_process(self):
        super().post_process()
