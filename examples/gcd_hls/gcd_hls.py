import siliconcompiler
from siliconcompiler.targets import freepdk45_demo

def main():
    chip = siliconcompiler.Chip('gcd')
    chip.input('gcd.c')
    chip.set('option', 'frontend', 'c')
    # default Bambu clock pin is 'clock'
    chip.clock(pin='clock', period=5)
    chip.use(freepdk45_demo)
    chip.run()
    chip.summary()
    chip.show()

if __name__ == '__main__':
    main()
