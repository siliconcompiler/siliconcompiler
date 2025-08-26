#!/usr/bin/env python3
# Copyright 2025 Silicon Compiler Authors. All Rights Reserved.

from siliconcompiler import DesignSchema
from siliconcompiler.project import LintProject
from siliconcompiler import ASICProject, FPGAProject

from siliconcompiler.flows.lintflow import LintFlow
from siliconcompiler.flows.synflow import SynthesisFlow
from siliconcompiler.flows.asicflow import ASICFlow, HLSASSICFlow
from siliconcompiler.flows.fpgaflow import FPGAFlow

from siliconcompiler._dummy import target
from siliconcompiler._dummy import ICE40FPGA, K6_N8_28x28_BDFPGA, K4_N8_6x6FPGA


class GCDDesign(DesignSchema):
    def __init__(self):
        super().__init__()
        self.set_name("gcd")

        self.set_dataroot("gcd-example", __file__)

        with self.active_dataroot("gcd-example"):
            with self.active_fileset("rtl"):
                self.set_topmodule("gcd")
                self.add_file("gcd.v")

            with self.active_fileset("hls.c"):
                self.set_topmodule("gcd")
                self.add_file("gcd.c")

            with self.active_fileset("hls.scala"):
                self.set_topmodule("GCD")
                self.add_file("GCD.scala")

            with self.active_fileset("rtl.freepdk45"):
                self.add_file("gcd_freepdk45.sdc")

            with self.active_fileset("rtl.asap7"):
                self.add_file("gcd_asap7.sdc")


def lint():
    project = LintProject()

    project.set_design(GCDDesign())
    project.add_fileset("rtl")
    project.set_flow(LintFlow())

    project.run(raise_exception=True)


def syn(pdk: str = "freepdk45"):
    project = ASICProject()

    project.set_design(GCDDesign())
    project.add_fileset("rtl")
    project.add_fileset(f"rtl.{pdk}")
    project.set_flow(SynthesisFlow())

    project.load_target(target, pdk=pdk)

    project.run(raise_exception=True)
    project.summary()


def asic(pdk: str = "freepdk45", fileset: str = "rtl", show: bool = False,
         screenshot: bool = False):
    project = ASICProject()

    project.set_design(GCDDesign())
    project.add_fileset(fileset)
    project.add_fileset(f"rtl.{pdk}")
    if fileset == "hls.c":
        project.set_flow(HLSASSICFlow())
    else:
        project.set_flow(ASICFlow())

    project.load_target(target, pdk=pdk)

    project.run(raise_exception=True)
    project.summary()

    project.snapshot(display=False)

    if show or screenshot:
        project.show(extension="odb", screenshot=screenshot)


def fpga(fpga: str = "K4_N8"):
    project = FPGAProject()

    project.set_design(GCDDesign())
    project.add_fileset("rtl")
    project.set_flow(FPGAFlow())

    project.add_dep(ICE40FPGA())
    project.add_dep(K6_N8_28x28_BDFPGA())
    project.add_dep(K4_N8_6x6FPGA())
    project.set_fpga(fpga)

    project.run(raise_exception=True)
    project.summary()


def check():
    assert GCDDesign().check_filepaths()


if __name__ == "__main__":
    syn()
