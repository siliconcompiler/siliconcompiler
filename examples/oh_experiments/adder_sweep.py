import siliconcompiler

import os

try:
    import matplotlib.pyplot as plt
    has_matplotlib = True
except ImportError:
    has_matplotlib = False

oh_dir = "../../third_party/designs/oh/"

def main():
    # datawidths to check
    datawidths = [8,16,32,64]
    source = os.path.join(oh_dir, 'mathlib', 'hdl', 'oh_add.v')
    design = 'oh_add'

    # Gather Data
    area = []
    for n in datawidths:
        chip = siliconcompiler.Chip(design)
        chip.load_target('freepdk45_demo')
        chip.add('source', 'verilog', source)
        chip.set('option', 'quiet', True)
        chip.set('option','relax', True)
        chip.set('option','steplist', ['import', 'syn'])
        chip.set('option','param','N',str(n))
        chip.run()

        area.append(chip.get('metric', 'syn', '0', 'cellarea', 'real'))

    if has_matplotlib:
        # Plot Data
        fig, ax = plt.subplots(1, 1)

        plt.plot(datawidths, area)
        plt.show()
    else:
        print('areas:', area)
        print('Install matplotlib to automatically plot this data!')
        return area

if __name__ == '__main__':
    main()
