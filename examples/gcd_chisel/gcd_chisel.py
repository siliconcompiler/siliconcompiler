import siliconcompiler

def main():
    chip = siliconcompiler.Chip()
    chip.set('source', 'GCD.scala')
    chip.set('frontend', 'chisel')
    chip.set('design', 'GCD')
    # default Chisel clock pin is 'clock'
    chip.clock(name='clock', pin='clock', period=5)
    chip.load_target('freepdk45_demo')
    chip.run()
    chip.summary()
    chip.show()

if __name__ == '__main__':
    main()
