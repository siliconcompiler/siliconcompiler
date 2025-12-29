from siliconcompiler import Design, ASIC
from siliconcompiler.targets import freepdk45_demo
from lambdalib.ramlib import Spram

from siliconcompiler.optimizer import Optimizer, ResultOptimizer
from siliconcompiler.tools.yosys.syn_asic import ASICSynthesis
from siliconcompiler.tools.openroad.macro_placement import MacroPlacementTask


class FazyRV(Design):
    def __init__(self):
        super().__init__("fazyrv")
        self.set_dataroot("local", __file__)
        self.set_dataroot("fazyrv",
                          'https://github.com/meiniKi/FazyRV/archive/',
                          tag='f287cf56b06ed20ead2d1dd0aab0c64ee50c5133')

        with self.active_dataroot("fazyrv"):
            with self.active_fileset("rtl"):
                self.set_topmodule("fsoc")
                self.add_file([
                    'rtl/fazyrv_hadd.v',
                    'rtl/fazyrv_fadd.v',
                    'rtl/fazyrv_cmp.v',
                    'rtl/fazyrv_alu.sv',
                    'rtl/fazyrv_decode.sv',
                    'rtl/fazyrv_decode_mem1.sv',
                    'rtl/fazyrv_shftreg.sv',
                    'rtl/fazyrv_csr.sv',
                    'rtl/fazyrv_rf_lut.sv',
                    'rtl/fazyrv_rf.sv',
                    'rtl/fazyrv_pc.sv',
                    'rtl/fazyrv_cntrl.sv',
                    'rtl/fazyrv_spm_a.sv',
                    'rtl/fazyrv_spm_d.sv',
                    'rtl/fazyrv_core.sv',
                    'rtl/fazyrv_top.sv',
                    'soc/rtl/gpio.sv',
                    'soc/rtl/fsoc.sv'])
                self.set_param("RFTYPE", '"BRAM"')
                self.set_param("CONF", '"MIN"')
                self.set_param("CHUNKSIZE", '8')
                self.add_define("SYNTHESIS")

        with self.active_dataroot("local"):
            with self.active_fileset("rtl"):
                self.add_file("lambdalib.sv")
                self.add_depfileset(Spram(), "rtl")
            with self.active_fileset("sdc"):
                self.add_file("fazyrv.sdc")


def _create_project() -> ASIC:    # --- Project Setup ---
    # Create an ASIC project from the design configuration.
    project = ASIC(FazyRV())

    # Tell the project which filesets are needed for the compilation flow.
    project.add_fileset(["rtl", "sdc"])

    # Load the pre-defined target for the FreePDK45 demo process.
    # This configures the project with the correct PDK, standard cell libraries,
    # and tool flow for this technology.
    freepdk45_demo(project)

    ASICSynthesis.find_task(project).set_yosys_useslang(True)
    MacroPlacementTask.find_task(project).set("var", "macro_place_halo", [10, 10])

    return project


def optimize(count: int = 5):
    project = _create_project()

    opt = Optimizer(project)
    opt.add_parameter("tool", "openroad", "task", "global_placement", "var", "place_density")
    opt.add_parameter("tool", "openroad", "task", "global_placement", "var", "gpl_routability_driven")
    opt.add_parameter("tool", "openroad", "task", "global_placement", "var", "gpl_timing_driven")

    opt.add_goal("metric", "totalarea", goal="min", step="floorplan.init", index="0")
    opt.add_goal("metric", "setupslack", goal="max", step="place.detailed", index="0")
    opt.add_goal("metric", "setuptns", goal="min", step="place.detailed", index="0")
    opt.add_goal("metric", "peakpower", goal="min", step="place.detailed", index="0")
    opt.run(experiments=count)
    opt.report()
    opt.write("optimize.json")


def reuse(idx: int = 0):
    project = _create_project()
    ResultOptimizer.load("optimize.json").use(project, result=idx)
    project.run()
    project.summary()
