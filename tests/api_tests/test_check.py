# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import sys
import siliconcompiler
from siliconcompiler.schema import schema_cfg
from siliconcompiler.schema import schema_flowgraph

def main():

    chip = siliconcompiler.Chip(loglevel="INFO")
    chip.target("freepdk45_asicflow")
    chip.set('source', 'examples/gcd/gcd.v')
    chip.check('route')

#########################
if __name__ == "__main__":
    sys.exit(main())
    print("errorcode=",error)
