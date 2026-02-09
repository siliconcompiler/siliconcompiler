from typing import Optional, Union

from siliconcompiler.tools.openroad._apr import APRTask
from siliconcompiler.tools.openroad._apr import OpenROADSTAParameter, OpenROADGPLParameter, \
    OpenROADGRTGeneralParameter, OpenROADPPLParameter


class GlobalPlacementTask(APRTask, OpenROADSTAParameter, OpenROADGPLParameter,
                          OpenROADGRTGeneralParameter, OpenROADPPLParameter):
    '''
    Perform global placement
    '''
    def __init__(self):
        super().__init__()

        self.add_parameter("enable_scan_chains", "bool",
                           "true/false, when true scan chains will be inserted.", defvalue=False)
        self.add_parameter("scan_enable_port_pattern", "str",
                           "pattern of the scan chain enable port")
        self.add_parameter("scan_in_port_pattern", "str",
                           "pattern of the scan chain in port")
        self.add_parameter("scan_out_port_pattern", "str",
                           "pattern of the scan chain out port")

        self.add_parameter("enable_multibit_clustering", "bool",
                           "true/false, when true multibit clustering will be performed.",
                           defvalue=False)

    def set_openroad_enablescanchains(self, enable: bool,
                                      step: Optional[str] = None,
                                      index: Optional[Union[int, str]] = None):
        """
        Enables or disables scan chain insertion.

        Args:
            enable (bool): True to enable, False to disable.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "enable_scan_chains", enable, step=step, index=index)

    def set_openroad_scanenableportpattern(self, pattern: str,
                                           step: Optional[str] = None,
                                           index: Optional[Union[int, str]] = None):
        """
        Sets the pattern for the scan chain enable port.

        Args:
            pattern (str): The port pattern.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "scan_enable_port_pattern", pattern, step=step, index=index)

    def set_openroad_scaninportpattern(self, pattern: str,
                                       step: Optional[str] = None,
                                       index: Optional[Union[int, str]] = None):
        """
        Sets the pattern for the scan chain input port.

        Args:
            pattern (str): The port pattern.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "scan_in_port_pattern", pattern, step=step, index=index)

    def set_openroad_scanoutportpattern(self, pattern: str,
                                        step: Optional[str] = None,
                                        index: Optional[Union[int, str]] = None):
        """
        Sets the pattern for the scan chain output port.

        Args:
            pattern (str): The port pattern.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "scan_out_port_pattern", pattern, step=step, index=index)

    def set_openroad_enablemultibitclustering(self, enable: bool,
                                              step: Optional[str] = None,
                                              index: Optional[Union[int, str]] = None):
        """
        Enables or disables multibit clustering.

        Args:
            enable (bool): True to enable, False to disable.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "enable_multibit_clustering", enable, step=step, index=index)

    def task(self):
        return "global_placement"

    def setup(self):
        super().setup()

        self.set_script("apr/sc_global_placement.tcl")

        self._set_reports([
            'setup',
            'unconstrained',
            'power',
            'fmax',
            'report_buffers',

            # Images
            'placement_density',
            'routing_congestion',
            'power_density',
            'module_view'
        ])

        self.add_required_key("var", "enable_multibit_clustering")
        self.add_required_key("var", "enable_scan_chains")
        if self.get("var", "scan_enable_port_pattern"):
            self.add_required_key("var", "scan_enable_port_pattern")
        if self.get("var", "scan_in_port_pattern"):
            self.add_required_key("var", "scan_in_port_pattern")
        if self.get("var", "scan_out_port_pattern"):
            self.add_required_key("var", "scan_out_port_pattern")
