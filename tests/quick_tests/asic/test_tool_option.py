import siliconcompiler

if __name__ != "__main__":
    from tests.fixtures import test_wrapper

def test_tool_option():
    '''Regresttion test for checker being too strict and prevening user from
    setting tool options. Doesn't check any outputs, just that this doesn't fail
    early.'''
    chip = siliconcompiler.Chip()

    gcd_ex_dir = 'examples/gcd/'

    # Inserting value into configuration
    chip.set('design', 'gcd', clobber=True)
    chip.target("freepdk45_asicflow")
    chip.add('source', gcd_ex_dir + 'gcd.v')
    chip.set('clock', 'clock_name', 'pin', 'clk')
    chip.add('constraint', gcd_ex_dir + 'gcd.sdc')
    chip.set('asic', 'diearea', [(0,0), (100.13,100.8)])
    chip.set('asic', 'corearea', [(10.07,11.2), (90.25,91)])
    chip.set('quiet', 'true')
    chip.set('relax', 'true')

    chip.set('eda', 'openroad', 'place', '0', 'option', 'place_density', '0.15')

    # No need to run beyond place, we just want to check that setting place_density
    # doesn't break anything.
    steplist = [
        'import', 
        'syn', 
        'synmin', 
        'floorplan',
        'floorplanmin',
        'physyn',
        'physynmin',
        'place',
        'placemin'
    ]
    chip.set('steplist', steplist)

    # Run the chip's build process synchronously.
    chip.run()
