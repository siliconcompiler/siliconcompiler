#!/usr/bin/env python3
# Copyright 2025 Silicon Compiler Authors. All Rights Reserved.

from pathlib import Path

from siliconcompiler import DesignSchema
from siliconcompiler.project import LintProject, ASICProject

from siliconcompiler.flows.lintflow import LintFlowgraph
from siliconcompiler.flows.synflow import SynthesisFlowgraph
from lambdapdk import __version__ as lambda_version
from siliconcompiler.package import PythonPathResolver

from siliconcompiler.library import StdCellLibrarySchema

from siliconcompiler import PDKSchema
from siliconcompiler.dependencyschema import DependencySchema

from siliconcompiler.tools.yosys.syn_asic import YosysStdCellLibrarySchema
from siliconcompiler.tools.openroad import OpenROADStdCellLibrarySchema
from siliconcompiler.tools.bambu import BambuStdCellLibrarySchema


class FreePDK45(PDKSchema, DependencySchema):
    def __init__(self):
        super().__init__()
        self.set_name("freepdk45")

        PythonPathResolver.set_dataroot(
            self,
            "lambdapdk",
            "lambdapdk",
            "https://github.com/siliconcompiler/lambdapdk/archive/refs/tags/",
            alternative_ref=f"v{lambda_version}",
            python_module_path_append=".."
        )


class ASAP7SC7p5Base(YosysStdCellLibrarySchema,
                     OpenROADStdCellLibrarySchema,
                     BambuStdCellLibrarySchema,
                     StdCellLibrarySchema):
    def __init__(self, vt, suffix):
        super().__init__()
        self.set_name(f"asap7sc7p5t_{vt}")

        PythonPathResolver.set_dataroot(
            self,
            "lambdapdk",
            "lambdapdk",
            "https://github.com/siliconcompiler/lambdapdk/archive/refs/tags/",
            alternative_ref=f"v{lambda_version}",
            python_module_path_append=".."
        )

        # # version
        # lib.set("package", "version", version)

        # site name
        self.add_asic_site('asap7sc7p5t')

        # tie cells
        self.add_asic_cell_list('tie', [f"TIEHIx1_ASAP7_75t_{suffix}",
                                        f"TIELOx1_ASAP7_75t_{suffix}"])

        # filler
        self.add_asic_cell_list('filler', [f"FILLER_ASAP7_75t_{suffix}",
                                           f"FILLERxp5_ASAP7_75t_{suffix}"])

        # decap
        self.add_asic_cell_list('decap', [f"DECAPx1_ASAP7_75t_{suffix}",
                                          f"DECAPx2_ASAP7_75t_{suffix}",
                                          f"DECAPx4_ASAP7_75t_{suffix}",
                                          f"DECAPx6_ASAP7_75t_{suffix}",
                                          f"DECAPx10_ASAP7_75t_{suffix}"])

        # Stupid small cells
        self.add_asic_cell_list('dontuse', ["*x1p*_ASAP7*",
                                            "*xp*_ASAP7*",
                                            "SDF*",
                                            "ICG*"])

        # Tapcell
        self.add_asic_cell_list('tap', f"TAPCELL_ASAP7_75t_{suffix}")

        # Endcap
        self.add_asic_cell_list('endcap', f"DECAPx1_ASAP7_75t_{suffix}")

        lib_path = Path("lambdapdk", "asap7", "libs", f"asap7sc7p5t_{vt}")

        # General filelists
        with self.active_dataroot("lambdapdk"):
            for corner_name, lib_corner in [
                    ('typical', 'TT'),
                    ('fast', 'FF'),
                    ('slow', 'SS')]:

                with self.active_fileset(f"models.timing.{corner_name}.nldm"):
                    for lib_type in ('AO', 'INVBUF', 'OA', 'SEQ', 'SIMPLE'):
                        self.add_file(lib_path / "nldm" / f"asap7sc7p5t_{lib_type}_{suffix}VT_{lib_corner}_nldm.lib.gz")

                    self.add_asic_corner_fileset(corner_name)

            with self.active_fileset("models.spice"):
                self.add_file(lib_path / "netlist" / f"asap7sc7p5t_28_{suffix}.sp")

            with self.active_fileset("models.physical"):
                self.add_file(lib_path / "lef" / f"asap7sc7p5t_28_{suffix}.lef")
                self.add_file(lib_path / "gds" / f"asap7sc7p5t_28_{suffix}.gds.gz")

            with self.active_fileset("models.lvs"):
                self.add_file(lib_path / "netlist" / f"asap7sc7p5t_28_{suffix}.cdl")

        # Setup for yosys
        with self.active_dataroot("lambdapdk"):
            self.set_yosys_driver_cell(f"BUFx2_ASAP7_75t_{suffix}")
            self.set_yosys_buffer_cell(f"BUFx2_ASAP7_75t_{suffix}", "A", "Y")
            self.set_yosys_tielow_cell(f"TIELOx1_ASAP7_75t_{suffix}", "L")
            self.set_yosys_tiehigh_cell(f"TIEHIx1_ASAP7_75t_{suffix}", "H")

            cap_table = {  # BUFx2_ASAP7_75t_, fF
                'R': "2.308",
                'L': "2.383",
                'SL': "2.464"
            }
            self.set_yosys_abc(1, cap_table[suffix])
            self.set_yosys_adder_map(lib_path / "techmap" / "yosys" / "cells_adders.v")
            self.add_yosys_tech_map(lib_path / "techmap" / "yosys" / "cells_latch.v")

        # Setup for openroad
        with self.active_dataroot("lambdapdk"):
            self.set_openroad_placement_density(0.60)
            self.set_openroad_tielow_cell(f"TIELOx1_ASAP7_75t_{suffix}", "L")
            self.set_openroad_tiehigh_cell(f"TIEHIx1_ASAP7_75t_{suffix}", "H")
            self.set_openroad_macro_placement_halo(5, 5)
            self.set_openroad_tracks_file(lib_path / "apr" / "openroad" / "tracks.tcl")
            self.set_openroad_tapcells_file(lib_path / "apr" / "openroad" / "tapcells.tcl")
            self.add_openroad_global_connect_file(lib_path / "apr" / "openroad" / "global_connect.tcl")
            self.add_openroad_power_grid_file(lib_path / "apr" / "openroad" / "pdngen.tcl")

        # Setup for bambu
        self.set_bambu_device_name("asap7-WC")
        self.set_bambu_clock_multiplier(0.001)


