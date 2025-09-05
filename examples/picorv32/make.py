#!/usr/bin/env python3
# Copyright 2025 Silicon Compiler Authors. All Rights Reserved.

from siliconcompiler import DesignSchema
from siliconcompiler import ASICProject
from siliconcompiler.project import LintProject

from siliconcompiler.flows.lintflow import LintFlow
from siliconcompiler.targets import asic_target

from lambdalib.ramlib import Spram


class PicoRV32Design(DesignSchema):
    def __init__(self):
        super().__init__()
        self.set_name("picorv32")

        self.set_dataroot('picorv32',
                          'git+https://github.com/YosysHQ/picorv32.git',
                          'c0acaebf0d50afc6e4d15ea9973b60f5f4d03c42')
        self.set_dataroot('example', __file__)

        with self.active_fileset("rtl"):
            with self.active_dataroot("picorv32"):
                self.set_topmodule("picorv32")
                self.add_file("picorv32.v")

        with self.active_fileset("rtl.memory"):
            with self.active_dataroot("picorv32"):
                self.set_topmodule("picorv32_top")
                self.add_file("picorv32.v")
            with self.active_dataroot("example"):
                self.add_file("picorv32_top.v")
                self.add_depfileset(Spram(), "rtl")

        with self.active_fileset("sdc.freepdk45"):
            with self.active_dataroot("example"):
                self.add_file("picorv32.sdc")

        with self.active_fileset("sdc.asap7"):
            with self.active_dataroot("example"):
                self.add_file("picorv32.sdc")

        with self.active_fileset("sdc.gf180"):
            with self.active_dataroot("example"):
                self.add_file("picorv32.sdc")


def lint(fileset: str = "rtl"):
    project = LintProject()

    project.set_design(PicoRV32Design())
    project.add_fileset(fileset)
    project.set_flow(LintFlow())

    project.run()
    project.summary()


def syn(fileset: str = "rtl", pdk: str = "freepdk45"):
    project = ASICProject()

    project.set_design(PicoRV32Design())
    project.add_fileset(fileset)

    project.load_target(asic_target, pdk=pdk)
    project.set_flow("synflow")

    project.run()
    project.summary()


def asic(fileset: str = "rtl", pdk: str = "freepdk45"):
    project = ASICProject()

    project.set_design(PicoRV32Design())
    project.add_fileset(fileset)
    project.add_fileset(f"sdc.{pdk}")

    project.load_target(asic_target, pdk=pdk)

    project.run()
    project.summary()
    project.snapshot()


def check():
    assert PicoRV32Design().check_filepaths()


if __name__ == "__main__":
    syn()
