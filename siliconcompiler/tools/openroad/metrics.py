from siliconcompiler.tools.openroad._apr import APRTask
from siliconcompiler.tools.openroad._apr import OpenROADSTAParameter


class MetricsTask(APRTask, OpenROADSTAParameter):
    '''
    Extract metrics
    '''
    def task(self):
        return "metrics"

    def setup(self):
        super().setup()

        self.set_script("apr/sc_metrics.tcl")

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
            'clock_placement',
            'clock_trees',
            'optimization_placement'
        ])
