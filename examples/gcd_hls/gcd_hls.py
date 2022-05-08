import siliconcompiler

def main():
    chip = siliconcompiler.Chip('gcd')
    chip.set('source', 'c', 'gcd.c')
    chip.set('frontend', 'c')
    # default Bambu clock pin is 'clock'
    #chip.clock(name='clock', pin='clock', period=5)
    chip.load_target('freepdk45_demo')
    chip.run()
    chip.summary()
    chip.show()

if __name__ == '__main__':
    main()
