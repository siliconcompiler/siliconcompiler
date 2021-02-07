
import os
import siliconcompiler as sc


def setup_klayout(chip, root):

     refdir = root + '/klayout'
     
     for stage in (['export']):
          chip.add('sc_tool', stage, 'np', '4')
          chip.add('sc_tool', stage, 'format', 'tcl')
          chip.add('sc_tool', stage, 'copy', 'False')
          chip.add('sc_tool', stage, 'vendor', 'klayout')
          chip.add('sc_tool', stage, 'exe', 'klayout')
          chip.add('sc_tool', stage, 'opt', '')
          chip.add('sc_tool', stage, 'refdir', refdir)
          chip.add('sc_tool', stage, 'script', refdir + '/sc_'+stage+'.tcl')




           
