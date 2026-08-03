from typing import Optional, Union

from siliconcompiler.tools.openroad._apr import APRTask
from siliconcompiler.tools.openroad._apr import OpenROADSTAParameter, \
    OpenROADDRTPinAccessParameter, OpenROADDRTParameter, OpenROADANTCheckParameter, \
    OpenROADFillCellsParameter


class DetailedRouteTask(APRTask, OpenROADSTAParameter, OpenROADDRTPinAccessParameter,
                        OpenROADDRTParameter, OpenROADANTCheckParameter,
                        OpenROADFillCellsParameter):
    '''
    Perform detailed routing

    After routing, antenna violations are checked and, while any remain, repaired by
    inserting diodes and rerouting the affected nets. The loop needs the main library
    to declare an antenna cell; without one it is skipped and only the check runs.

    Setting ``ant_margin`` above zero also enables the loop on a design the check
    reports as clean, since the point of a margin is to fix nets that are merely
    close to the antenna limit.
    '''
    def __init__(self):
        super().__init__()

        self.add_parameter("ant_reroute_iterations", "int<0..>",
                           "maximum number of antenna repair and reroute iterations to perform "
                           "after detailed routing, 0 disables post-route antenna repair",
                           defvalue=5)

    def set_openroad_antrerouteiterations(self, iterations: int,
                                          step: Optional[str] = None,
                                          index: Optional[Union[int, str]] = None):
        """
        Sets the maximum number of post-route antenna repair and reroute iterations.

        This is the outer loop around ``repair_antennas`` and ``detailed_route``, and is
        distinct from ``ant_iterations``, which bounds the iterations inside a single
        ``repair_antennas`` call.

        Args:
            iterations (int): The number of iterations, 0 disables the loop.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "ant_reroute_iterations", iterations, step=step, index=index)

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

        self.add_required_key("var", "ant_reroute_iterations")
