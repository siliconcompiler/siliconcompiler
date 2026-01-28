from typing import Optional, Union

from siliconcompiler.tools._common.cocotb.cocotb_task import CocotbTask
from siliconcompiler.tools.execute.exec_input import ExecInputTask


class CocotbExecTask(CocotbTask, ExecInputTask):

    def __init__(self):
        super().__init__()

        self.add_parameter("trace", "bool",
                           'Enable waveform tracing. The simulation must have been '
                           'compiled with trace support enabled.',
                           defvalue=False)

        self.add_parameter("trace_type", "<vcd,fst>",
                           'Specifies type of wave file to create when [trace] is set.',
                           defvalue="vcd")

    def set_cocotb_trace(
        self,
        enable: bool = True,
        trace_type: str = "vcd",
        step: Optional[str] = None,
        index: Optional[Union[str, int]] = None
    ):
        self.set("var", "trace", enable, step=step, index=index)
        self.set("var", "trace_type", trace_type, step=step, index=index)

    def tool(self):
        return "verilator"

    def task(self):
        return super().task()

    def setup(self):
        super().setup()

        self.add_required_key("var", "trace")
        self.add_required_key("var", "trace_type")

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
