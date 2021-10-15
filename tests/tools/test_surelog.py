import os
import siliconcompiler

if __name__ != "__main__":
    import tests.fixtures

def test_surelog():
    localdir = os.path.dirname(os.path.abspath(__file__))
    gcd_src = localdir + '/../../examples/gcd/gcd.v'
    design = "gcd"
    step = "import"

    chip = siliconcompiler.Chip(loglevel="INFO")

    chip.add('source', gcd_src)
    chip.set('design', design)
    chip.set('mode', 'sim')
    chip.set('arg', 'step', step)
    chip.target('surelog')

    chip.run()

    assert chip.find_result('v', step=step) is not None

if __name__ == "__main__":
    test_surelog()
