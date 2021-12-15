import os
import siliconcompiler

def gcd_chip():
    gcd_ex_dir = os.path.join(scroot(), 'examples', 'gcd')

    chip = siliconcompiler.Chip()
    chip.set('design', 'gcd', clobber=True)
    chip.target('asicflow_freepdk45')
    chip.add('source', os.path.join(gcd_ex_dir, 'gcd.v'))
    chip.set('clock', 'clock_name', 'pin', 'clk')
    chip.set('clock', 'clock_name', 'period', 2)
    chip.add('read', 'sdc', 'import', '0', os.path.join(gcd_ex_dir, 'gcd_noclock.sdc'))
    chip.set('asic', 'diearea', [(0,0), (100.13,100.8)])
    chip.set('asic', 'corearea', [(10.07,11.2), (90.25,91)])
    chip.set('quiet', 'true', clobber=True)
    chip.set('relax', 'true', clobber=True)

    return chip

def scroot():
    mydir = os.path.dirname(__file__)
    return os.path.abspath(os.path.join(mydir, '..'))

def datadir(file):
    mydir = os.path.dirname(file)
    return os.path.abspath(os.path.join(mydir, 'data'))
