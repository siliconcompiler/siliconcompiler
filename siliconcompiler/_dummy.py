#!/usr/bin/env python3
# Copyright 2025 Silicon Compiler Authors. All Rights Reserved.

from pathlib import Path
from typing import final

from lambdapdk import __version__ as lambda_version
from siliconcompiler.package import PythonPathResolver
from siliconcompiler.schema import EditableSchema, Parameter, Scope, PerNode

from siliconcompiler.library import StdCellLibrarySchema

from siliconcompiler import PDKSchema, DesignSchema

from siliconcompiler.tools.yosys.syn_asic import YosysStdCellLibrarySchema
from siliconcompiler.tools.openroad import OpenROADStdCellLibrarySchema, OpenROADPDK
from siliconcompiler.tools.bambu import BambuStdCellLibrarySchema


class Spram(DesignSchema):
    def __init__(self):
        super().__init__()
        self.set_name("la_spram")

        self.set_dataroot("lambdalib", "python://lambdalib")

        with self.active_dataroot("lambdalib"):
            with self.active_fileset("rtl"):
                self.set_topmodule("la_spram")
                self.add_file("ramlib/rtl/la_spram.v")
                self.add_file("ramlib/rtl/la_spram_impl.v")


class FreePDK45(OpenROADPDK, PDKSchema):
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

        pdk_path = Path("lambdapdk", "freepdk45", "base")

        self.set_foundry("virtual")
        self.set_version("r1p0")
        self.set_node(45)
        self.set_stackup("10M")
        self.set_wafersize(300)
        self.set_scribewidth(0.1, 0.1)
        self.set_edgemargin(2)
        self.set_defectdensity(1.25)

        with self.active_dataroot("lambdapdk"):
            # APR Setup
            with self.active_fileset("views.lef"):
                self.add_file(pdk_path / "apr" / "freepdk45.tech.lef")
                for tool in ('openroad', 'klayout', 'magic'):
                    self.add_apr_techfileset(tool)

            self.set_apr_routinglayers(min="metal2", max="metal7")

            # Klayout setup file
            with self.active_fileset("klayout.techmap"):
                self.add_file(pdk_path / "setup" / "klayout" / "freepdk45.lyt", filetype="layermap")
                self.add_file(pdk_path / "setup" / "klayout" / "freepdk45.lyp", filetype="diplay")
                self.set("pdk", "layermapfileset", "klayout", "def", "klayout", "klayout.techmap")
                self.set("pdk", "displayfileset", "klayout", "klayout.techmap")

            self.set_openroad_rclayers(signal="metal3", clock="metal5")

            # Openroad global routing grid derating
            for layer, detate in [
                    ('metal1', 1.0),
                    ('metal2', 0.5),
                    ('metal3', 0.5),
                    ('metal4', 0.25),
                    ('metal5', 0.25),
                    ('metal6', 0.25),
                    ('metal7', 0.25),
                    ('metal8', 0.25),
                    ('metal9', 0.25),
                    ('metal10', 0.25)]:
                self.set_openroad_globalroutingdetating(layer, detate)

            self.add_openroad_pinlayers(veritcal="metal6", horizontal="metal5")

            # PEX
            with self.active_fileset("openroad.pex"):
                self.add_file(pdk_path / "pex" / "openroad" / "typical.tcl", filetype="tcl")
                self.add_file(pdk_path / "pex" / "openroad" / "typical.rules", filetype="openrcx")

                self.set("pdk", "pexmodelfileset", "openroad", "typical", "openroad.pex")
                self.set("pdk", "pexmodelfileset", "openroad-openrcx", "typical", "openroad.pex")

    @final
    def define_tool_parameter(self, tool: str, name: str, type: str, help: str, **kwargs):
        """
        Define a new tool parameter for the library

        Args:
            tool (str): name of the tool
            name (str): name of the parameter
            type (str): type of parameter, see :class:`.Parameter`.
            help (str): help information for this parameter
            kwargs: passthrough for :class:`.Parameter`.
        """
        if isinstance(help, str):
            # grab first line for short help
            shorthelp = help.splitlines()[0].strip()
        else:
            raise TypeError("help must be a string")

        kwargs["scope"] = Scope.GLOBAL
        kwargs["pernode"] = PerNode.NEVER
        kwargs["shorthelp"] = shorthelp
        kwargs["help"] = help

        EditableSchema(self).insert(
            "tool", tool, name,
            Parameter(type, **kwargs)
        )


