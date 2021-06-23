import os
import re

def setup_board(chip, vendor, device, constraint_ext):
    # Find the directory containing board config files.
    scriptdir = os.path.dirname(os.path.abspath(__file__))
    sc_root   = re.sub('siliconcompiler/fpga/targets',
                       'siliconcompiler',
                       scriptdir)
    board_loc = sc_root + '/fpga/boards/' + device

    # Set core values in the Chip config dictionary.
    chip.add('mode', 'fpga')
    chip.set('fpga', 'vendor', vendor)
    chip.set('fpga', 'device', device)
    chip.set('constraint', board_loc + '/' + device + '.' + constraint_ext)
