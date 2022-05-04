import os
import siliconcompiler

def gcd_chip():
    gcd_ex_dir = os.path.join(scroot(), 'examples', 'gcd')

    chip = siliconcompiler.Chip('gcd')
    chip.load_target('freepdk45_demo')
    chip.add('source', 'verilog', os.path.join(gcd_ex_dir, 'gcd.v'))
    chip.add('source', 'sdc', os.path.join(gcd_ex_dir, 'gcd.sdc'))
    chip.set('asic', 'diearea', [(0,0), (100.13,100.8)])
    chip.set('asic', 'corearea', [(10.07,11.2), (90.25,91)])
    chip.set('option', 'quiet', 'true')
    chip.set('option', 'relax', 'true')

    return chip

def scroot():
    mydir = os.path.dirname(__file__)
    return os.path.abspath(os.path.join(mydir, '..'))

def datadir(file):
    mydir = os.path.dirname(file)
    return os.path.abspath(os.path.join(mydir, 'data'))
