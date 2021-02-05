
import os
import re
import siliconcompiler as sc
from siliconcompiler.eda.verilator import setup_verilator
from siliconcompiler.eda.yosys import setup_yosys
from siliconcompiler.eda.openroad import setup_openroad
from siliconcompiler.eda.klayout import setup_klayout


####################################################
# Setup
####################################################

def foss_eda(chip, root):

     #local variables
     threads = 4
     
     # commmon settings
     for stage in chip.get('sc_stages'):
          chip.add('sc_tool', stage, 'np', threads)
          chip.add('sc_tool', stage, 'format', 'tcl')
          chip.add('sc_tool', stage, 'copy', 'False')
     
     # tool specific settings
     setup_verilator(chip, root) # import
     setup_yosys(chip, root)     # synthesis
     setup_openroad(chip, root)  # apr
     setup_klayout(chip, root)   # export

#########################
if __name__ == "__main__":    

    # File being executed
    prefix = os.path.splitext(os.path.basename(__file__))[0]
    output = prefix + '.json'
    dirname = os.path.dirname(os.path.abspath(__file__))
    datadir = re.sub('siliconcompiler/siliconcompiler','siliconcompiler', dirname)

    # create a chip instance
    chip = sc.Chip()
    # load configuration
    foss_eda(chip, datadir)
    # write out storage file
    chip.writecfg(output)



           
