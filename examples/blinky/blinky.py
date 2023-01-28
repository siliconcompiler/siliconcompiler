import siliconcompiler
from siliconcompiler.targets import fpgaflow_demo

def main():
    chip = siliconcompiler.Chip('blinky')
    chip.input('blinky.v')
    chip.input('icebreaker.pcf')
    chip.set('fpga', 'partname', 'ice40up5k-sg48')
    chip.use(fpgaflow_demo)

    chip.run()
    chip.summary()

if __name__ == '__main__':
    main()
