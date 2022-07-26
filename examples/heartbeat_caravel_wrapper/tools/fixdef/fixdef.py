import siliconcompiler

def make_docs():
    '''Utility for covering 'pin' data types with 'drawing' data types in a DEF
    file. This is required for the eFabless MPW prechecks, because the mask
    production process does not include 'pin' data types, and the main DRCs can
    miss open circuits by counting those data types as valid connections.
    '''
    chip = siliconcompiler.Chip('<design>')
    return setup(chip)

def setup(chip):
    tool = 'fixdef'
    design = chip.get('design')
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')

    chip.set('tool', tool, 'input', step, index, f'{design}.def')
    chip.set('tool', tool, 'output', step, index, f'{design}.def')

def run(chip):
    design = chip.get('design')
    with open(f'inputs/{design}.def') as f:
        with open(f'outputs/{design}.def', 'w') as wf:
            # State-tracking variables for parsing the file.
            in_pins = 0
            in_pin = ''
            in_net = ''
            in_layer = ''
            pin_w = 0
            pin_h = 0
            pin_locs = {}

            # Process the file one line at a time:
            # 1. Gather information about pin polys.
            # 2. Add overlaps in the 'SPECIALNETS' section.
            # Assumptions: 'PINS' comes before 'SPECIALNETS', and there is only one 'PINS' section.
            for line in f:
                l = line

                # We don't care about lines before the 'PINS' section; write them verbatim to new DEF.
                if not in_pins:
                    wf.write(l)
                    # Start paying attention at the start of the 'PINS' section.
                    if l.strip().startswith('PINS'):
                        in_pins = 1
                # Note name, dimensions, and net of each non-power pin. (Power nets should go thru PDN)
                elif in_pins == 1:
                    wf.write(l)
                    if l.strip().startswith('END PINS'):
                        in_pins = 2
                    elif l.strip().startswith('-'):
                        la = l.strip().split()
                        in_pin = la[1]
                        in_net = la[4]
                    # TODO: We should not use hardcoded prefixes for power nets to ignore.
                    elif ('LAYER' in l) and (not 'vcc' in in_pin) and (not 'vss' in in_pin):
                        la = l.strip().split()
                        in_layer = la[2]
                        pin_w = abs(int(la[8]) - int(la[4]))
                        pin_h = abs(int(la[9]) - int(la[5]))
                    elif ('PLACED' in l) and (not 'vcc' in in_pin) and (not 'vss' in in_pin):
                        la = l.strip().split()
                        pin_locs[in_pin] = {'layer': in_layer,
                                            'net': in_net,
                                            'x': int(la[3]),
                                            'y': int(la[4]),
                                            'w': pin_w,
                                            'h': pin_h}
                # After the 'PINS' section, look for 'SPECIALNETS' section and add tracks over each pin.
                # This section may not exist; create it if we find 'END NETS' before 'SPECIALNETS'
                elif in_pins == 2:
                    if l.strip().startswith('SPECIALNETS'):
                        la = l.strip().split()
                        numnets = int(la[1]) + len(pin_locs)
                        wf.write('SPECIALNETS %i ;\n'%numnets)
                    # (There may not be a SPECIALNETS section in the DEF output)
                    elif l.strip().startswith('END NETS'):
                        wf.write(l)
                        numnets = len(pin_locs)
                        wf.write('SPECIALNETS %i ;\n'%numnets)
                    elif (l.strip() == 'END SPECIALNETS') or (l.strip() == 'END DESIGN'):
                        for k, v in pin_locs.items():
                            ml = 0
                            if v['layer'] == 'met2':
                                ml = v['w']
                                xl = v['x']
                                xr = v['x']
                                yb = int(v['y'] - v['h'] / 2)
                                yu = int(v['y'] + v['h'] / 2)
                            elif v['layer'] == 'met3':
                                ml = v['h']
                                xl = int(v['x'] - v['w'] / 2)
                                xr = int(v['x'] + v['w'] / 2)
                                yb = v['y']
                                yu = v['y']
                            wf.write('    - %s ( PIN %s ) + USE SIGNAL\n'%(v['net'], k))
                            wf.write('      + ROUTED %s %i + SHAPE STRIPE ( %i %i ) ( %i %i )\n'%(v['layer'], int(ml), xl, yb, xr, yu))
                            wf.write('      NEW %s %i + SHAPE STRIPE ( %i %i ) ( %i %i ) ;\n'%(v['layer'], int(ml), xl, yb, xr, yu))
                        if l.strip() == 'END DESIGN':
                            wf.write('END SPECIALNETS\n')
                        wf.write(l)
                        in_pins = 3
                    else:
                        wf.write(l)
                elif in_pins == 3:
                    wf.write(l)

    return 0
