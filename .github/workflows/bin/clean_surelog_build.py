#!/usr/bin/env python3

'''Remove files from Surelog installation that aren't necessary for runtime.'''

import glob
import os

for file in glob.glob('siliconcompiler/tools/surelog/**/*', recursive=True):
    if not os.path.isfile(file): continue

    if (
        (not file.endswith('.py')) and
        (not file.startswith('siliconcompiler/tools/surelog/bin/surelog')) and
        file != 'siliconcompiler/tools/surelog/lib/surelog/sv/builtin.sv'
    ):
        os.remove(file)
