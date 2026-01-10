import os.path

from typing import Union, Optional

from siliconcompiler import Task


class SimulateTask(Task):
    def __init__(self):
        super().__init__()

        self.add_parameter("trace", "bool", "true/false, enable dumping all signals")
        self.add_parameter("trace_format", "<ASCII,binary>", "Format to use for traces.",
                           defvalue="ASCII")

    def set_xyce_trace(self, enable: bool,
                       step: Optional[str] = None, index: Optional[Union[int, str]] = None):
        """
        Enables or disables dumping all signals.

        Args:
            enable (bool): True to enable, False to disable.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set('var', 'trace', enable, step=step, index=index)

    def set_xyce_traceformat(self, trace_format: str,
                             step: Optional[str] = None, index: Optional[Union[int, str]] = None):
        """
        Sets the format to use for traces.

        Args:
            trace_format (str): The format to use for traces.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set('var', 'trace_format', trace_format, step=step, index=index)

    def tool(self):
        return "xyce"

    def task(self):
        return "simulate"

    def parse_version(self, stdout):
        ver = stdout.split()[-1]
        return ver.split('-')[0]

    def setup(self):
        super().setup()

        self.set_exe("Xyce", vswitch="-v")
        self.add_version(">=v7.8")

        self.add_regex("warnings", "warning")
        self.add_regex("errors", "error")

        self.set_threads(1)

        self.add_required_key("var", "trace")
        self.add_required_key("var", "trace_format")

        if f"{self.design_topmodule}.xyce" in self.get_files_from_input_nodes():
            self.add_input_file(ext="xyce")
        elif f"{self.design_topmodule}.cir" in self.get_files_from_input_nodes():
            self.add_input_file(ext="cir")
        else:
            for lib, fileset in self.project.get_filesets():
                if lib.has_file(fileset=fileset, filetype="spice"):
                    self.add_required_key(lib, "fileset", fileset, "file", "spice")

        if self.get("var", "trace"):
            self.add_output_file(ext="raw")

    def runtime_options(self):
        options = super().runtime_options()

        if self.get("var", "trace_format") == "ASCII":
            options.append("-a")

        if self.get("var", "trace"):
            options.extend(["-r", f"outputs/{self.design_topmodule}.raw"])

        if os.path.exists(f"inputs/{self.design_topmodule}.xyce"):
            options.append(f"inputs/{self.design_topmodule}.xyce")
        elif os.path.exists(f"inputs/{self.design_topmodule}.cir"):
            options.append(f"inputs/{self.design_topmodule}.cir")
        else:
            for lib, fileset in self.project.get_filesets():
                options.extend(lib.get_file(fileset=fileset, filetype="spice"))

        return options
