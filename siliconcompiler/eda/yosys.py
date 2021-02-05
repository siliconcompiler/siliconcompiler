
import os
import siliconcompiler as sc

def setup_yosys(chip, root):

     refdir = root + '/yosys'
     
     chip.add('sc_tool', 'syn', 'exe', 'yosys')
     chip.add('sc_tool', 'syn', 'opt', '-c')
     chip.add('sc_tool', 'syn', 'vendor', 'yosys')
     chip.add('sc_tool', 'syn', 'refdir', refdir)
     chip.add('sc_tool', 'syn', 'script', refdir + '/sc_syn.tcl')
   
           
