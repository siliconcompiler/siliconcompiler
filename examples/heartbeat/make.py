#!/usr/bin/env python3
# Copyright 2025 Silicon Compiler Authors. All Rights Reserved.

from siliconcompiler import DesignSchema, FPGASchema
from siliconcompiler.project import LintProject, SimProject
from siliconcompiler import ASICProject, FPGAProject

from siliconcompiler.flows.lintflow import LintFlow
from siliconcompiler.flows.synflow import SynthesisFlow
from siliconcompiler.flows.dvflow import DVFlow
from siliconcompiler.flows.asicflow import ASICFlow
from siliconcompiler.flows.fpgaflow import FPGAXilinxFlow

from siliconcompiler.targets import asic_target


class HeartbeatDesign(DesignSchema):
    def __init__(self):
        super().__init__()
        self.set_name("heartbeat")

        self.set_dataroot("heartbeat", __file__)

        with self.active_dataroot("heartbeat"):
            with self.active_fileset("rtl"):
                self.set_topmodule("heartbeat")
                self.add_file("heartbeat.v")
                self.set_param("N", "8")

            with self.active_fileset("testbench.icarus"):
                self.set_topmodule("heartbeat_tb")
                self.add_file("testbench.v")
                self.set_param("N", "8")

            with self.active_fileset("testbench.verilator"):
                self.set_topmodule("heartbeat")
                self.add_file("testbench.cc")
                self.set_param("N", "8")

            with self.active_fileset("rtl.freepdk45"):
                self.add_file("heartbeat.sdc")

            with self.active_fileset("rtl.asap7"):
                self.add_file("heartbeat_asap7.sdc")

            with self.active_fileset("fpga.xc7a100tcsg324"):
                self.add_file("heartbeat.xdc")


def lint(N: str = None):
    project = LintProject()

    hb = HeartbeatDesign()

    project.set_design(hb)
    project.add_fileset("rtl")

    if N is not None:
        hb.set_param("N", N, fileset="rtl")

    project.set_flow(LintFlow())

    project.run()
    project.summary()


def syn(pdk: str = "freepdk45", N: str = None):
    project = ASICProject()

    hb = HeartbeatDesign()

    project.set_design(hb)
    project.add_fileset("rtl")
    project.add_fileset(f"rtl.{pdk}")
    project.set_flow(SynthesisFlow())

    if N is not None:
        hb.set_param("N", N, fileset="rtl")

    project.load_target(asic_target, pdk=pdk)

    project.run()
    project.summary()


def asic(pdk: str = "freepdk45", N: str = None):
    project = ASICProject()

    hb = HeartbeatDesign()

    project.set_design(hb)
    project.add_fileset("rtl")
    project.add_fileset(f"rtl.{pdk}")
    project.set_flow(ASICFlow())

    if N is not None:
        hb.set_param("N", N, fileset="rtl")

    project.load_target(asic_target, pdk=pdk)

    project.run()
    project.summary()
    project.snapshot()


def sim(N: str = None, tool: str = "verilator"):
    project = SimProject()

    hb = HeartbeatDesign()

    project.set_design(hb)
    project.add_fileset(f"testbench.{tool}")
    project.add_fileset("rtl")
    project.set_flow(DVFlow(tool=tool))

    if N is not None:
        hb.set_param("N", N, fileset="testbench")

    project.run()
    project.summary()


def fpga(N: str = None):
    project = FPGAProject()

    hb = HeartbeatDesign()

    project.set_design(hb)
    project.add_fileset("rtl")
    project.add_fileset("fpga.xc7a100tcsg324")
    project.set_flow(FPGAXilinxFlow())

    fpga = FPGASchema("xc7")
    fpga.set_partname("xc7a100tcsg324")
    project.set_fpga(fpga)

    if N is not None:
        hb.set_param("N", N, fileset="testbench")

    project.run()
    project.summary()


def check():
    assert HeartbeatDesign().check_filepaths()


if __name__ == "__main__":
    syn()
