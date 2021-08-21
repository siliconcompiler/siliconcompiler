# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import sys
import siliconcompiler
from siliconcompiler.schema import schema_cfg
from siliconcompiler.schema import schema_flowgraph

def main():

    chip = siliconcompiler.Chip(loglevel="DEBUG")

    error = 0

    # big default dict
    default_cfg = schema_cfg()
    chip.writecfg("default.json", cfg=default_cfg, prune=False)

    # setting partial dict
    new_cfg = {}
    new_cfg  = schema_flowgraph(new_cfg, step='syn')
    chip.writecfg("new.json", cfg=new_cfg, prune=False)

    # merged dict
    merged_cfg = chip.merge(default_cfg, new_cfg)
    chip.writecfg("default2.json", cfg=default_cfg, prune=False)
    chip.writecfg("new2.json", cfg=new_cfg, prune=False)
    chip.writecfg("merged2.json", cfg=merged_cfg, prune=False)

#########################
if __name__ == "__main__":
    sys.exit(main())
    print("errorcode=",error)
