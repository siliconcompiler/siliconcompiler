import siliconcompiler

from sky130_floorplan import make_floorplan

def main():
    '''GCD example with custom floorplan and signoff steps.'''

    # Create instance of Chip class
    chip = siliconcompiler.Chip()

    chip.add('source', 'gcd.v')
    chip.set('design', 'gcd')
    chip.set('relax', True)
    chip.set('quiet', True)
    chip.set('clock', 'core_clock', 'pin', 'clk')
    chip.set('clock', 'core_clock', 'period', 2)

    chip.load_target("skywater130_demo")

    chip.set('supply', 'vdd', 'pin', 'vdd')
    # level unimportant, just needs to be >0 to indicate power
    chip.set('supply', 'vdd', 'level', 1)

    chip.set('supply', 'vss', 'pin', 'vss')
    chip.set('supply', 'vss', 'level', 0)

    # 1) RTL2GDS

    def_path = make_floorplan(chip)
    chip.set('read', 'def', 'floorplan', '0', def_path)

    chip.run()
    chip.summary()

    gds_path = chip.find_result('gds', step='export')
    vg_path = chip.find_result('vg', step='dfm')

    # 2) Signoff

    chip.set('jobname', 'signoff')
    chip.set('flow', 'signoffflow')

    chip.set('read', 'gds', 'drc', '0', gds_path)
    chip.set('read', 'gds', 'extspice', '0', gds_path)
    chip.set('read', 'netlist', 'lvs', '0', vg_path)

    chip.run()
    chip.summary()

if __name__ == '__main__':
    main()
