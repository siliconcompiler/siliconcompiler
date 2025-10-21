import os
import re
import shutil

import os.path

from typing import Optional

from siliconcompiler.utils import sc_open

from siliconcompiler import Task
from siliconcompiler.asic import ASICTask


class ConvertTask(ASICTask, Task):
    def __init__(self):
        super().__init__()

        self.add_parameter("memorychannels", "int", "Number of memory channels available",
                           defvalue=1)

    def set_bambu_memorychannels(self, channels: int,
                                 step: Optional[str] = None, index: Optional[str] = None) -> None:
        """Sets the number of memory channels for the Bambu synthesizer.

        This method configures the 'memorychannels' variable within the Bambu
        tool flow. It's used to specify the number of independent memory
        channels the synthesized hardware should have.

        Args:
            channels: The number of memory channels to configure.
            step: The specific synthesis step to which this setting applies.
                  If None, it applies globally. Defaults to None.
            index: The index for the step, used if a step can have multiple
                   configurations. Defaults to None.
        """
        self.set("var", "memorychannels", channels, step=step, index=index)

    def tool(self):
        return "bambu"

    def task(self):
        return "convert"

    def parse_version(self, stdout):
        # Long multiline output, but second-to-last line looks like:
        # Version: PandA 0.9.6 - Revision 5e5e306b86383a7d85274d64977a3d71fdcff4fe-main
        version_line = stdout.split('\n')[-3]
        return version_line.split()[2]

    def setup(self):
        super().setup()

        self.set_exe("bambu", vswitch="--version")
        self.add_version(">=2024.03")

        self.set_threads(1)

        self.add_output_file(ext="v")

        self.add_required_key("option", "design")
        self.add_required_key("option", "fileset")
        if self.project.get("option", "alias"):
            self.add_required_key("option", "alias")

        # Mark required
        for lib, fileset in self.project.get_filesets():
            if lib.has_idir(fileset):
                self.add_required_key(lib, "fileset", fileset, "idir")
            if lib.get("fileset", fileset, "define"):
                self.add_required_key(lib, "fileset", fileset, "define")
            if lib.has_file(fileset=fileset, filetype="c"):
                self.add_required_key(lib, "fileset", fileset, "file", "c")
            elif lib.has_file(fileset=fileset, filetype="llvm"):
                self.add_required_key(lib, "fileset", fileset, "file", "llvm")

    def runtime_options(self):
        options = super().runtime_options()

        filesets = self.project.get_filesets()
        idirs = []
        defines = []
        for lib, fileset in filesets:
            idirs.extend(lib.get_idir(fileset))
            defines.extend(lib.get("fileset", fileset, "define"))

        for idir in idirs:
            options.append(f"-I{idir}")

        for define in defines:
            options.append(f"-D{define}")

        for lib, fileset in filesets:
            if lib.get_file(fileset=fileset, filetype="c"):
                for value in lib.get_file(fileset=fileset, filetype="c"):
                    options.append(value)
            elif lib.get_file(fileset=fileset, filetype="llvm"):
                for value in lib.get_file(fileset=fileset, filetype="llvm"):
                    options.append(value)

        options.append('--soft-float')
        options.append('--memory-allocation-policy=NO_BRAM')

        mem_channels = self.get("var", "memorychannels")
        if mem_channels > 0:
            options.append(f'--channels-number={mem_channels}')

        clk_name, clk_period = self.get_clock()
        if clk_period is not None:
            if self.mainlib.valid("var", "bambu_clock_multiplier"):
                clock_multiplier = self.mainlib.get("var", "bambu_clock_multiplier")
            else:
                clock_multiplier = 1.0
            clk_period *= clock_multiplier
            if clk_name:
                options.append(f'--clock-name={clk_name}')
            options.append(f'--clock-period={clk_period}')

        options.append('--disable-function-proxy')

        if self.project.valid("asic", "mainlib"):
            device = self.project.get("library",
                                      self.project.get("asic", "mainlib"),
                                      "tool", "bambu", "device")
            if device:
                options.append(f'--device={device}')

        options.append(f'--top-fname={self.design_topmodule}')

        return options

    def post_process(self):
        super().post_process()

        shutil.copy2(f'{self.design_topmodule}.v', os.path.join('outputs',
                                                                f'{self.design_topmodule}.v'))

        ff = re.compile(fr"Total number of flip-flops in function {self.design_topmodule}: (\d+)")
        area = re.compile(r"Total estimated area: (\d+)")
        fmax = re.compile(r"Estimated max frequency \(MHz\): (\d+\.?\d*)")
        slack = re.compile(r"Minimum slack: (\d+\.?\d*)")

        log_file = self.get_logpath("exe")
        with sc_open(log_file) as log:
            for line in log:
                ff_match = ff.findall(line)
                area_match = area.findall(line)
                fmax_match = fmax.findall(line)
                slack_match = slack.findall(line)
                if ff_match:
                    self.record_metric("registers", int(ff_match[0]), log_file)
                if area_match:
                    self.record_metric("cellarea", float(area_match[0]), log_file,
                                       source_unit='um^2')
                if fmax_match:
                    self.record_metric("fmax", float(fmax_match[0]), log_file, source_unit='MHz')
                if slack_match:
                    slack_ns = float(slack_match[0])
                    if slack_ns >= 0:
                        self.record_metric("setupwns", 0, log_file, source_unit='ns')
                    else:
                        self.record_metric("setupwns", slack_ns, log_file, source_unit='ns')
                    self.record_metric("setupslack", slack_ns, log_file, source_unit='ns')
