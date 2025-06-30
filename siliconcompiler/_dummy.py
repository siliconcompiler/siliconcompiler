#!/usr/bin/env python3
# Copyright 2025 Silicon Compiler Authors. All Rights Reserved.

from pathlib import Path

from lambdapdk import __version__ as lambda_version

from lambdapdk.asap7.libs.asap7sc7p5t import ASAP7SC7p5RVT, ASAP7SC7p5SLVT, ASAP7SC7p5LVT
from lambdapdk.asap7.libs.fakeram7 import FakeRAM7Lambdalib_SinglePort, FakeRAM7Lambdalib_DoublePort

from lambdapdk.freepdk45.libs.nangate45 import Nangate45
from lambdapdk.freepdk45.libs.fakeram45 import FakeRAM45Lambdalib_SinglePort

from lambdapdk.sky130.libs.sky130sc import Sky130_SCHDLibrary
from lambdapdk.sky130.libs.sky130sram import Sky130Lambdalib_SinglePort

from lambdapdk.ihp130.libs.sg13g2_stdcell import IHP130StdCell_1p2
from lambdapdk.ihp130.libs.sg13g2_sram import IHP130Lambdalib_SinglePort

from lambdapdk.gf180 import GF180_5LM_1TM_9K_9t
from lambdapdk.gf180.libs.gf180mcu import GF180_MCU_9T_5LMLibrary
from lambdapdk.gf180.libs.gf180sram import GF180Lambdalib_SinglePort

from lambdapdk.interposer import Interposer_3ML_0400
from lambdapdk.interposer.libs.bumps import BumpLibrary


from siliconcompiler.package import PythonPathResolver

from siliconcompiler import DesignSchema, FPGASchema
from siliconcompiler import ASICProject

from siliconcompiler.tools.yosys import YosysFPGA
from siliconcompiler.tools.vpr import VPRFPGA


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


class ICE40FPGA(YosysFPGA, FPGASchema):
    def __init__(self):
        super().__init__()
        self.set_name("ice")
        self.set_partname("ice40up5k-sg48")
        self.set_lutsize(4)
        self.set_vendor("lattice")


class K4_N8_6x6FPGA(YosysFPGA, VPRFPGA, FPGASchema):
    def __init__(self):
        super().__init__()
        self.set_name("K4_N8")
        self.set_partname("K4_N8_6x6")
        self.set_lutsize(4)
        self.set_vendor("zeroasic")

        self.set_dataroot("cad",
                          "github://siliconcompiler/logiklib/v0.1.0/K4_N8_6x6_cad.tar.gz",
                          "v0.1.0")

        # Yosys setup
        self.add_yosys_registertype("dff")

        # VPR setup
        with self.active_dataroot("cad"):
            self.add_vpr_registertype("dff")
            self.set_vpr_devicecode("K4_N8_6x6")
            self.set_vpr_channelwidth(50)
            self.set_vpr_clockmodel("ideal")
            self.set_vpr_archfile("cad/K4_N8_6x6.xml")
            self.set_vpr_graphfile("cad/K4_N8_6x6_rr_graph.xml")


class K6_N8_28x28_BDFPGA(YosysFPGA, VPRFPGA, FPGASchema):
    def __init__(self):
        super().__init__()
        self.set_name("K6_N8")
        self.set_partname("K6_N8_28x28_BD")
        self.set_lutsize(6)
        self.set_vendor("zeroasic")

        self.set_dataroot("cad",
                          "github://siliconcompiler/logiklib/v0.1.0/K6_N8_28x28_BD_cad.tar.gz",
                          "v0.1.0")

        # Yosys setup
        with self.active_dataroot("cad"):
            self.set_yosys_flipfloptechmap("techlib/tech_flops.v")
            self.set_yosys_memorymap(libmap="techlib/bram_memory_map.txt", techmap="techlib/tech_bram.v")
            self.set_yosys_dsptechmap("techlib/tech_dsp.v", options=[
                'DSP_A_MAXWIDTH=18', 'DSP_A_MINWIDTH=2',
                'DSP_B_MAXWIDTH=18', 'DSP_B_MINWIDTH=2',
                'DSP_NAME=_dsp_block_'])

            self.add_yosys_registertype(['dff', 'dffe', 'dffer', 'dffers', 'dffes', 'dffr', 'dffrs', 'dffs'])
            self.add_yosys_bramtype('bram_sp')
            self.add_yosys_dsptype('dsp_mult')
            self.add_yosys_featureset(['async_reset', 'async_set', 'enable'])

        # VPR setup
        with self.active_dataroot("cad"):
            self.add_vpr_registertype(['dff', 'dffe', 'dffer', 'dffers', 'dffes', 'dffr', 'dffrs', 'dffs'])
            self.add_vpr_bramtype('bram_sp')
            self.add_vpr_dsptype('dsp_mult')
            self.set_vpr_devicecode("K6_N8_28x28_BD")
            self.set_vpr_channelwidth(120)
            self.set_vpr_clockmodel("ideal")
            self.set_vpr_archfile("cad/K6_N8_28x28_BD.xml")
            self.set_vpr_graphfile("cad/K6_N8_28x28_BD_rr_graph.xml")