class ASAP7SC7p5RVT(ASAP7SC7p5Base):
    def __init__(self):
        ASAP7SC7p5Base.__init__(self, "rvt", "R")


class ASAP7SC7p5LVT(ASAP7SC7p5Base):
    def __init__(self):
        ASAP7SC7p5Base.__init__(self, "lvt", "L")


class ASAP7SC7p5SLVT(ASAP7SC7p5Base):
    def __init__(self):
        ASAP7SC7p5Base.__init__(self, "slvt", "SL")


class Nangate45(YosysStdCellLibrarySchema,
                OpenROADStdCellLibrarySchema,
                BambuStdCellLibrarySchema,
                StdCellLibrarySchema):
    def __init__(self):
        super().__init__()
        self.set_name("nangate45")

        PythonPathResolver.set_dataroot(
            self,
            "lambdapdk",
            "lambdapdk",
            "https://github.com/siliconcompiler/lambdapdk/archive/refs/tags/",
            alternative_ref=f"v{lambda_version}",
            python_module_path_append=".."
        )

        # # version
        # lib.set("package", "version", version)

        self.add_asic_site("FreePDK45_38x28_10R_NP_162NW_34O")

        # clock buffers
        self.add_asic_cell_list("clkbuf", ["CLKBUF_X1",
                                           "CLKBUF_X2",
                                           "CLKBUF_X3"])

        # tie cells
        self.add_asic_cell_list("tie", ["LOGIC0_X1",
                                        "LOGIC1_X1"])

        # filler
        self.add_asic_cell_list("filler", ["FILLCELL_X1",
                                           "FILLCELL_X2",
                                           "FILLCELL_X4",
                                           "FILLCELL_X8",
                                           "FILLCELL_X16",
                                           "FILLCELL_X32"])

        # Dont use for synthesis
        self.add_asic_cell_list("dontuse", "OAI211_X1")

        # Tapcell
        self.add_asic_cell_list("tap", "TAPCELL_X1")

        # Endcap
        self.add_asic_cell_list("endcap", "TAPCELL_X1")

        lib_path = Path("lambdapdk", "freepdk45", "libs", "nangate45")

        # General filelists
        with self.active_dataroot("lambdapdk"):
            with self.active_fileset("models.timing.nldm"):
                self.add_file(lib_path / "nldm" / "NangateOpenCellLibrary_typical.lib")
                self.add_asic_corner_fileset("typical")

            with self.active_fileset("models.physical"):
                self.add_file(lib_path / "lef" / "NangateOpenCellLibrary.macro.mod.lef")
                self.add_file(lib_path / "gds" / "NangateOpenCellLibrary.gds")

            with self.active_fileset("models.lvs"):
                self.add_file(lib_path / "cdl" / "NangateOpenCellLibrary.cdl")

        # Setup for yosys
        with self.active_dataroot("lambdapdk"):
            self.set_yosys_driver_cell("BUF_X4")
            self.set_yosys_buffer_cell("BUF_X1", "A", "Z")
            self.set_yosys_tielow_cell("LOGIC0_X1", "Z")
            self.set_yosys_tiehigh_cell("LOGIC1_X1", "Z")
            self.set_yosys_abc(1000, 3.899)
            self.set_yosys_tristatebuffer_map(lib_path / "techmap" / "yosys" / "cells_tristatebuf.v")
            self.set_yosys_adder_map(lib_path / "techmap" / "yosys" / "cells_adders.v")
            self.add_yosys_tech_map(lib_path / "techmap" / "yosys" / "cells_latch.v")

        # Setup for openroad
        with self.active_dataroot("lambdapdk"):
            self.set_openroad_placement_density(0.50)
            self.set_openroad_tielow_cell("LOGIC0_X1", "Z")
            self.set_openroad_tiehigh_cell("LOGIC1_X1", "Z")
            self.set_openroad_macro_placement_halo(22.4, 15.12)
            self.set_openroad_tapcells_file(lib_path / "apr" / "openroad" / "tapcell.tcl")
            self.add_openroad_global_connect_file(lib_path / "apr" / "openroad" / "global_connect.tcl")
            self.add_openroad_power_grid_file(lib_path / "apr" / "openroad" / "pdngen.tcl")

        # Setup for bambu
        self.set_bambu_device_name("nangate45")
        self.set_bambu_clock_multiplier(1)


