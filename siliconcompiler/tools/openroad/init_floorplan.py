from siliconcompiler.tools.openroad._apr import APRTask
from siliconcompiler.tools.openroad._apr import OpenROADSTAParameter, OpenROADPPLParameter


class InitFloorplanTask(APRTask,
                        OpenROADSTAParameter,
                        OpenROADPPLParameter):
    '''
    Perform floorplanning and initial pin placements
    '''
    def __init__(self):
        super().__init__()

        self.add_parameter("ifp_snap_strategy", "<none,site,grid>",
                           "Snapping strategy to use when placing macros.", defvalue="site")
        self.add_parameter("remove_synth_buffers", "bool",
                           "remove buffers inserted by synthesis", defvalue=True)
        self.add_parameter("remove_dead_logic", "bool",
                           "remove logic which does not drive a primary output", defvalue=True)

        self.add_parameter("padringfileset", "[str]", "filesets to generate a padring")

    def task(self):
        return "init_floorplan"

    def setup(self):
        super().setup()

        self.set_script("apr/sc_init_floorplan.tcl")

        # if chip.valid('input', 'asic', 'floorplan') and \
        #    chip.get('input', 'asic', 'floorplan', step=step, index=index):
        #     chip.add('tool', tool, 'task', task, 'require',
        #              ",".join(['input', 'asic', 'floorplan']),
        #              step=step, index=index)

        # if f'{design}.vg' in input_provides(chip, step, index):
        #     chip.add('tool', tool, 'task', task, 'input', f'{design}.vg',
        #              step=step, index=index)
        # else:
        #     chip.add('tool', tool, 'task', task, 'require', 'input,netlist,verilog',
        #              step=step, index=index)
        if f"{self.design_topmodule}.vg" in self.get_files_from_input_nodes():
            self.add_input_file(ext="vg")
        else:
            pass

        self._set_reports([
            'check_setup',
            'setup',
            'unconstrained',
            'power'
        ])

        self.add_required_key("var", "ifp_snap_strategy")
        self.add_required_key("var", "remove_synth_buffers")
        self.add_required_key("var", "remove_dead_logic")

        if self.get("var", "padringfileset"):
            self.add_required_key("var", "padringfileset")

            for fileset in self.get("var", "padringfileset"):
                self.add_required_key(self.project.design, "fileset", fileset, "file", "tcl")

    def add_openroad_padringfileset(self, fileset: str, clobber=False):
        if clobber:
            self.set("var", "padringfileset", fileset)
        else:
            self.add("var", "padringfileset", fileset)
