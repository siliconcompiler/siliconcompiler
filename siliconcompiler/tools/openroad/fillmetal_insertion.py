from siliconcompiler.tools.openroad import OpenROADFillParameter
from siliconcompiler.tools.openroad._apr import APRTask
from siliconcompiler.tools.openroad._apr import OpenROADSTAParameter

from siliconcompiler import TaskSkip


class FillMetalTask(APRTask, OpenROADSTAParameter, OpenROADFillParameter):
    '''
    Perform fill metal insertion
    '''
    def task(self):
        return "fillmetal_insertion"

    def setup(self):
        super().setup()

        self.set_script("apr/sc_fillmetal_insertion.tcl")

        self._set_reports([
            'scenarios',
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

        # A pre or post script gives the node a reason to run even when it will not
        # fill anything, so neither skip below applies when one is attached.
        has_scripts = bool(self.get("prescript") or self.get("postscript"))

        if not self.get("var", "fin_add_fill"):
            if not has_scripts:
                raise TaskSkip("metal fill is disabled")
            return

        # If the PDK provides no metal fill rules there is nothing to do and the
        # task is skipped.
        if not self._setup_fill_deck() and not has_scripts:
            raise TaskSkip("no metal fill rules are available")
