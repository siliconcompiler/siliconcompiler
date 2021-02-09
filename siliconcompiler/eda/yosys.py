
import os
import siliconcompiler as sc

def setup_yosys(chip, root):

     refdir = root + '/yosys'
     stage = 'syn'

     chip.add('tool', stage, 'np', '4')
     chip.add('tool', stage, 'format', 'tcl')
     chip.add('tool', stage, 'copy', 'False')
     chip.add('tool', stage, 'vendor', 'yosys')
     chip.add('tool', stage, 'exe', 'yosys')
     chip.add('tool', stage, 'opt', '-c')
     chip.add('tool', stage, 'refdir', refdir)
     chip.add('tool', stage, 'script', refdir + '/sc_syn.tcl')
   
           
