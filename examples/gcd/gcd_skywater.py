import siliconcompiler

import os
import sys

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
    chip.set('clock', 'core_clock', 'period', 5)

    chip.load_target("skywater130_demo")

    chip.set('supply', 'vdd', 'pin', 'vdd')
    # level unimportant, just needs to be >0 to indicate power
    chip.set('supply', 'vdd', 'level', 1)

    chip.set('supply', 'vss', 'pin', 'vss')
    chip.set('supply', 'vss', 'level', 0)

    # 1) RTL2GDS

    def_path = make_floorplan(chip)
    chip.set('read', 'def', 'floorplan', '0', def_path)

    chip.set('jobname', 'rtl2gds')
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

    # 3) Checklist
    # Manual reports
    spec_path = os.path.join(os.path.dirname(__file__), 'spec.txt')
    chip.add('checklist', 'oh_tapeout', 'spec', 'report', spec_path)
    waiver_path = os.path.join(os.path.dirname(__file__), 'route_waiver.txt')

    chip.add('checklist', 'oh_tapeout', 'errors_warnings', 'waiver', 'warnings', waiver_path)

    chip.set('checklist', 'oh_tapeout', 'drc_clean', 'tasks', ('signoff', 'drc', '0'))
    chip.set('checklist', 'oh_tapeout', 'lvs_clean', 'tasks', ('signoff', 'lvs', '0'))
    chip.set('checklist', 'oh_tapeout', 'setup_time', 'tasks', ('rtl2gds', 'dfm', '0'))

    for step in chip.getkeys('flowgraph', 'asicflow'):
        for index in chip.getkeys('flowgraph', 'asicflow', step):
            tool = chip.get('flowgraph', 'asicflow', step, index, 'tool')
            if tool not in chip.builtin:
                chip.add('checklist', 'oh_tapeout', 'errors_warnings', 'tasks', ('rtl2gds', step, index))
    for step in chip.getkeys('flowgraph', 'signoffflow'):
        for index in chip.getkeys('flowgraph', 'signoffflow', step):
            tool = chip.get('flowgraph', 'signoffflow', step, index, 'tool')
            if tool not in chip.builtin:
                chip.add('checklist', 'oh_tapeout', 'errors_warnings', 'tasks', ('signoff', step, index))

    status = chip.check_checklist('oh_tapeout')
    if not status:
        sys.exit(1)

    # Mark 'ok'
    for item in chip.getkeys('checklist', 'oh_tapeout'):
        chip.set('checklist', 'oh_tapeout', item, 'ok', True)

    status = chip.check_checklist('oh_tapeout', check_ok=True)
    if not status:
        sys.exit(1)

    chip.write_manifest('gcd.checked.pkg.json')

if __name__ == '__main__':
    main()
