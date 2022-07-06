import siliconcompiler

import os
import sys

from sky130_floorplan import make_floorplan

def main():
    '''GCD example with custom floorplan and signoff steps.'''

    # Create instance of Chip class
    chip = siliconcompiler.Chip("gcd")

    chip.add('input', 'verilog', 'gcd.v')
    chip.set('option', 'relax', True)
    chip.set('option', 'quiet', True)

    chip.clock('clk', period=5)

    chip.load_target("skywater130_demo")

    chip.set('datasheet', chip.get_entrypoint(), 'pin', 'vdd', 'type', 'global', 'power')
    chip.set('datasheet', chip.get_entrypoint(), 'pin', 'vss', 'type', 'global', 'ground')

    # 1) RTL2GDS

    def_path = make_floorplan(chip)
    chip.set('input', 'floorplan.def', def_path)

    chip.set('option', 'jobname', 'rtl2gds')
    chip.run()
    chip.summary()

    gds_path = chip.find_result('gds', step='export')
    vg_path = chip.find_result('vg', step='dfm')

    # 2) Signoff

    chip.set('option', 'jobname', 'signoff')
    chip.set('option', 'flow', 'signoffflow')

    chip.set('input', 'gds', gds_path)
    chip.set('input', 'netlist', vg_path)

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
