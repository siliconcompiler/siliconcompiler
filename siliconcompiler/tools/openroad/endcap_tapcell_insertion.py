from siliconcompiler.tools.openroad._apr import APRTask
from siliconcompiler.tools.openroad._apr import OpenROADSTAParameter


class EndCapTapCellTask(APRTask, OpenROADSTAParameter):
    '''
    Perform endcap and tap cell insertion
    '''
    def __init__(self):
        super().__init__()

    def task(self):
        return "endcap_tapcell_insertion"

    def setup(self):
        super().setup()

        self.set_script("apr/sc_endcap_tapcell_insertion.tcl")

        self._set_reports([
            'scenarios',
            'floating_nets',
            'overdriven_nets',

            # Images
            'snapshot',
            'placement_view',
            'routing_view',
            'markers_view',
            'placement_density'
        ])

        # sc_endcap_tapcell_insertion.tcl sources the tapcells file when the mainlib
        # defines it; declare it required so it is hashed (cache) and copied (remote).
        if self.mainlib.get("tool", "openroad", "tapcells"):
            self.add_required_key(self.mainlib, "tool", "openroad", "tapcells")
