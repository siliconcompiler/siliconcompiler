from siliconcompiler.tools.openroad._apr import APRTask
from siliconcompiler.tools.openroad._apr import OpenROADSTAParameter, OpenROADPSMParameter


class PowerGridTask(APRTask, OpenROADSTAParameter, OpenROADPSMParameter):
    '''
    Perform power grid insertion and connectivity analysis
    '''
    def __init__(self):
        super().__init__()

        self.add_parameter("fixed_pin_keepout", "float",
                           "if > 0, applies a blockage in multiples of the routing pitch to each "
                           "fixed pin to ensure there is room for routing.", defvalue=0)
        self.add_parameter("psm_allow_missing_terminal_nets", "[str]",
                           "list of nets where a missing terminal is acceptable")

        self.add_parameter("pdn_enable", "bool", "enable power grid generation", defvalue=True)
        self.add_parameter("pdn_config", "[file]", "power grid definition files")

    def task(self):
        return "power_grid"

    def setup(self):
        super().setup()

        self.set_script("apr/sc_power_grid.tcl")

        self._set_reports([])

    def pre_process(self):
        super().pre_process()

        # Setup power grid scripts
        if self.get("var", "pdn_config"):
            # Already set so do nothing
            return

        for lib in self.schema().get("asic", "asiclib"):
            libobj = self.schema().get("library", lib, field="schema")
            if libobj.valid("tool", "openroad", "power_grid"):
                self.add("var", "pdn_config", libobj.find_files("tool", "openroad", "power_grid"))

        # define_pdn_files(chip)
        # pdncfg = [file for file in chip.find_files('tool', tool, 'task', task, 'file',
        # 'pdn_config',
        #                                         step=step, index=index) if file]
        # if not has_pre_post_script(chip) and \
        #         (chip.get('tool', tool, 'task', task, 'var', 'pdn_enable',
        #                 step=step, index=index)[0] == 'false' or len(pdncfg) == 0):
        #     chip.set('record', 'status', NodeStatus.SKIPPED, step=step, index=index)
        #     chip.logger.warning(f'{step}/{index} will be skipped since power grid is disabled.')
        #     return
