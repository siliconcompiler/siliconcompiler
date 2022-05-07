import siliconcompiler

import os
import sys

from sky130_floorplan import make_floorplan

def main():
    '''GCD example with custom floorplan and signoff steps.'''

    # Create instance of Chip class
    chip = siliconcompiler.Chip("gcd")

    chip.add('source', 'verilog', 'gcd.v')
    chip.add('source', 'sdc', 'gcd.sdc')
    chip.set('option', 'relax', True)
    chip.set('option', 'quiet', True)

    chip.load_target("skywater130_demo")

    #chip.set('supply', 'vdd', 'pin', 'vdd')
    #chip.set('supply', 'vdd', 'level', 1)
    #chip.set('supply', 'vss', 'pin', 'vss')
    #chip.set('supply', 'vss', 'level', 0)

    # 1) RTL2GDS

    def_path = make_floorplan(chip)
    chip.set('source', 'def', def_path)

    chip.set('option', 'jobname', 'rtl2gds')
    chip.run()
    chip.summary()

    gds_path = chip.find_result('gds', step='export')
    vg_path = chip.find_result('vg', step='dfm')

    # 2) Signoff

    chip.set('jobname', 'signoff')
    chip.set('flow', 'signoffflow')

    chip.set('source', 'gds', gds_path)
    chip.set('source', 'netlist', vg_path)

    chip.run()
    chip.summary()

    # 3) Checklist
    # Manual reports
    spec_path = os.path.join(os.path.dirname(__file__), 'spec.txt')
    chip.add('checklist', 'oh_tapeout', 'spec', 'report', spec_path)
    waiver_path = os.path.join(os.path.dirname(__file__), 'route_waiver.txt')

    chip.add('checklist', 'oh_tapeout', 'errors_warnings', 'waiver', 'warnings', waiver_path)

    chip.set('checklist', 'oh_tapeout', 'drc_clean', 'task', ('signoff', 'drc', '0'))
    chip.set('checklist', 'oh_tapeout', 'lvs_clean', 'task', ('signoff', 'lvs', '0'))
    chip.set('checklist', 'oh_tapeout', 'setup_time', 'task', ('rtl2gds', 'dfm', '0'))

    for step in chip.getkeys('flowgraph', 'asicflow'):
        for index in chip.getkeys('flowgraph', 'asicflow', step):
            tool = chip.get('flowgraph', 'asicflow', step, index, 'tool')
            if tool not in chip.builtin:
                chip.add('checklist', 'oh_tapeout', 'errors_warnings', 'task', ('rtl2gds', step, index))
    for step in chip.getkeys('flowgraph', 'signoffflow'):
        for index in chip.getkeys('flowgraph', 'signoffflow', step):
            tool = chip.get('flowgraph', 'signoffflow', step, index, 'tool')
            if tool not in chip.builtin:
                chip.add('checklist', 'oh_tapeout', 'errors_warnings', 'task', ('signoff', step, index))

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
