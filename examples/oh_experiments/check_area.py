import siliconcompiler

import glob
import os
import re
import sys

def checkarea(filelist, libdir, target):
    '''
    Runs SC through synthesis and prints out the module name, cell count,
    and area as a csv format ready to be imported into a spreadsheet
    program.

    Args:
    filelist (list): List of files to process. Naming should be "module".v.
    libdir (str): Path to required Verilog sources.
    target (str): Name of the SC target. For example, freepdk45_demo.
    '''

    print("module", "cells", "area", sep=",")
    for item in filelist:
          design = re.match(r'.*/(\w+)\.v',item).group(1)
          chip = siliconcompiler.Chip(loglevel="ERROR")
          chip.load_target(target)
          chip.add('source', item)
          chip.add('ydir', libdir)
          chip.set('design', design)
          chip.set('quiet', True)
          chip.set('steplist', ['import', 'syn'])
          chip.run()
          cells = chip.get('metric','syn', '0', 'cells', 'real')
          area = chip.get('metric', 'syn', '0', 'cellarea', 'real')
          print(design, cells, area, sep=",")

    return 0

def main():
    oh_dir = (os.path.dirname(os.path.abspath(__file__)) +
               "/../../third_party/designs/oh/")
    #Checking asiclib
    libdir = os.path.join(oh_dir, 'asiclib', 'hdl')
    print(libdir)
    filelist = glob.glob(libdir + '/*.v')
    dontcheck = ['asic_keeper.v',
                 'asic_antenna.v',
                 'asic_header.v',
                 'asic_footer.v',
                 'asic_decap.v']
    print(filelist)
    for item in dontcheck:
        filelist.remove(os.path.join(libdir, item))

    return checkarea(filelist, libdir, 'freepdk45_demo')

#########################
if __name__ == "__main__":
    sys.exit(main())
