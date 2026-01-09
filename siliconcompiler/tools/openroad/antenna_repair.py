from typing import Optional, Union

from siliconcompiler import TaskSkip
from siliconcompiler.tools.openroad._apr import APRTask
from siliconcompiler.tools.openroad._apr import OpenROADSTAParameter, OpenROADGRTParameter, \
    OpenROADANTParameter, OpenROADFillCellsParameter


class AntennaRepairTask(APRTask, OpenROADSTAParameter, OpenROADGRTParameter, OpenROADANTParameter,
                        OpenROADFillCellsParameter):
    '''
    Perform antenna repair
    '''
    def __init__(self):
        super().__init__()

        self.add_parameter("ant_check", "bool",
                           "true/false, flag to indicate whether to check for antenna violations",
                           defvalue=True)
        self.add_parameter("ant_repair", "bool",
                           "true/false, flag to indicate whether to repair antenna violations",
                           defvalue=True)

    def set_openroad_antcheck(self, enable: bool,
                              step: Optional[str] = None, index: Optional[Union[int, str]] = None):
        """
        Enables or disables checking for antenna violations.

        Args:
            enable (bool): True to check, False to skip.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "ant_check", enable, step=step, index=index)

    def set_openroad_antrepair(self, enable: bool,
                               step: Optional[str] = None, index: Optional[Union[int, str]] = None):
        """
        Enables or disables repairing antenna violations.

        Args:
            enable (bool): True to repair, False to skip.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "ant_repair", enable, step=step, index=index)

    def task(self):
        return "antenna_repair"

    def setup(self):
        super().setup()

        self.set_script("apr/sc_antenna_repair.tcl")

        self._set_reports([
            'setup',
            'hold',
            'unconstrained',
            'clock_skew',
            'power',
            'drv_violations',
            'fmax',

            # Images
            'placement_density',
            'routing_congestion',
            'power_density',
            'optimization_placement',
            'clock_placement',
            'clock_trees',
            'module_view'
        ])

        self.add_required_key("var", "ant_check")
        self.add_required_key("var", "ant_repair")

    def pre_process(self):
        if not self.get("var", "ant_check"):
            raise TaskSkip("antenna repair is disabled")
        super().pre_process()
