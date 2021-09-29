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

    print(gcd_src)
    chip.add('source', gcd_src)
    chip.set('design', design)
    chip.set('mode', 'sim')
    chip.set('arg', 'step', step)
    chip.target('surelog')

    chip.run()

    assert os.path.isfile(f"build/{design}/job0/{step}0/outputs/{design}.v")

if __name__ == "__main__":
    test_surelog()
