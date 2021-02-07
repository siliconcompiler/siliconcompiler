
import os
import siliconcompiler as sc

def setup_yosys(chip, root):

     refdir = root + '/yosys'
     stage = 'syn'

     chip.add('sc_tool', stage, 'np', '4')
     chip.add('sc_tool', stage, 'format', 'tcl')
     chip.add('sc_tool', stage, 'copy', 'False')
     chip.add('sc_tool', stage, 'vendor', 'yosys')
     chip.add('sc_tool', stage, 'exe', 'yosys')
     chip.add('sc_tool', stage, 'opt', '-c')
     chip.add('sc_tool', stage, 'refdir', refdir)
     chip.add('sc_tool', stage, 'script', refdir + '/sc_syn.tcl')
   
           
