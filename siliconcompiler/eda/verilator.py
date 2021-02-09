import os
import siliconcompiler as sc

####################################################
# Setup
####################################################

def setup_verilator(chip, root):
     
    stage = 'import'
        
    chip.add('tool', stage, 'np', '4')
    chip.add('tool', stage, 'format', 'tcl')
    chip.add('tool', stage, 'copy', 'False')
    chip.add('tool', stage, 'exe', 'verilator')
    chip.add('tool', stage, 'vendor', 'verilator')
    chip.add('tool', stage, 'opt', '--lint-only --debug')
  



           
