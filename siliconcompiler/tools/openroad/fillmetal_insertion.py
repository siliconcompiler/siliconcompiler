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

            # Images
            'placement_density',
            'routing_congestion',
            'power_density',
            'optimization_placement',
            'clock_placement',
            'clock_trees'
        ])

        self.add_required_key("var", "fin_add_fill")

        if self.get("var", "fin_add_fill"):
            found = False
            # for fileset in self.pdk.get("pdk", "fill", "runsetfileset", "openroad"):
            #     if self.pdk.valid("fileset", fileset, "file", "fill"):
            #         self.add_required_key(self.pdk, "fileset", fileset, "file", "fill")
            #         found = True

            if not found:
                raise TaskSkip("no metal fill script is available")
            # if self.pdk.valid("chip.get('pdk', pdk, 'aprtech', tool, stackup, libtype, 'fill'):
            #     chip.add('tool', tool, 'task', task, 'require',
            #             ",".join(['pdk', pdk, 'aprtech', tool, stackup, libtype, 'fill']),
            #             step=step, index=index)
            # else:
            #     if not has_pre_post_script(chip):
            #         # nothing to do so we can skip
            #         return "no fill script is available"

            #     chip.set('tool', tool, 'task', task, 'var', 'fin_add_fill', False,
            #             step=step, index=index)
