from typing import Optional, Union

from siliconcompiler.tools.openroad._apr import APRTask
from siliconcompiler.tools.openroad._apr import OpenROADSTAParameter, OpenROADRSZDRVParameter


class RepairDesignTask(APRTask, OpenROADSTAParameter, OpenROADRSZDRVParameter):
    '''
    Perform timing repair and tie-off cell insertion
    '''
    def __init__(self):
        super().__init__()

        self.add_parameter("ifp_tie_separation", "float",
                           "maximum distance between tie high/low cells in microns",
                           defvalue=0, unit="um")

        self.add_parameter("rsz_buffer_inputs", "bool",
                           "true/false, when true enables adding buffers to the input ports",
                           defvalue=False)
        self.add_parameter("rsz_buffer_outputs", "bool",
                           "true/false, when true enables adding buffers to the output ports",
                           defvalue=False)

    def set_openroad_tieseparation(self, separation: float,
                                   step: Optional[str] = None,
                                   index: Optional[Union[int, str]] = None):
        """
        Sets the maximum distance between tie high/low cells.

        Args:
            separation (float): The separation distance in microns.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "ifp_tie_separation", separation, step=step, index=index)

    def set_openroad_bufferinputs(self, enable: bool,
                                  step: Optional[str] = None,
                                  index: Optional[Union[int, str]] = None):
        """
        Enables or disables adding buffers to the input ports.

        Args:
            enable (bool): True to enable, False to disable.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "rsz_buffer_inputs", enable, step=step, index=index)

    def set_openroad_bufferoutputs(self, enable: bool,
                                   step: Optional[str] = None,
                                   index: Optional[Union[int, str]] = None):
        """
        Enables or disables adding buffers to the output ports.

        Args:
            enable (bool): True to enable, False to disable.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "rsz_buffer_outputs", enable, step=step, index=index)

    def task(self):
        return "repair_design"

    def setup(self):
        super().setup()

        self.set_script("apr/sc_repair_design.tcl")

        self._set_reports([
            'setup',
            'unconstrained',
            'power',
            'drv_violations',
            'fmax',
            'report_buffers',

            # Images
            'placement_density',
            'routing_congestion',
            'power_density',
            'optimization_placement',
            'module_view'
        ])

        self.add_required_key("var", "ifp_tie_separation")
        self.add_required_key("var", "rsz_buffer_inputs")
        self.add_required_key("var", "rsz_buffer_outputs")