class ASAP7(OpenROADPDK, PDKSchema):
    def __init__(self):
        super().__init__()
        self.set_name("asap7")

        PythonPathResolver.set_dataroot(
            self,
            "lambdapdk",
            "lambdapdk",
            "https://github.com/siliconcompiler/lambdapdk/archive/refs/tags/",
            alternative_ref=f"v{lambda_version}",
            python_module_path_append=".."
        )

        pdk_path = Path("lambdapdk", "asap7", "base")

        self.set_foundry("virtual")
        self.set_version("r1p7")
        self.set_node(7)
        self.set_stackup("10M")
        self.set_wafersize(300)
        self.set_scribewidth(0.1, 0.1)
        self.set_edgemargin(2)
        self.set_defectdensity(1.25)

        with self.active_dataroot("lambdapdk"):
            # APR Setup
            with self.active_fileset("views.lef"):
                self.add_file(pdk_path / "apr" / "asap7_tech.lef")
                for tool in ('openroad', 'klayout', 'magic'):
                    self.add_apr_techfileset(tool)

            self.set_apr_routinglayers(min="M2", max="M7")

            with self.active_fileset("layermap"):
                self.add_file(pdk_path / "apr" / "asap7.layermap", filetype="layermap")

            # Klayout setup file
            with self.active_fileset("klayout.techmap"):
                self.add_file(pdk_path / "setup" / "klayout" / "asap7.lyt", filetype="layermap")
                self.add_file(pdk_path / "setup" / "klayout" / "asap7.lyp", filetype="display")
                self.set("pdk", "layermapfileset", "klayout", "def", "klayout", "klayout.techmap")
                self.set("pdk", "displayfileset", "klayout", "klayout.techmap")
            self.set("pdk", "layermapfileset", "klayout", "def", "gds", "layermap")

            self.set_openroad_rclayers(signal="M3", clock="M3")

            # Openroad global routing grid derating
            for layer, detate in [
                    ('M1', 0.25),
                    ('M2', 0.25),
                    ('M3', 0.25),
                    ('M4', 0.25),
                    ('M5', 0.25),
                    ('M6', 0.25),
                    ('M7', 0.25),
                    ('M8', 0.25),
                    ('M9', 0.25),
                    ('Pad', 0.25)]:
                self.set_openroad_globalroutingdetating(layer, detate)

            self.add_openroad_pinlayers(veritcal="M5", horizontal="M4")

            # # Relaxed routing rules
            # pdk.set('pdk', process, 'file', 'openroad', 'relax_routing_rules', stackup,
            #         pdkdir + '/apr/openroad_relaxed_rules.tcl')

            # # PEX
            with self.active_fileset("openroad.pex"):
                self.add_file(pdk_path / "pex" / "openroad" / "typical.tcl", filetype="tcl")
                self.add_file(pdk_path / "pex" / "openroad" / "typical.rules", filetype="openrcx")

                self.set("pdk", "pexmodelfileset", "openroad", "typical", "openroad.pex")
                self.set("pdk", "pexmodelfileset", "openroad-openrcx", "typical", "openroad.pex")


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

        # version
        self.set_version("28")

        # PDK
        self.set_asic_pdk(ASAP7())

        # site name
        self.add_asic_site('asap7sc7p5t')

        # tie cells
        self.add_asic_celllist('tie', [f"TIEHIx1_ASAP7_75t_{suffix}",
                                       f"TIELOx1_ASAP7_75t_{suffix}"])

        # filler
        self.add_asic_celllist('filler', [f"FILLER_ASAP7_75t_{suffix}",
                                          f"FILLERxp5_ASAP7_75t_{suffix}"])

        # decap
        self.add_asic_celllist('decap', [f"DECAPx1_ASAP7_75t_{suffix}",
                                         f"DECAPx2_ASAP7_75t_{suffix}",
                                         f"DECAPx4_ASAP7_75t_{suffix}",
                                         f"DECAPx6_ASAP7_75t_{suffix}",
                                         f"DECAPx10_ASAP7_75t_{suffix}"])

        # Stupid small cells
        self.add_asic_celllist('dontuse', ["*x1p*_ASAP7*",
                                           "*xp*_ASAP7*",
                                           "SDF*",
                                           "ICG*"])

        # Tapcell
        self.add_asic_celllist('tap', f"TAPCELL_ASAP7_75t_{suffix}")

        # Endcap
        self.add_asic_celllist('endcap', f"DECAPx1_ASAP7_75t_{suffix}")

        lib_path = Path("lambdapdk", "asap7", "libs", f"asap7sc7p5t_{vt}")

        # General filelists
        with self.active_dataroot("lambdapdk"):
            for corner_name, lib_corner in [
                    ('typical', 'TT'),
                    ('fast', 'FF'),
                    ('slow', 'SS')]:

                for lib_type in ('AO', 'INVBUF', 'OA', 'SEQ', 'SIMPLE'):
                    with self.active_fileset(f"models.timing.{corner_name}.nldm.{lib_type.lower()}"):
                        self.add_file(lib_path / "nldm" / f"asap7sc7p5t_{lib_type}_{suffix}VT_{lib_corner}_nldm.lib.gz")
                        self.add_asic_libcornerfileset(corner_name, "nldm")

            with self.active_fileset("models.spice"):
                self.add_file(lib_path / "netlist" / f"asap7sc7p5t_28_{suffix}.sp")

            with self.active_fileset("models.physical"):
                self.add_file(lib_path / "lef" / f"asap7sc7p5t_28_{suffix}.lef")
                self.add_file(lib_path / "gds" / f"asap7sc7p5t_28_{suffix}.gds.gz")
                self.add_asic_aprfileset()

            with self.active_fileset("models.lvs"):
                self.add_file(lib_path / "netlist" / f"asap7sc7p5t_28_{suffix}.cdl")
                self.add_asic_aprfileset()

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

        # version
        self.set_version("r1p0")

        self.set_asic_pdk(FreePDK45())

        self.add_asic_site("FreePDK45_38x28_10R_NP_162NW_34O")

        # clock buffers
        self.add_asic_celllist("clkbuf", ["CLKBUF_X1",
                                          "CLKBUF_X2",
                                          "CLKBUF_X3"])

        # tie cells
        self.add_asic_celllist("tie", ["LOGIC0_X1",
                                       "LOGIC1_X1"])

        # filler
        self.add_asic_celllist("filler", ["FILLCELL_X1",
                                          "FILLCELL_X2",
                                          "FILLCELL_X4",
                                          "FILLCELL_X8",
                                          "FILLCELL_X16",
                                          "FILLCELL_X32"])

        # Dont use for synthesis
        self.add_asic_celllist("dontuse", "OAI211_X1")

        # Tapcell
        self.add_asic_celllist("tap", "TAPCELL_X1")

        # Endcap
        self.add_asic_celllist("endcap", "TAPCELL_X1")

        lib_path = Path("lambdapdk", "freepdk45", "libs", "nangate45")

        # General filelists
        with self.active_dataroot("lambdapdk"):
            with self.active_fileset("models.timing.nldm"):
                self.add_file(lib_path / "nldm" / "NangateOpenCellLibrary_typical.lib")
                self.add_asic_libcornerfileset("typical", "nldm")

            with self.active_fileset("models.physical"):
                self.add_file(lib_path / "lef" / "NangateOpenCellLibrary.macro.mod.lef")
                self.add_file(lib_path / "gds" / "NangateOpenCellLibrary.gds")
                self.add_asic_aprfileset()

            with self.active_fileset("models.lvs"):
                self.add_file(lib_path / "cdl" / "NangateOpenCellLibrary.cdl")
                self.add_asic_aprfileset()

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


