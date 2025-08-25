#!/usr/bin/env python3
# Copyright 2025 Silicon Compiler Authors. All Rights Reserved.

from siliconcompiler import DesignSchema
from siliconcompiler.project import LintProject, FPGAProject
from siliconcompiler import ASICProject

from siliconcompiler.flows.lintflow import LintFlowgraph
from siliconcompiler.flows.synflow import SynthesisFlowgraph
from siliconcompiler.flows.asicflow import ASICFlow
from siliconcompiler.flows.fpgaflow import FPGAFlow

from siliconcompiler._dummy import target
from siliconcompiler._dummy import ICE40FPGA, K6_N8_28x28_BDFPGA, K4_N8_6x6FPGA


class IBEXDesign(DesignSchema):
    def __init__(self):
        super().__init__()
        self.set_name("ibex")

        self.set_dataroot("ibex-example", __file__)
        self.set_dataroot("opentitan",
                          "git+https://github.com/lowRISC/opentitan.git",
                          "6074460f410bd6302cec90f32c7bb96aa8011243")
        self.set_dataroot("ibex-src",
                          "git+https://github.com/lowRISC/ibex.git",
                          "d097c918f5758b11995098103fdad6253fe555e7")

        with self.active_fileset("rtl"):
            self.set_topmodule("ibex_core")

            with self.active_dataroot("ibex-src"):
                for src in (
                        "rtl/ibex_pkg.sv",
                        "rtl/ibex_alu.sv",
                        "rtl/ibex_compressed_decoder.sv",
                        "rtl/ibex_controller.sv",
                        "rtl/ibex_counter.sv",
                        "rtl/ibex_cs_registers.sv",
                        "rtl/ibex_decoder.sv",
                        "rtl/ibex_ex_block.sv",
                        "rtl/ibex_id_stage.sv",
                        "rtl/ibex_if_stage.sv",
                        "rtl/ibex_load_store_unit.sv",
                        "rtl/ibex_multdiv_slow.sv",
                        "rtl/ibex_multdiv_fast.sv",
                        "rtl/ibex_prefetch_buffer.sv",
                        "rtl/ibex_fetch_fifo.sv",
                        "rtl/ibex_register_file_ff.sv",
                        "rtl/ibex_core.sv",
                        "rtl/ibex_csr.sv",
                        "rtl/ibex_wb_stage.sv",
                        "vendor/lowrisc_ip/ip/prim/rtl/prim_cipher_pkg.sv"):
                    self.add_file(src)
                self.add_idir("rtl")

                self.add_define("SYNTHESIS")

            with self.active_dataroot("opentitan"):
                self.add_idir("hw/ip/prim/rtl")
                self.add_idir("hw/dv/sv/dv_utils")

        with self.active_dataroot("ibex-example"):
            with self.active_fileset("rtl.freepdk45"):
                self.add_file("ibex_freepdk45.sdc")

            with self.active_fileset("rtl.asap7"):
                self.add_file("ibex_asap7.sdc")


def lint():
    project = LintProject()

    project.set_design(IBEXDesign())
    project.add_fileset("rtl")
    project.set_flow(LintFlowgraph())

    project.run(raise_exception=True)
    project.summary()


def syn(pdk: str = "freepdk45"):
    project = ASICProject()

    project.set_design(IBEXDesign())
    project.add_fileset("rtl")
    project.add_fileset(f"rtl.{pdk}")
    project.set_flow(SynthesisFlowgraph())

    project.load_target(target, pdk=pdk)

    project.get_task("yosys", "syn_asic").set("var", "use_slang", True)
    project.get_task("yosys", "syn_asic").set("var", "flatten", False)

    project.run(raise_exception=True)
    project.summary()


def asic(pdk: str = "freepdk45", show: bool = False):
    project = ASICProject()

    project.set_design(IBEXDesign())
    project.add_fileset("rtl")
    project.add_fileset(f"rtl.{pdk}")
    project.set_flow(ASICFlow())

    project.load_target(target, pdk=pdk)

    project.get_task("yosys", "syn_asic").set("var", "use_slang", True)
    project.get_task("yosys", "syn_asic").set("var", "flatten", False)

    project.run(raise_exception=True)
    project.summary()

    if show:
        project.show(extension="odb")


def fpga(fpga: str = "K4_N8"):
    project = FPGAProject()

    project.set_design(IBEXDesign())
    project.add_fileset("rtl")
    project.set_flow(FPGAFlow())

    project.add_dep(ICE40FPGA())
    project.add_dep(K6_N8_28x28_BDFPGA())
    project.add_dep(K4_N8_6x6FPGA())
    project.set_fpga(fpga)

    project.get_task("yosys", "syn_fpga").set("var", "use_slang", True)

    project.run(raise_exception=True)
    project.summary()


def check():
    assert IBEXDesign().check_filepaths()


if __name__ == "__main__":
    syn()
