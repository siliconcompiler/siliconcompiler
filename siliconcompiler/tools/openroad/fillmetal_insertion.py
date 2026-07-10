from typing import Optional, Union

from siliconcompiler.tools.openroad._apr import APRTask
from siliconcompiler.tools.openroad._apr import OpenROADSTAParameter

from siliconcompiler import TaskSkip


class FillMetalTask(APRTask, OpenROADSTAParameter):
    '''
    Perform fill metal insertion
    '''
    def __init__(self):
        super().__init__()

        self.add_parameter("fin_add_fill", "bool",
                           "true/false, when true enables adding fill, "
                           "if enabled by the PDK, to the design", defvalue=True)

    def set_openroad_addfill(self, enable: bool,
                             step: Optional[str] = None, index: Optional[Union[int, str]] = None):
        """
        Enables or disables adding fill to the design.

        Args:
            enable (bool): True to enable fill, False to disable.
            step (str, optional): The specific step to apply this configuration to.
            index (str, optional): The specific index to apply this configuration to.
        """
        self.set("var", "fin_add_fill", enable, step=step, index=index)

    def task(self):
        return "fillmetal_insertion"

    def setup(self):
        super().setup()

        self.set_script("apr/sc_fillmetal_insertion.tcl")

        self._set_reports([
            'setup',
            'hold',
            'unconstrained',
            'clock_skew',
            'drv_violations',
            'fmax',
            'floating_nets',
            'overdriven_nets',
            "logicdepth",

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

        self.add_required_key("var", "fin_add_fill")

        if self.get("var", "fin_add_fill"):
            # The metal fill rules are shipped by the PDK as a fill file (filetype
            # "fill") inside the OpenROAD APR tech fileset. Mark it required so it is
            # hashed (cache) and copied (remote runs). If no PDK provides one, there
            # is nothing to do and the task is skipped.
            found = False
            for fileset in self.pdk.get("pdk", "aprtechfileset", "openroad"):
                if self.pdk.has_file(fileset=fileset, filetype="fill"):
                    self.add_required_key(self.pdk, "fileset", fileset, "file", "fill")
                    found = True

            if not found:
                raise TaskSkip("no metal fill rules are available")
