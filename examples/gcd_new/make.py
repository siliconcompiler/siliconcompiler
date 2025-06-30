#!/usr/bin/env python3
# Copyright 2025 Silicon Compiler Authors. All Rights Reserved.

from siliconcompiler import DesignSchema
from siliconcompiler.project import LintProject, ASICProject

from siliconcompiler.flows.lintflow import LintFlowgraph
from siliconcompiler.flows.synflow import SynthesisFlowgraph
from siliconcompiler.flows.asicflow import ASICFlow

from siliconcompiler._dummy import target_asap7, target_nangate45


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
                self.add_file("gcd.cc")

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
    project.set_flow(LintFlowgraph())

    project.run(raise_exception=True)


def syn(pdk: str = "freepdk45"):
    project = ASICProject()

    project.set_design(GCDDesign())
    project.add_fileset("rtl")
    project.add_fileset(f"rtl.{pdk}")
    project.set_flow(SynthesisFlowgraph())

    if pdk == "freepdk45":
        target_nangate45(project)
    elif pdk == "asap7":
        target_asap7(project)
    else:
        raise ValueError

    project.run(raise_exception=True)


def asic(pdk: str = "freepdk45"):
    project = ASICProject()

    project.set_design(GCDDesign())
    project.add_fileset("rtl")
    project.add_fileset(f"rtl.{pdk}")
    project.set_flow(ASICFlow())

    if pdk == "freepdk45":
        target_nangate45(project)
    elif pdk == "asap7":
        target_asap7(project)
    else:
        raise ValueError

    project.run(raise_exception=True)


def check():
    assert GCDDesign().check_filepaths()


if __name__ == "__main__":
    syn()
