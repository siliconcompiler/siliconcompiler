from typing import Optional, Union

from siliconcompiler import TaskSkip
from siliconcompiler.tools.openroad._apr import APRTask
from siliconcompiler.tools.openroad._apr import OpenROADSTAParameter, \
    OpenROADDRTPinAccessParameter, OpenROADDRTParameter, OpenROADANTCheckParameter, \
    OpenROADFillCellsParameter


class DetailedRouteTask(APRTask, OpenROADSTAParameter, OpenROADDRTPinAccessParameter,
                        OpenROADDRTParameter):
    '''
    Perform detailed routing
    '''
    def __init__(self):
        super().__init__()

    def task(self):
        return "detailed_route"

    def setup(self):
        super().setup()

        self.set_script("apr/sc_detailed_route.tcl")

        self._set_reports([
            'setup',
            'hold',
            'unconstrained',
            'clock_skew',
            'power',
            'drv_violations',
            'fmax',
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
            'clock_trees'
        ])


class DetailedRouteAntennaRepairTask(DetailedRouteTask, OpenROADANTCheckParameter,
                                     OpenROADFillCellsParameter):
    '''
    Repair antenna violations on the detailed routing

    Checks the routed design for antenna violations and, while any remain, inserts
    diodes and reroutes the affected nets. Repairing against the detailed routes is
    what both reference flows do, and it is the only point in the flow where the
    antenna ratios being checked are the ones that ship.

    Derives from the detailed routing task so the reroute uses exactly the detailed
    router configuration the initial route used. The loop needs the main library to
    declare an antenna cell; without one only the check runs.

    Setting ``ant_margin`` above zero also enables the repair on a design the check
    reports as clean, since the point of a margin is to fix nets that are merely
    close to the antenna limit.
    '''
    def __init__(self):
        super().__init__()

        self.add_parameter("ant_reroute_iterations", "int<0..>",
                           "maximum number of antenna repair and reroute iterations to perform, "
                           "0 disables antenna repair", defvalue=5)

    def set_openroad_antrerouteiterations(self, iterations: int,
                                          step: Optional[str] = None,
                                          index: Optional[Union[int, str]] = None):
        """
        Sets the maximum number of antenna repair and reroute iterations.

        This is the outer loop around ``repair_antennas`` and ``detailed_route``, and is
        distinct from ``ant_iterations``, which bounds the iterations inside a single
        ``repair_antennas`` call.

        Args:
            iterations (int): The number of iterations, 0 disables the repair.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "ant_reroute_iterations", iterations, step=step, index=index)

    def task(self):
        return "detailed_route_antenna_repair"

    def setup(self):
        # ant_check cannot change between setup and execution, so drop the node here
        # rather than in pre_process and avoid building a work directory for it.
        if not self.get("var", "ant_check"):
            raise TaskSkip("antenna repair is disabled")

        super().setup()

        # clobber: the parent sets the plain detailed routing script and set_script
        # does not overwrite by default, so without this the node would re-run a full
        # detailed route instead of repairing antennas.
        self.set_script("apr/sc_detailed_route_antenna_repair.tcl", clobber=True)

        self.add_required_key("var", "ant_reroute_iterations")
