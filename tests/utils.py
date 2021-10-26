import siliconcompiler
import os

def gcd_chip():
    root_dir = os.path.abspath(__file__)
    root_dir = root_dir[:root_dir.rfind('/tests')]
    gcd_ex_dir = root_dir + '/examples/gcd/'

    chip = siliconcompiler.Chip()
    chip.set('design', 'gcd', clobber=True)
    chip.target('asicflow_freepdk45')
    chip.add('source', gcd_ex_dir + 'gcd.v')
    chip.set('clock', 'core_clock', 'pin', 'clk')
    chip.set('clock', 'core_clock', 'period', 2)
    chip.add('constraint', gcd_ex_dir + 'gcd.sdc')
    chip.set('asic', 'diearea', [(0,0), (100.13,100.8)])
    chip.set('asic', 'corearea', [(10.07,11.2), (90.25,91)])
    chip.set('quiet', 'true', clobber=True)
    chip.set('relax', 'true', clobber=True)

    return chip
