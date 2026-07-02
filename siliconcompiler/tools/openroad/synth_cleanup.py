from typing import Optional

from siliconcompiler.tools.openroad._apr import APRTask
from siliconcompiler.tools.openroad._apr import OpenROADSTAParameter


class CleanupSynthTask(APRTask, OpenROADSTAParameter):
    """
    A task for cleaning up synthesized netlists using OpenROAD.
    Mainly used to remove buffers and dead logic inserted during synthesis from yosys.
    """
    def __init__(self):
        super().__init__()

        self.add_parameter("remove_synth_buffers", "bool",
                           "remove buffers inserted by synthesis", defvalue=True)
        self.add_parameter("remove_dead_logic", "bool",
                           "remove logic which does not drive a primary output", defvalue=True)

    def set_openroad_removebuffers(self, enable: bool,
                                   step: Optional[str] = None, index: Optional[str] = None):
        """
        Enables or disables the removal of buffers inserted during synthesis.

        Args:
            enable: True to remove synthesis buffers, False to keep them.
            step: The specific step to apply this configuration to.
            index: The specific index to apply this configuration to.
        """
        self.set("var", "remove_synth_buffers", enable, step=step, index=index)

    def set_openroad_removedeadlogic(self, enable: bool,
                                     step: Optional[str] = None, index: Optional[str] = None):
        """
        Enables or disables the removal of logic that does not drive a primary output.

        Args:
            enable: True to remove dead logic, False to keep it.
            step: The specific step to apply this configuration to.
            index: The specific index to apply this configuration to.
        """
        self.set("var", "remove_dead_logic", enable, step=step, index=index)

    def task(self):
        return "cleanup_synth"

    def setup(self):
        super().setup()

        self.set_script("apr/sc_cleanup_synth.tcl")

        self._set_reports([
            'check_setup',
            'setup',
            'unconstrained',
            'power',
            'floating_nets',
            'overdriven_nets',
            "logicdepth"
        ])
        self.set_openroad_enableimages(False)

        self.add_required_key("var", "remove_synth_buffers")
        self.add_required_key("var", "remove_dead_logic")
