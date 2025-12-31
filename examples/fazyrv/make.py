from siliconcompiler import Design, ASIC
from siliconcompiler.targets import freepdk45_demo
from lambdalib.ramlib import Spram

from siliconcompiler.optimizer import Optimizer, ResultOptimizer
from siliconcompiler.tools.yosys.syn_asic import ASICSynthesis
from siliconcompiler.tools.openroad.macro_placement import MacroPlacementTask


class FazyRV(Design):
    """
    Design configuration for the FazyRV RISC-V core.
    """
    def __init__(self):
        super().__init__("fazyrv")
        # Set up data roots. 'local' is for files in this directory,
        # 'fazyrv' is for the remote repository.
        self.set_dataroot("local", __file__)
        self.set_dataroot("fazyrv",
                          'https://github.com/meiniKi/FazyRV/archive/',
                          tag='f287cf56b06ed20ead2d1dd0aab0c64ee50c5133')

        # Configure source files from the remote 'fazyrv' root.
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
                # Set design-specific parameters.
                self.set_param("RFTYPE", '"BRAM"')
                self.set_param("CONF", '"MIN"')
                self.set_param("CHUNKSIZE", '8')
                self.add_define("SYNTHESIS")

        # Configure local files (wrappers and constraints).
        with self.active_dataroot("local"):
            with self.active_fileset("rtl"):
                self.add_file("lambdalib.sv")
                # Add memory library dependency.
                self.add_depfileset(Spram(), "rtl")
            with self.active_fileset("sdc"):
                self.add_file("fazyrv.sdc")


def _create_project() -> ASIC:    # --- Project Setup ---
    """
    Helper function to create and configure the ASIC project.
    """
    # Create an ASIC project from the design configuration.
    project = ASIC(FazyRV())

    # Tell the project which filesets are needed for the compilation flow.
    project.add_fileset(["rtl", "sdc"])

    # Load the pre-defined target for the FreePDK45 demo process.
    # This configures the project with the correct PDK, standard cell libraries,
    # and tool flow for this technology.
    freepdk45_demo(project)

    # Enable 'slang' frontend in Yosys for better SystemVerilog support.
    ASICSynthesis.find_task(project).set_yosys_useslang(True)
    # Configure macro placement halo in OpenROAD.
    MacroPlacementTask.find_task(project).set("var", "macro_place_halo", [10, 10])

    return project


def optimize(count: int = 5):
    """
    Runs hyperparameter optimization on the design.
    """
    project = _create_project()

    opt = Optimizer(project)
    # Add parameters to sweep.
    opt.add_parameter("tool", "openroad", "task", "global_placement", "var", "place_density")
    opt.add_parameter("tool", "openroad", "task", "global_placement", "var", "gpl_routability_driven")
    opt.add_parameter("tool", "openroad", "task", "global_placement", "var", "gpl_timing_driven")

    opt.add_goal("metric", "totalarea", goal="min", step="floorplan.init", index="0")
    opt.add_goal("metric", "setupslack", goal="max", step="place.detailed", index="0")
    opt.add_goal("metric", "setuptns", goal="min", step="place.detailed", index="0")
    opt.add_goal("metric", "peakpower", goal="min", step="place.detailed", index="0")

    # Run experiments and save results.
    opt.run(experiments=count)
    opt.report()
    opt.write("optimize.json")


def reuse(idx: int = 0):
    """
    Reuses a specific configuration from a previous optimization run.
    """
    project = _create_project()
    # Load optimization results and apply the configuration for the given index.
    ResultOptimizer.load("optimize.json").use(project, result=idx)
    project.run()
    project.summary()
