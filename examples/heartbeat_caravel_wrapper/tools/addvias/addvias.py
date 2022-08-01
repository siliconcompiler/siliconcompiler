import siliconcompiler

def make_docs():
    '''Utility for adding via definitions to a gate-level netlist.'''
    chip = siliconcompiler.Chip('<design>')
    return setup(chip)

def setup(chip):
    tool = 'addvias'
    design = chip.get('design')
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')

    chip.set('tool', tool, 'input', step, index, f'{design}.vg')
    chip.set('tool', tool, 'output', step, index, f'{design}.vg')

def run(chip):
    design = chip.get('design')

    in_mod = False
    done_mod = False
    with open(f'outputs/{design}.vg', 'w') as wf:
      with open(f'inputs/{design}.vg', 'r') as rf:
        for line in rf.readlines():
          if in_mod:
            if line.strip().startswith('endmodule'):
              wf.write(''' VIA_L1M1_PR(vssd1);
 VIA_L1M1_PR(vccd1);
 VIA_L1M1_PR_MR(vssd1);
 VIA_L1M1_PR_MR(vccd1);
 VIA_M1M2_PR(vssd1);
 VIA_M1M2_PR(vccd1);
 VIA_M1M2_PR_MR(vssd1);
 VIA_M1M2_PR_MR(vccd1);
 VIA_M2M3_PR(vssd1);
 VIA_M2M3_PR(vccd1);
 VIA_M2M3_PR_MR(vssd1);
 VIA_M2M3_PR_MR(vccd1);
 VIA_M3M4_PR(vssd1);
 VIA_M3M4_PR(vccd1);
 VIA_M3M4_PR_MR(vssd1);
 VIA_M3M4_PR_MR(vccd1);
 VIA_via2_3_3100_480_1_9_320_320(vssd1);
 VIA_via2_3_3100_480_1_9_320_320(vccd1);
 VIA_via3_4_3100_480_1_7_400_400(vssd1);
 VIA_via3_4_3100_480_1_7_400_400(vccd1);
 VIA_via4_3100x3100(vssd1);
 VIA_via4_3100x3100(vccd1);
 VIA_via4_5_3100_480_1_7_400_400(vssd1);
 VIA_via4_5_3100_480_1_7_400_400(vccd1);\n''')
          elif not done_mod:
            if line.strip().startswith(f'module {design}'):
              in_mod = True
          wf.write(line)

    return 0
