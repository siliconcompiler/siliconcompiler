import siliconcompiler
from siliconcompiler.targets import freepdk45_demo

def main():
    chip = siliconcompiler.Chip('mkFibOne')
    chip.input('FibOne.bsv')
    chip.set('option', 'frontend', 'bluespec')
    # default Bluespec clock pin is 'CLK'
    chip.clock(pin='CLK', period=5)
    chip.use(freepdk45_demo)
    chip.run()
    chip.summary()
    chip.show()

if __name__ == '__main__':
    main()
