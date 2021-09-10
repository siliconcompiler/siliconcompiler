# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import sys
import siliconcompiler
import copy
import re
import os

if __name__ != "__main__":
    from tests.fixtures import test_wrapper

def test_fork():

    chip = siliconcompiler.Chip(loglevel="INFO")
    chip.target("freepdk45_asicflow")
    chip.writecfg("prefork.json")
    chip.fork("syn", 3)
    chip.writecfg("postfork.json")

#########################
if __name__ == "__main__":
    test_fork()
