import os
import siliconcompiler as sc

####################################################
# Setup
####################################################

def setup_verilator(chip, root):
     
    stage = 'import'
        
    chip.add('sc_tool', stage, 'np', '4')
    chip.add('sc_tool', stage, 'format', 'tcl')
    chip.add('sc_tool', stage, 'copy', 'False')
    chip.add('sc_tool', stage, 'exe', 'verilator')
    chip.add('sc_tool', stage, 'vendor', 'verilator')
    chip.add('sc_tool', stage, 'opt', '--lint-only --debug')
  



           