class FakeRam45(StdCellLibrarySchema):
    def __init__(self):
        super().__init__()
        self.set_name("fakeram45")

        PythonPathResolver.set_dataroot(
            self,
            "lambdapdk",
            "lambdapdk",
            "https://github.com/siliconcompiler/lambdapdk/archive/refs/tags/",
            alternative_ref=f"v{lambda_version}",
            python_module_path_append=".."
        )

        # version
        self.set_version("v1")

        lib_path = Path("lambdapdk", "freepdk45", "libs", "fakeram45")

        # General filelists
        for config in ('64x32', '128x32', '256x32', '256x64', '512x32', '512x64'):
            mem_name = f'fakeram45_{config}'

            with self.active_dataroot("lambdapdk"):
                with self.active_fileset("models.timing.nldm"):
                    self.add_file(lib_path / "nldm" / f"{mem_name}.lib")
                    self.add_asic_libcornerfileset("typical", "nldm")

                with self.active_fileset("models.physical"):
                    self.add_file(lib_path / "lef" / f"{mem_name}.lef")
                    self.add_asic_aprfileset()


class FakeRam45Lambdalib(DesignSchema):
    def __init__(self):
        super().__init__()
        self.set_name("fakeram45_lambdaramlib")

        PythonPathResolver.set_dataroot(
            self,
            "lambdapdk",
            "lambdapdk",
            "https://github.com/siliconcompiler/lambdapdk/archive/refs/tags/",
            alternative_ref=f"v{lambda_version}",
            python_module_path_append=".."
        )

        # version
        self.set_version("v1")

        lib_path = Path("lambdapdk", "freepdk45", "libs", "fakeram45")

        with self.active_dataroot("lambdapdk"):
            with self.active_fileset("rtl"):
                self.add_file(lib_path / "lambda" / "la_spram.v")


