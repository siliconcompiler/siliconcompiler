from siliconcompiler.floorplan import Floorplan, _layer_i

import math

def place_pdn(fp, vdd, vss, hwidth, hspacing, hlayer, vwidth, vspacing,
             vlayer, stdcell_pin_vdd, stdcell_pin_vss, stdcell_pin_width):
   '''Generates PDN for a block-level design. '''
   if vdd not in fp.nets:
       fp.add_net(vdd, [stdcell_pin_vdd], 'power')
   if vss not in fp.nets:
       fp.add_net(vss, [stdcell_pin_vss], 'ground')

   core_left, core_bottom = fp.corearea[0]
   core_right, core_top = fp.corearea[1]

   core_w = core_right - core_left
   core_h = core_top - core_bottom

   vss_ring_left = core_left - 4 * vwidth
   vss_ring_bottom = core_bottom - 4 * hwidth
   vss_ring_width = core_w + 9 * vwidth
   vss_ring_height = core_h + 9 * hwidth

   vdd_ring_left = vss_ring_left + 2 * vwidth
   vdd_ring_bottom = vss_ring_bottom + 2 * hwidth
   vdd_ring_width = vss_ring_width - 4 * vwidth
   vdd_ring_height = vss_ring_height - 4 * hwidth

   fp.place_ring(vdd, vdd_ring_left, vdd_ring_bottom, vdd_ring_width,
                   vdd_ring_height, hwidth, vwidth, hlayer, vlayer)
   fp.place_ring(vss, vss_ring_left, vss_ring_bottom, vss_ring_width,
                   vss_ring_height, hwidth, vwidth, hlayer, vlayer)
   # Horizontal stripes
   spacing = 2 * (hspacing + hwidth)
   n_hori = int(core_h // (hspacing + hwidth))

   bottom = core_bottom + hspacing
   fp.place_wires([vdd] * (n_hori // 2), vdd_ring_left, bottom, 0, spacing,
               vdd_ring_width, hwidth, hlayer, shape='stripe')

   bottom = core_bottom + hspacing + (hspacing + hwidth)
   fp.place_wires([vss] * (n_hori // 2), vss_ring_left, bottom, 0, spacing,
               vss_ring_width, hwidth, hlayer, shape='stripe')

   # Vertical stripes
   spacing = 2 * (vspacing + vwidth)
   n_vert = int(core_w // (vspacing + vwidth))

   left = core_left + vspacing
   fp.place_wires([vdd] * (n_vert // 2), left, vdd_ring_bottom, spacing, 0,
               vwidth, vdd_ring_height, vlayer, shape='stripe')

   left = core_left + vspacing + (vspacing + vwidth)
   fp.place_wires([vss] * (n_vert // 2), left, vss_ring_bottom, spacing, 0,
               vwidth, vss_ring_height, vlayer, shape='stripe')

   # Power stripes
   rows = len(fp.rows)
   npwr = 1 + math.floor(rows / 2)
   ngnd = math.ceil(rows / 2)

   # TODO: infer stripe_w from LEF
   stripe_w = stdcell_pin_width
   mainlib = fp.chip.get('asic', 'logiclib')[0]
   stripe_layer = fp.chip.get('library', mainlib, 'pgmetal')
   spacing = 2 * fp.stdcell_height

   bottom = core_bottom - stripe_w/2
   fp.place_wires([vdd] * npwr, core_left, bottom, 0, spacing,
                    core_w, stripe_w, stripe_layer, 'followpin')

   bottom = core_bottom - stripe_w/2 + fp.stdcell_height
   fp.place_wires([vss] * ngnd, core_left, bottom, 0, spacing,
                    core_w, stripe_w, stripe_layer, 'followpin')

   vlayer_i = _layer_i(fp.layers[vlayer]['sc_name'])
   hlayer_i = _layer_i(fp.layers[hlayer]['sc_name'])
   if vlayer_i > hlayer_i:
       gridlayers = hlayer, vlayer
   else:
       gridlayers = vlayer, hlayer
   fp.insert_vias(layers=[(stripe_layer, vlayer), gridlayers])

def generate_block_floorplan(fp, diearea, corearea, inputs, outputs, pdn=None):
   '''Generate a basic floorplan for a block-level design. '''
   fp.create_diearea(diearea, corearea)

   input_pins = []
   for name, width in inputs:
       if width > 1:
           input_pins.extend([f'{name}[{i}]' for i in range(width)])
       else:
           input_pins.append(name)

   output_pins = []
   for name, width in outputs:
       if width > 1:
           output_pins.extend([f'{name}[{i}]' for i in range(width)])
       else:
           output_pins.append(name)

   layer = fp.chip.get('asic', 'hpinlayer')
   width = fp.layers[layer]['width']
   depth = 3 * width

   die_width, die_height = diearea[1]
   in_spacing = (die_height - len(input_pins) * width) / (len(input_pins) + 1)
   fp.place_pins(input_pins, 0, in_spacing, 0, in_spacing + width, depth, width, layer, snap=True)

   out_spacing = (die_height - len(output_pins) * width) / (len(output_pins) + 1)
   fp.place_pins(output_pins, die_width-depth, out_spacing, 0, out_spacing + width, depth, width, layer, snap=True)

   if pdn:
       place_pdn(fp, **pdn)

   return pdn

def make_floorplan(chip):
    fp = Floorplan(chip)

    diearea = [(0, 0), (200.56, 201.28)]
    corearea = [(20.24, 21.76), (180.32, 184.96)]
    inputs = [
        ('clk', 1),
        ('req_val', 1),
        ('reset', 1),
        ('resp_rdy', 1),
        ('req_msg', 32)
    ]
    outputs = [
        ('req_rdy', 1),
        ('resp_val', 1),
        ('resp_msg', 16)
    ]
    pdn_params = {
        'vdd': 'vdd',
        'vss': 'vss',
        'hwidth': 2,
        'hspacing': 10,
        'hlayer': 'm5',
        'vwidth': 2,
        'vspacing': 10,
        'vlayer': 'm4',
        'stdcell_pin_vdd': 'VPWR',
        'stdcell_pin_vss': 'VGND',
        'stdcell_pin_width': 0.48
    }

    generate_block_floorplan(fp, diearea, corearea, inputs, outputs, pdn_params)
    fp.write_def('gcd.def')
    return 'gcd.def'