def target(project: ASICProject, pdk: str = None):
    if pdk == "freepdk45":
        target_freepdk45(project)
    elif pdk == "asap7":
        target_asap7(project)
    elif pdk == "gf180":
        target_gf180(project)
    elif pdk == "ihp130":
        target_ihp130(project)
    elif pdk == "sky130":
        target_skywater130(project)
    else:
        raise ValueError


def target_asap7(project: ASICProject):
    project.add_asiclib(ASAP7SC7p5RVT())
    project.add_asiclib(ASAP7SC7p5LVT())
    project.add_asiclib(ASAP7SC7p5SLVT())

    scenario = project.get_timingconstraints().make_scenario("slow")
    scenario.add_libcorner("slow")
    scenario.set_pexcorner("typical")
    scenario.add_check("setup")
    scenario = project.get_timingconstraints().make_scenario("typical")
    scenario.add_libcorner("typical")
    scenario.set_pexcorner("typical")
    scenario.add_check("power")
    scenario = project.get_timingconstraints().make_scenario("fast")
    scenario.add_libcorner("fast")
    scenario.set_pexcorner("typical")
    scenario.add_check("hold")

    project.set("asic", "delaymodel", "nldm")
    area = project.get_areaconstraints()
    area.set_density(40)
    area.set_coremargin(1)

    FakeRAM7Lambdalib_SinglePort.alias(project)
    FakeRAM7Lambdalib_DoublePort.alias(project)


def target_freepdk45(project: ASICProject):
    project.add_asiclib(Nangate45())
    project.set_mainlib("nangate45")

    scenario = project.get_timingconstraints().make_scenario("typical")
    scenario.add_libcorner("typical")
    scenario.set_pexcorner("typical")
    scenario.add_check(["setup", "hold"])

    project.set("asic", "delaymodel", "nldm")
    area = project.get_areaconstraints()
    area.set_density(40)
    area.set_coremargin(1)

    FakeRAM45Lambdalib_SinglePort.alias(project)


def target_gf180(project: ASICProject):
    project.set_pdk(GF180_5LM_1TM_9K_9t())
    project.add_asiclib(GF180_MCU_9T_5LMLibrary())
    project.set_mainlib(GF180_MCU_9T_5LMLibrary())

    scenario = project.get_timingconstraints().make_scenario("slow")
    scenario.add_libcorner("slow")
    scenario.set_pexcorner("typical")
    scenario.add_check("setup")
    scenario = project.get_timingconstraints().make_scenario("typical")
    scenario.add_libcorner("typical")
    scenario.set_pexcorner("typical")
    scenario.add_check("power")
    scenario = project.get_timingconstraints().make_scenario("fast")
    scenario.add_libcorner("fast")
    scenario.set_pexcorner("typical")
    scenario.add_check("hold")

    project.set("asic", "delaymodel", "nldm")
    area = project.get_areaconstraints()
    area.set_density(40)
    area.set_coremargin(1)

    GF180Lambdalib_SinglePort.alias(project)


def target_ihp130(project: ASICProject):
    project.set_mainlib(IHP130StdCell_1p2())

    scenario = project.get_timingconstraints().make_scenario("slow")
    scenario.add_libcorner("slow")
    scenario.set_pexcorner("typical")
    scenario.add_check("setup")
    scenario = project.get_timingconstraints().make_scenario("typical")
    scenario.add_libcorner("typical")
    scenario.set_pexcorner("typical")
    scenario.add_check("power")
    scenario = project.get_timingconstraints().make_scenario("fast")
    scenario.add_libcorner("fast")
    scenario.set_pexcorner("typical")
    scenario.add_check("hold")

    project.set("asic", "delaymodel", "nldm")
    area = project.get_areaconstraints()
    area.set_density(40)
    area.set_coremargin(4.8)

    IHP130Lambdalib_SinglePort.alias(project)


def target_skywater130(project: ASICProject):
    project.set_mainlib(Sky130_SCHDLibrary())

    scenario = project.get_timingconstraints().make_scenario("slow")
    scenario.add_libcorner("slow")
    scenario.set_pexcorner("typical")
    scenario.add_check("setup")
    scenario = project.get_timingconstraints().make_scenario("typical")
    scenario.add_libcorner("typical")
    scenario.set_pexcorner("typical")
    scenario.add_check("power")
    scenario = project.get_timingconstraints().make_scenario("fast")
    scenario.add_libcorner("fast")
    scenario.set_pexcorner("typical")
    scenario.add_check("hold")

    project.set("asic", "delaymodel", "nldm")
    area = project.get_areaconstraints()
    area.set_density(40)
    area.set_coremargin(1)

    Sky130Lambdalib_SinglePort.alias(project)


def target_interposer(project: ASICProject):
    project.set_pdk(Interposer_3ML_0400())
    project.add_asiclib(BumpLibrary())

    scenario = project.get_timingconstraints().make_scenario("typical")
    scenario.add_libcorner("typical")
    scenario.set_pexcorner("typical")
    scenario.add_check(["setup", "hold", "power"])

    project.set("asic", "delaymodel", "nldm")
    area = project.get_areaconstraints()
    area.set_density(40)
    area.set_coremargin(1)

    Sky130Lambdalib_SinglePort.alias(project)
