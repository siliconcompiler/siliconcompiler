import siliconcompiler

from siliconcompiler.targets import lattice_ice40_fpga_demo


def main():
    chip = siliconcompiler.Chip('blinky')
    chip.input('blinky.v')
    chip.input('icebreaker.pcf')
    chip.set('fpga', 'partname', 'ice40up5k-sg48')

    chip.load_target(lattice_ice40_fpga_demo)

    chip.run()
    chip.summary()


if __name__ == '__main__':
    main()
