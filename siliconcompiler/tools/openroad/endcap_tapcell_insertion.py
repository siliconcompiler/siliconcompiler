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
            # Images
            'placement_density'
        ])
