from typing import List, Optional

from siliconcompiler.tools.openroad._apr import APRTask
from siliconcompiler.tools.openroad._apr import OpenROADSTAParameter
from siliconcompiler.tools.openroad._apr import OpenROADRSZDRVParameter
from siliconcompiler.tools.openroad._apr import OpenROADRSZTimingParameter


# Both resizer mixins, matching RepairTimingTask: sc_repair_timing_args reads
# rsz_match_cell_footprint and rsz_max_utilization, which live on the DRV mixin because
# they apply to repair_design as well.
class CleanupSynthTask(APRTask, OpenROADSTAParameter,
                       OpenROADRSZDRVParameter, OpenROADRSZTimingParameter):
    """
    A task for cleaning up synthesized netlists using OpenROAD.
    Mainly used to remove buffers and dead logic inserted during synthesis from yosys.

    Can also run a setup repair pass over the synthesized netlist. Synthesis optimizes
    against a simple delay and capacitance model, so its gate sizing is systematically
    off in a way a liberty-accurate pass can correct, and correcting it here means
    placement is given cells that are already close to their final size. The pass is
    off by default because it moves the quality of results of every design.

    Buffer removal and timing repair are alternatives rather than additive, so enabling
    both is rejected during setup.
    """
    def __init__(self):
        super().__init__()

        self.add_parameter("remove_synth_buffers", "bool",
                           "remove buffers inserted by synthesis", defvalue=True)
        self.add_parameter("remove_dead_logic", "bool",
                           "remove logic which does not drive a primary output", defvalue=True)
        self.add_parameter("repair_synth_timing", "bool",
                           "true/false, perform setup timing repair on the synthesized netlist. "
                           "No placement exists yet, so this runs on wire load models and is "
                           "most useful for correcting gate sizing rather than wire delay",
                           defvalue=False)

    def _default_sequence(self) -> List[str]:
        """
        Restricts the pass to the moves that are meaningful before placement.

        Gate resizing is what a pre-placement pass can justify: it corrects synthesis
        sizing using real liberty delays, which needs no placement. Buffer insertion,
        cloning and load splitting are all wire-delay driven and there is no wire
        length to drive them with yet.
        """
        return ["unbuffer", "sizeup"]

    def _default_skip_final_sizing(self) -> bool:
        """
        Skips the greedy final sizing pass, which is expensive for what it returns here.

        Upstream reports the same conclusion the other way round: its guidance when
        pre-placement repair takes too long is to skip this pass or bound the repair
        with a slack margin.
        """
        return True

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

    def set_openroad_repairsynthtiming(self, enable: bool,
                                       step: Optional[str] = None,
                                       index: Optional[str] = None):
        """
        Enables or disables setup timing repair on the synthesized netlist.

        Args:
            enable: True to repair timing, False to leave the netlist as synthesized.
            step: The specific step to apply this configuration to.
            index: The specific index to apply this configuration to.
        """
        self.set("var", "repair_synth_timing", enable, step=step, index=index)

    def task(self):
        return "cleanup_synth"

    def setup(self):
        super().setup()

        self.set_script("apr/sc_cleanup_synth.tcl")

        self._set_reports([
            'scenarios',
            'check_setup',
            'setup',
            'unconstrained',
            'power',
            'floating_nets',
            'overdriven_nets',
            "logicdepth"
        ])
        self.set_openroad_enableimages(False)

        # Removing the buffers and then repairing timing is the one combination that is
        # worse than either alone: the buffering is deleted, and the repair is then asked
        # to recover from that with a move sequence that deliberately cannot insert
        # buffers. Upstream treats the two as alternatives for the same reason.
        if self.get("var", "remove_synth_buffers") and self.get("var", "repair_synth_timing"):
            raise ValueError(
                "remove_synth_buffers and repair_synth_timing are alternatives, not "
                "additive: removing the synthesis buffers discards the buffering the "
                "repair pass would otherwise refine, and the repair cannot insert "
                "buffers to replace them. Enable one or neither.")

        self.add_required_key("var", "remove_synth_buffers")
        self.add_required_key("var", "remove_dead_logic")
        self.add_required_key("var", "repair_synth_timing")
