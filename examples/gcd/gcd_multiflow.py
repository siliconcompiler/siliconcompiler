#!/usr/bin/env python3
# This test does not work at the moment (Jan 4, 2023)

import siliconcompiler

def main():
    '''GCD example with multiflow.'''

    # Create instance of Chip class
    chip = siliconcompiler.Chip('gcd', loglevel='INFO')

    chip.add('input', 'verilog', 'gcd.v')
    chip.add('input', 'sdc', 'gcd.sdc')
    chip.set('option', 'relax', True)
    chip.set('option', 'quiet', True)
    chip.set('option', 'skipcheck', True)

    chip.load_target("skywater130_demo")

    #IMPORT
    #APR
    chip.pipe('apr', [{'import' : 'nop'},
                      {'syn' : 'yosys'},
                      {'floorplan' : 'openroad'},
                      {'physyn' : 'openroad'},
                      {'place' : 'openroad'},
                      {'cts' : 'openroad'},
                      {'route' : 'openroad'},
                      {'dfm' : 'openroad'},
                      {'export' : 'klayout'}])

    #SIGNOFF
    chip.node('signoff', 'import', 'nop')
    chip.node('signoff', 'extspice', 'magic')
    chip.node('signoff', 'drc', 'magic')
    chip.node('signoff', 'lvs', 'netgen')
    chip.node('signoff', 'export', 'join')

    chip.edge('signoff', 'import', 'drc')
    chip.edge('signoff', 'import', 'extspice')
    chip.edge('signoff', 'extspice', 'lvs')
    chip.edge('signoff', 'lvs', 'export')
    chip.edge('signoff', 'drc', 'export')

    #TOP
    #TODO: note that import has to be placed first, otherwise
    #defaults won't be there.(need a better way!)
    chip.node('top','import', 'surelog')
    chip.graph("top","apr", name="apr")
    chip.graph("top","signoff", name="dv")
    chip.write_manifest("top0.tcl")
    chip.edge('top','import','apr')
    chip.edge("top", "apr", "dv")
    chip.set('option', 'flow', 'top')
    chip.write_flowgraph("top.png")
    chip.write_manifest("top.tcl")

    chip.run()
    chip.summary()

if __name__ == '__main__':
    main()
