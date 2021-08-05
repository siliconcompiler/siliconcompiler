import os
import re

def setup_board(chip, vendor, partname, constraint_ext):
    # Find the directory containing board config files.
    scriptdir = os.path.dirname(os.path.abspath(__file__))
    sc_root   = re.sub('siliconcompiler/fpga/targets',
                       'siliconcompiler',
                       scriptdir)
    board_loc = sc_root + '/fpga/boards/' + partname

    # Set core values in the Chip config dictionary.
    chip.add('mode', 'fpga')
    chip.set('fpga', 'vendor', vendor)
    chip.set('fpga', 'partname', partname)
    chip.set('constraint', board_loc + '/' + partname + '.' + constraint_ext)
