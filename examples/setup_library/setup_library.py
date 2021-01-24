# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

import siliconcompiler as sc
import json

# Create instance of Chip class
chip = sc.Chip()

with open("old.json", 'w') as f:
    print(json.dumps(chip.cfg, sort_keys=True, indent=4), file=f)
      
chip.set2('sc_stdlib', "mylib", "timing", "tt", "/home/aolofsson/mylib_tt.lib")
chip.set2('sc_stdlib', "mylib", "lef",          "/home/aolofsson/mylib.lef"   )
chip.set2('sc_design',                          "top"                         )

with open("new.json", 'w') as f:
    print(json.dumps(chip.cfg, sort_keys=True, indent=4), file=f)