class GCDDesign(DesignSchema):
    def __init__(self):
        super().__init__()
        self.set_name("gcd")

        self.set_dataroot("gcd-example", __file__)

        with self.active_dataroot("gcd-example"):
            with self.active_fileset("rtl"):
                self.set_topmodule("gcd")
                self.add_file("gcd.v")

            with self.active_fileset("rtl.freepdk45"):
                self.add_file("gcd_freepdk45.sdc")

            with self.active_fileset("rtl.asap7"):
                self.add_file("gcd_asap7.sdc")


def lint():
    project = LintProject()

    gcd = GCDDesign()

    project.set_design(gcd)
    project.add_fileset("rtl")
    project.set_flow(LintFlowgraph())

    project.run(raise_exception=True)


def syn():
    project = ASICProject()

    gcd = GCDDesign()

    project.set_design(gcd)
    project.add_fileset("rtl")
    project.add_fileset("rtl.freepdk45")
    project.set_flow(SynthesisFlowgraph())

    # project.add_logiclib(Nangate45())
    project.add_logiclib(ASAP7SC7p5RVT())
    project.add_logiclib(ASAP7SC7p5LVT())
    project.add_logiclib(ASAP7SC7p5SLVT())

    project.get_task("yosys", "syn_asic").add_synthesis_corner("slow")

    project.run(raise_exception=True)


def check():
    assert GCDDesign().check_filepaths()
    assert Nangate45().check_filepaths()
    assert ASAP7SC7p5RVT().check_filepaths()
    assert ASAP7SC7p5LVT().check_filepaths()
    assert ASAP7SC7p5SLVT().check_filepaths()


if __name__ == "__main__":
    syn()
