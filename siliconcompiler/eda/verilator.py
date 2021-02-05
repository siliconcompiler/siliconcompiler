import os
import siliconcompiler as sc

####################################################
# Setup
####################################################

def setup_verilator(chip, root):
     
    chip.add('sc_tool', 'import', 'exe', 'verilator')
    chip.add('sc_tool', 'import', 'vendor', 'verilator')
    chip.add('sc_tool', 'import', 'opt', '--lint-only --debug')
  



           
