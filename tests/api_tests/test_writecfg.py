# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import sys
import siliconcompiler
from siliconcompiler.schema import schema_cfg
from siliconcompiler.schema import schema_flowgraph

def main():

    chip = siliconcompiler.Chip(loglevel="DEBUG")

    error = 0

    # without prune
    default_cfg = schema_cfg()
    chip.writecfg("noprune.json", cfg=default_cfg, prune=False)

    # with prune
    default_cfg = schema_cfg()
    chip.writecfg("prune.json", cfg=default_cfg)

#########################
if __name__ == "__main__":
    sys.exit(main())
    print("errorcode=",error)
