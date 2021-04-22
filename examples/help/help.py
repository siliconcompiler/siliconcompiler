# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

import re
import os
import siliconcompiler

#Create one (or many...) instances of Chip class
chip = siliconcompiler.Chip(loglevel="INFO")

# Print full help
allkeys = chip.getkeys()
with open("docs/sc_refmanual.md", 'w') as f:
    for key in allkeys:
        chip.help(*key, file=f)

# Print reference card
with open("docs/sc_reftable.md", 'w') as f:
    outlist = ['param', 'desription', 'type', 'required', 'default', 'value']
    outstr = " | {: <52} | {: <30} | {: <15} | {: <10} | {: <10}|".format(*outlist)
    print(outstr, file=f)
    outlist = [':----',
               ':----',
               ':----',
               ':----',
               ':----']
    outstr = " | {: <52} | {: <30} | {: <15} | {: <10} | {: <10}|".format(*outlist)
    print(outstr, file=f)
    for key in allkeys:
        chip.help(*key, file=f, mode='refcard')
