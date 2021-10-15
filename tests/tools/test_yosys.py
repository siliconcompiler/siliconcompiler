import siliconcompiler
import os

if __name__ != "__main__":
    from tests.fixtures import test_wrapper

def test_yosys_lec():
    localdir = os.path.dirname(os.path.abspath(__file__))
    lec_dir = f"{localdir}/../data/lec"

    chip = siliconcompiler.Chip()

    chip.set('arg', 'step', 'lec')
    chip.set('design', 'foo')
    chip.set('mode', 'asic')
    chip.target('yosys_freepdk45')

    chip.add('source', f'{lec_dir}/foo.v')
    chip.add('source', f'{lec_dir}/foo.vg')

    chip.run()

    errors = chip.get('metric', 'lec', '0', 'errors', 'real')

    assert errors == 0

def test_yosys_lec_broken():
    localdir = os.path.dirname(os.path.abspath(__file__))
    lec_dir = f"{localdir}/../data/lec"

    chip = siliconcompiler.Chip()

    chip.set('arg', 'step', 'lec')
    chip.set('design', 'foo_broken')
    chip.set('mode', 'asic')
    chip.target('yosys_freepdk45')

    chip.add('source', f'{lec_dir}/foo_broken.v')
    chip.add('source', f'{lec_dir}/foo_broken.vg')

    chip.run()

    errors = chip.get('metric', 'lec', '0', 'errors', 'real')

    assert errors == 2

if __name__ == "__main__":
    test_yosys_lec()
