
import os
import siliconcompiler as sc

def setup_openroad(chip, root):

     #local variables
     refdir = root + '/openroad'
     
     for stage in ('floorplan', 'place', 'cts', 'route', 'signoff'):
          chip.add('sc_tool', stage, 'exe', 'openroad')
          chip.add('sc_tool', stage, 'vendor', 'openroad')
          chip.add('sc_tool', stage, 'opt', '-no_init -exit')
          chip.add('sc_tool', stage, 'refdir', refdir)
          chip.add('sc_tool', stage, 'script', refdir + '/sc_'+stage+'.tcl')



           