class FakeRam7(StdCellLibrarySchema):
    def __init__(self):
        super().__init__()
        self.set_name("fakeram7")

        PythonPathResolver.set_dataroot(
            self,
            "lambdapdk",
            "lambdapdk",
            "https://github.com/siliconcompiler/lambdapdk/archive/refs/tags/",
            alternative_ref=f"v{lambda_version}",
            python_module_path_append=".."
        )

        # version
        self.set_version("v1")

        lib_path = Path("lambdapdk", "asap7", "libs", "fakeram7")

        # General filelists
        for config in ('64x32', '128x32', '256x32', '256x64',
                       '512x32', '512x64', '512x128',
                       '1024x32', '1024x64',
                       '2048x32', '2048x64',
                       '4096x32', '4096x64',
                       '8192x32', '8192x64'):
            mem_name = f'fakeram7_sp_{config}'

            with self.active_dataroot("lambdapdk"):
                with self.active_fileset("models.timing.nldm"):
                    self.add_file(lib_path / "nldm" / f"{mem_name}.lib")
                    for corner in ("slow", "fast", "typical"):
                        self.add_asic_libcornerfileset(corner, "nldm")

                with self.active_fileset("models.physical"):
                    self.add_file(lib_path / "lef" / f"{mem_name}.lef")
                    self.add_asic_aprfileset()


class FakeRam7Lambdalib(DesignSchema):
    def __init__(self):
        super().__init__()
        self.set_name("fakeram7_lambdaramlib")

        PythonPathResolver.set_dataroot(
            self,
            "lambdapdk",
            "lambdapdk",
            "https://github.com/siliconcompiler/lambdapdk/archive/refs/tags/",
            alternative_ref=f"v{lambda_version}",
            python_module_path_append=".."
        )

        # version
        self.set_version("v1")

        lib_path = Path("lambdapdk", "asap7", "libs", "fakeram7")

        with self.active_dataroot("lambdapdk"):
            with self.active_fileset("rtl"):
                self.add_file(lib_path / "lambda" / "la_spram.v")


def target_nangate45(project):
    project.add_asiclib(Nangate45())
    project.set_mainlib("nangate45")

    scenario = project.get_constraints("timing").make_scenario("typical")
    scenario.add_libcorner("typical")
    scenario.set_pexcorner("typical")
    scenario.add_check(["setup", "hold"])

    project.set("asic", "delaymodel", "nldm")
    area = project.get_constraints("area")
    area.set_density(40)
    area.set_coremargin(1)

    # project.add_alias(Spram(), "rtl", FakeRam45Lambdalib(), "rtl")
    # project.add_asiclib(FakeRam45())


def target_asap7(project):
    project.add_asiclib(ASAP7SC7p5RVT())
    project.add_asiclib(ASAP7SC7p5LVT())
    project.add_asiclib(ASAP7SC7p5SLVT())

    scenario = project.get_constraints("timing").make_scenario("slow")
    scenario.add_libcorner("slow")
    scenario.set_pexcorner("typical")
    scenario.add_check("setup")
    scenario = project.get_constraints("timing").make_scenario("typical")
    scenario.add_libcorner("typical")
    scenario.set_pexcorner("typical")
    scenario.add_check("power")
    scenario = project.get_constraints("timing").make_scenario("fast")
    scenario.add_libcorner("fast")
    scenario.set_pexcorner("typical")
    scenario.add_check("hold")

    project.set("asic", "delaymodel", "nldm")
    area = project.get_constraints("area")
    area.set_density(40)
    area.set_coremargin(1)

    # project.add_alias(Spram(), "rtl", FakeRam7Lambdalib(), "rtl")
    # project.add_asiclib(FakeRam7())
