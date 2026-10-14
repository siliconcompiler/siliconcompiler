'''
Kepler-Formal is a logic equivalence checking (LEC) tool that operates on verilog
and the naja interchange format (https://github.com/keplertech/naja-if). It checks
gate-level netlists combinationally, and RTL against a netlist sequentially.

Sources: https://github.com/keplertech/kepler-formal
'''
from siliconcompiler import Task


class KeplerFormalTask(Task):
    def tool(self) -> str:
        return "kepler-formal"

    def parse_version(self, stdout: str) -> str:
        # kepler-formal version: 0.5.0
        return stdout.split()[2]

    def setup(self) -> None:
        super().setup()

        self.set_exe("kepler-formal", vswitch="--version")
        self.add_version(">=0.5.0")

        # Log file handled by kepler-formal config
        self.set_logdestination("stdout", "none")
        self.set_logdestination("stderr", "none")
