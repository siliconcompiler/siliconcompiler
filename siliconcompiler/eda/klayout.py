
import os
import siliconcompiler as sc


def setup_klayout(chip, root):
     refdir = root + '/klayout'
     
     for stage in (['export']):
          chip.add('sc_tool', stage, 'format', 'tcl')
          chip.add('sc_tool', stage, 'copy', 'no')
          chip.add('sc_tool', stage, 'exe', 'klayout')
          chip.add('sc_tool', stage, 'vendor', 'klayout')
          chip.add('sc_tool', stage, 'refdir', refdir)



           
