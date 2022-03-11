import siliconcompiler

def main():
    chip = siliconcompiler.Chip()
    chip.set('source', 'FibOne.bsv')
    chip.set('frontend', 'bluespec')
    chip.set('design', 'mkFibOne')
    # default Bluespec clock pin is 'CLK'
    chip.clock(name='clock', pin='CLK', period=5)
    chip.load_target('freepdk45_demo')
    chip.run()
    chip.summary()
    chip.show()

if __name__ == '__main__':
    main()
