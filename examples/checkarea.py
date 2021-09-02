import siliconcompiler
import glob
import re
import sys

def checkarea(filelist, target):
    '''
    Runs SC through synthesis and prints out the module name, cell count,
    and area as a csv format ready to be imported into a spreadsheet
    program.

    Args:
    filelist (list): List of files to process. Naming should be
    "module".v
    target (str): Name of the synthesis target. For example,
    freepdk45_asic.

    '''

    print("module","cells", "area", sep=",")
    for item in filelist:
          design = re.match(r'.*/(\w+)\.v',item).group(1)
          chip = siliconcompiler.Chip(loglevel="ERROR")
          chip.target(target)
          chip.add('source', item)
          chip.add('ydir', libdir)
          chip.set('design', design)
          chip.set('quiet', "true")
          chip.set('stop','syn')
          chip.run()
          cells = chip.get('real','syn','cells')[0]
          area = chip.get('real','syn','area_cells')[0]
          print(design, cells, area, sep=",")

#########################
if __name__ == "__main__":

    #Checking asiclib
    libdir = "third_party/designs/oh/asiclib/hdl/"
    filelist = glob.glob(libdir + '/*.v')
    dontcheck = ['asic_keeper.v',
                 'asic_antenna.v',
                 'asic_header.v',
                 'asic_footer.v',
                 'asic_decap.v']
    for item in dontcheck:
        filelist.remove(libdir+item)
    sys.exit(checkarea(filelist, "freepdk45_asic"))
