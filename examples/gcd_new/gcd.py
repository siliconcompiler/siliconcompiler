#!/usr/bin/env python3
# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

import os
import siliconcompiler

from pathlib import Path

from siliconcompiler.targets import freepdk45_demo

from siliconcompiler import DesignSchema
from siliconcompiler.project import LintProject
from siliconcompiler.schema import EditableSchema\

from siliconcompiler.flows.lintflow import LintFlowgraph, slang_lint
from siliconcompiler.flows.synflow import SynthesisFlowgraph, elaborate
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

        PythonPathResolver.register_source(
            self,
            "lambdapdk",
            "lambdapdk",
            "https://github.com/siliconcompiler/lambdapdk/archive/refs/tags/",
            alternative_ref=f"v{lambda_version}",
            python_module_path_append=".."
        )


class Nangate45(YosysStdCellLibrarySchema,
                OpenROADStdCellLibrarySchema,
                BambuStdCellLibrarySchema,
                StdCellLibrarySchema):
    def __init__(self):
        super().__init__()
        self.set_name("nangate45")

        PythonPathResolver.register_package(
            self,
            "lambdapdk",
            "lambdapdk",
            "https://github.com/siliconcompiler/lambdapdk/archive/refs/tags/",
            alternative_ref=f"v{lambda_version}",
            python_module_path_append=".."
        )

        # # version
        # lib.set("package", "version", version)

        # # list of stackups supported
        # lib.set("option", "stackup", stackup)

        # # list of pdks supported
        # lib.set("option", "pdk", process)

        # # footprint" / "type" / "sites
        # lib.set("asic", "libarch", libtype)
        # lib.set("asic", "site", libtype, "FreePDK45_38x28_10R_NP_162NW_34O")

        # clock buffers
        self.add_cell_list("clkbuf", ["CLKBUF_X1",
                                      "CLKBUF_X2",
                                      "CLKBUF_X3"])

        # tie cells
        self.add_cell_list("tie", ["LOGIC0_X1",
                                   "LOGIC1_X1"])

        # filler
        self.add_cell_list("filler", ["FILLCELL_X1",
                                      "FILLCELL_X2",
                                      "FILLCELL_X4",
                                      "FILLCELL_X8",
                                      "FILLCELL_X16",
                                      "FILLCELL_X32"])

        # Dont use for synthesis
        self.add_cell_list("dontuse", "OAI211_X1")

        # Tapcell
        self.add_cell_list("tap", "TAPCELL_X1")

        # Endcap
        self.add_cell_list("endcap", "TAPCELL_X1")

        lib_path = Path("lambdapdk", "freepdk45", "libs", "nangate45")

        # General filelists
        with self.active(package="lambdapdk"):
            with self.active_fileset("models.timing.nldm"):
                self.add_file(lib_path / "nldm" / "NangateOpenCellLibrary_typical.lib")
            self.add_timing_fileset("typical", "models.timing.nldm")

            with self.active_fileset("models.physical"):
                self.add_file(lib_path / "lef" / "NangateOpenCellLibrary.macro.mod.lef")
                self.add_file(lib_path / "gds" / "NangateOpenCellLibrary.gds")

            with self.active_fileset("models.lvs"):
                self.add_file(lib_path / "cdl" / "NangateOpenCellLibrary.cdl")

        # Setup for yosys
        with self.active(package="lambdapdk"):
            self.set_yosys_driver_cell("BUF_X4")
            self.set_yosys_buffer_cell("BUF_X1", "A", "Z")
            self.set_yosys_tielow_cell("LOGIC0_X1", "Z")
            self.set_yosys_tiehigh_cell("LOGIC1_X1", "Z")
            self.set_yosys_abc(1000, 3.899)
            self.set_yosys_tristatebuffer_map(lib_path / "techmap" / "yosys" / "cells_tristatebuf.v")
            self.set_yosys_adder_map(lib_path / "techmap" / "yosys" / "cells_adders.v")
            self.add_yosys_tech_map(lib_path / "techmap" / "yosys" / "cells_latch.v")

        # Setup for openroad
        with self.active(package="lambdapdk"):
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

        self.register_package("gcd-example", __file__)

        with self.active(package="gcd-example"):
            with self.active_fileset("rtl"):
                self.set_topmodule("gcd")
                self.add_file("gcd.v")

            with self.active_fileset("rtl.freepdk45"):
                self.add_file("gcd_freepdk45.sdc")

            with self.active_fileset("rtl.asap7"):
                self.add_file("gcd_asap7.sdc")


def main():
    project = LintProject()
    project.add_dep(GCDDesign())
    project.add_dep(Nangate45())
    project.add_dep(LintFlowgraph())
    project.add_dep(SynthesisFlowgraph())
    project.write_manifest("test.json")

    project.set("option", "flow", "synflow")
    project.set("tool", "yosys", "task", "syn_asic", "var", "synthesis_corner", "typical")

    project.run(raise_exception=True)


if __name__ == "__main__":
    main()
