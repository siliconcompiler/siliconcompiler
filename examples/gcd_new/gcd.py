#!/usr/bin/env python3
# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

import os
import siliconcompiler
from siliconcompiler.targets import freepdk45_demo

from siliconcompiler import DesignSchema
from siliconcompiler.project import LintProject
from siliconcompiler.schema import EditableSchema\

from siliconcompiler.flows.lintflow import LintFlowgraph, slang_lint


class GCDDesign(DesignSchema):
    def __init__(self):
        super().__init__()
        self.set_name("gcd")

        self.register_package("gcd-example", __file__)

        with self.active_fileset("rtl"):
            self.set_topmodule("gcd")
            self.add_file("gcd.v", package="gcd-example")

        with self.active_fileset("rtl.freepdk45"):
            self.add_file("gcd_freepdk45.sdc", package="gcd-example")

        with self.active_fileset("rtl.asap7"):
            self.add_file("gcd_asap7.sdc", package="gcd-example")


def main():
    gcd = GCDDesign()
    gcd.check_filepaths()
    gcd.write_fileset("rtl.f", ["rtl", "rtl.asap7"])

    project = LintProject()
    EditableSchema(project).insert("design", gcd, clobber=True)
    EditableSchema(project).insert("flowgraph", "lint", LintFlowgraph())
    EditableSchema(project).insert("tool", "slang", slang_lint.Lint())
    project.write_manifest("test.json")

    project.set("option", 'flow', "lint")

    project.run(raise_exception=True)


if __name__ == '__main__':
    main()
