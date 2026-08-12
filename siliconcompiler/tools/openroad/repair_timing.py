from typing import List, Optional, Union

from siliconcompiler import TaskSkip
from siliconcompiler.tools.openroad._apr import APRTask
from siliconcompiler.tools.openroad._apr import OpenROADSTAParameter, OpenROADDPLParameter, \
    OpenROADRSZDRVParameter, OpenROADRSZTimingParameter, OpenROADFillCellsParameter, \
    OpenROADGRTGeneralParameter, RSZ_MOVES


class RepairTimingTask(APRTask, OpenROADSTAParameter, OpenROADDPLParameter,
                       OpenROADRSZDRVParameter, OpenROADRSZTimingParameter,
                       OpenROADFillCellsParameter):
    '''
    Perform setup and hold timing repairs
    '''
    def __init__(self):
        super().__init__()

        self.add_parameter("rsz_skip_drv_repair", "bool", "skip design rule violation repair",
                           defvalue=False)
        self.add_parameter("rsz_skip_setup_repair", "bool", "skip setup timing repair",
                           defvalue=False)
        self.add_parameter("rsz_skip_hold_repair", "bool", "skip hold timing repair",
                           defvalue=False)
        self.add_parameter("rsz_skip_recover_power", "bool", "skip power recovery",
                           defvalue=self._default_skip_recover_power())
        # Unlike its siblings this defaults to skipped: the pass only makes sense once
        # global routing exists, since its default move sequence reroutes nets.
        self.add_parameter("rsz_skip_wns_repair", "bool",
                           "skip the disturbance minimizing worst negative slack repair pass. "
                           "This pass only applies once global routing has been performed",
                           defvalue=self._default_skip_wns_repair())
        self.add_parameter("rsz_wns_sequence", f"[<{','.join(RSZ_MOVES)}>]",
                           "order of optimization moves to use for the worst negative slack "
                           "repair pass, an empty list uses the tool default",
                           defvalue=["vt_swap", "reroute"])

    def _default_skip_recover_power(self) -> bool:
        return False

    def _default_skip_wns_repair(self) -> bool:
        return True

    def set_openroad_skipdrvrepair(self, skip: bool,
                                   step: Optional[str] = None,
                                   index: Optional[Union[int, str]] = None):
        """
        Enables or disables skipping design rule violation repair.

        Args:
            skip (bool): True to skip repair, False to perform it.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "rsz_skip_drv_repair", skip, step=step, index=index)

    def set_openroad_skipsetuprepair(self, skip: bool,
                                     step: Optional[str] = None,
                                     index: Optional[Union[int, str]] = None):
        """
        Enables or disables skipping setup timing repair.

        Args:
            skip (bool): True to skip repair, False to perform it.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "rsz_skip_setup_repair", skip, step=step, index=index)

    def set_openroad_skipholdrepair(self, skip: bool,
                                    step: Optional[str] = None,
                                    index: Optional[Union[int, str]] = None):
        """
        Enables or disables skipping hold timing repair.

        Args:
            skip (bool): True to skip repair, False to perform it.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "rsz_skip_hold_repair", skip, step=step, index=index)

    def set_openroad_skiprecoverpower(self, skip: bool,
                                      step: Optional[str] = None,
                                      index: Optional[Union[int, str]] = None):
        """
        Enables or disables skipping power recovery.

        Args:
            skip (bool): True to skip recovery, False to perform it.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "rsz_skip_recover_power", skip, step=step, index=index)

    def set_openroad_skipwnsrepair(self, skip: bool,
                                   step: Optional[str] = None,
                                   index: Optional[Union[int, str]] = None):
        """
        Enables or disables skipping the worst negative slack repair pass.

        This pass minimizes placement and routing disturbance and is only
        meaningful once global routing has been performed.

        Args:
            skip (bool): True to skip the pass, False to perform it.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "rsz_skip_wns_repair", skip, step=step, index=index)

    def add_openroad_rszwnssequence(self, moves: Union[str, List[str]],
                                    step: Optional[str] = None,
                                    index: Optional[Union[int, str]] = None,
                                    clobber: bool = False):
        """
        Adds moves to the worst negative slack repair pass move order.

        Moves are appended in call order. Unlike the other move lists this one has a
        non-empty default, so adding extends ``vt_swap reroute`` rather than replacing
        it -- pass clobber to supply the whole sequence instead.

        Args:
            moves (Union[str, List[str]]): The ordered move name(s) to add.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
            clobber (bool, optional): If True, overwrites the existing list. Defaults to False.
        """
        if clobber:
            self.set("var", "rsz_wns_sequence", moves, step=step, index=index)
        else:
            self.add("var", "rsz_wns_sequence", moves, step=step, index=index)

    def task(self):
        return "repair_timing"

    def setup(self):
        super().setup()

        self.set_script("apr/sc_repair_timing.tcl")

        self._set_reports([
            'setup',
            'hold',
            'unconstrained',
            'clock_skew',
            'power',
            'drv_violations',
            'fmax',
            'report_buffers',
            'floating_nets',
            'overdriven_nets',
            "logicdepth",
            'design_stats',
            'scenarios',

            # Images
            'snapshot',
            'placement_view',
            'routing_view',
            'markers_view',
            'placement_density',
            'routing_congestion',
            'power_density',
            'optimization_placement',
            'clock_placement',
            'clock_trees',
            'module_view'
        ])

        self.add_required_key("var", "rsz_skip_drv_repair")
        self.add_required_key("var", "rsz_skip_setup_repair")
        self.add_required_key("var", "rsz_skip_hold_repair")
        self.add_required_key("var", "rsz_skip_recover_power")
        self.add_required_key("var", "rsz_skip_wns_repair")
        if not self.get("var", "rsz_skip_wns_repair") and self.get("var", "rsz_wns_sequence"):
            self.add_required_key("var", "rsz_wns_sequence")


class PostRouteRepairTimingTask(RepairTimingTask, OpenROADGRTGeneralParameter):
    '''
    Repair timing on a globally routed design

    Runs design rule violation repair, setup repair and hold repair against the
    global routing parasitics, each followed by an incremental global route and
    detailed placement so the design stays routed and legal. A final worst negative
    slack pass then targets the single worst endpoint using only threshold voltage
    swaps and rerouting, which improves the critical path while leaving placement
    and routing almost untouched.

    Repairing an already routed design changes both quality of results and runtime,
    so the task is opt-in: ``rsz_enable`` must be set for it to run. Otherwise the
    node is skipped and its inputs are forwarded unchanged.
    '''
    def __init__(self):
        super().__init__()

        self.add_parameter("rsz_enable", "bool",
                           "true/false, when true perform timing repair using the global "
                           "routing parasitics", defvalue=False)

    def _default_skip_wns_repair(self) -> bool:
        """The worst negative slack pass needs the routing its moves reroute, so it is
        on here and off for the pre-route repair."""
        return False

    def _default_skip_recover_power(self) -> bool:
        """Power recovery upsizes and downsizes across the whole design, which undoes
        the point of a pass this careful about disturbing a routed result."""
        return True

    def _default_match_cell_footprint(self) -> bool:
        """Restricting swaps to cells of the same footprint keeps the repair from
        moving the placement the design was already routed against."""
        return True

    def set_openroad_rszenable(self, enable: bool,
                               step: Optional[str] = None,
                               index: Optional[Union[int, str]] = None):
        """
        Enables or disables the post global route timing repair.

        Args:
            enable (bool): True to perform the repair, False to skip the node.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "rsz_enable", enable, step=step, index=index)

    def task(self):
        return "post_route_repair_timing"

    def setup(self):
        # rsz_enable cannot change between setup and execution, so drop the node here
        # rather than in pre_process and avoid building a work directory for it.
        if not self.get("var", "rsz_enable"):
            raise TaskSkip("post route timing repair is disabled")

        super().setup()

        self.add_required_key("var", "rsz_enable")
