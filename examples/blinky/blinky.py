import siliconcompiler


def main():
    chip = siliconcompiler.Chip('blinky')
    chip.input('blinky.v')
    chip.input('icebreaker.pcf')
    chip.set('fpga', 'partname', 'ice40up5k-sg48')

    chip.add('tool', 'yosys', 'task', 'syn', 'var', 'lut_size', '4')

    chip.load_target("fpgaflow_demo")

    chip.run()
    chip.summary()


if __name__ == '__main__':
    main()
