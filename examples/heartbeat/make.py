#!/usr/bin/env python3
# Copyright 2025 Silicon Compiler Authors. All Rights Reserved.

from siliconcompiler import DesignSchema
from siliconcompiler.project import LintProject, SimProject
from siliconcompiler import ASICProject

from siliconcompiler.flows.lintflow import LintFlow
from siliconcompiler.flows.synflow import SynthesisFlow
from siliconcompiler.flows.dvflow import DVFlow
from siliconcompiler.flows.asicflow import ASICFlow

from siliconcompiler._dummy import target_asap7, target_nangate45


class HeartbeatDesign(DesignSchema):
    def __init__(self):
        super().__init__()
        self.set_name("heartbeat")

        self.set_dataroot("heartbeat-example", __file__)

        with self.active_dataroot("heartbeat-example"):
            with self.active_fileset("rtl"):
                self.set_topmodule("heartbeat")
                self.add_file("heartbeat.v")
                self.set_param("N", "8")

            with self.active_fileset("testbench"):
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

    project.run(raise_exception=True)
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

    if pdk == "freepdk45":
        target_nangate45(project)
    elif pdk == "asap7":
        target_asap7(project)
    else:
        raise ValueError

    project.run(raise_exception=True)
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

    if pdk == "freepdk45":
        target_nangate45(project)
    elif pdk == "asap7":
        target_asap7(project)
    else:
        raise ValueError

    project.run(raise_exception=True)
    project.summary()


def sim(N: str = None):
    project = SimProject()

    hb = HeartbeatDesign()

    project.set_design(hb)
    project.add_fileset("testbench")
    project.add_fileset("rtl")
    project.set_flow(DVFlow(N=4))

    if N is not None:
        hb.set_param("N", N, fileset="testbench")

    project.run(raise_exception=True)
    project.summary()


def check():
    assert HeartbeatDesign().check_filepaths()


if __name__ == "__main__":
    syn()
