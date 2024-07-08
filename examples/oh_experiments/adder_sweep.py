import os
import siliconcompiler

try:
    import matplotlib.pyplot as plt
    has_matplotlib = True
except ImportError:
    has_matplotlib = False

root = os.path.dirname(__file__)


def main():
    # datawidths to check
    datawidths = [8, 16, 32, 64]
    source = os.path.join('mathlib', 'hdl', 'oh_add.v')
    design = 'oh_add'

    # Gather Data
    area = []
    for n in datawidths:
        chip = siliconcompiler.Chip(design)
        chip.register_source('oh',
                             'git+https://github.com/aolofsson/oh',
                             '23b26c4a938d4885a2a340967ae9f63c3c7a3527')
        chip.load_target("freepdk45_demo")
        chip.input(source, package='oh')
        chip.set('option', 'quiet', True)
        chip.set('option', 'to', ['syn'])
        chip.set('option', 'param', 'N', str(n))
        chip.run()

        area.append(chip.get('metric', 'cellarea', step='syn', index='0'))

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
