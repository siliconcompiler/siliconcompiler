
import os
import sys
import re
import siliconcompiler

####################################################
# Library Setup
####################################################
def setup_skywater130_libs(chip):
    pass
  

#########################
if __name__ == "__main__":    

    # File being executed
    prefix = os.path.splitext(os.path.basename(__file__))[0]
    output = prefix + '.json'

    # create a chip instance
    chip = siliconcompiler.Chip()
    # load configuration
    setup_skywater130_libs(chip)
    # write out result
    chip.writecfg(output)

   
