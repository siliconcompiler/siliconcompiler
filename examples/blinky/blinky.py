import siliconcompiler

def main():
    chip = siliconcompiler.Chip()
    chip.set('source', 'blinky.v')
    chip.set('design', 'blinky')
    chip.set('constraint', 'icebreaker.pcf')
    chip.set('fpga', 'partname', 'ice40up5k-sg48')
    chip.load_target('fpgaflow_demo')

    chip.run()
    chip.summary()

if __name__ == '__main__':
    main()
