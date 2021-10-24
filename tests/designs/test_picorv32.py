import os
import siliconcompiler

if __name__ != "__main__":
    import tests.fixtures

# Command line version
# sc ../../third_party/designs/picorv32/picorv32.v -design picorv32 -mode sim -target "surelog" -arg_step "import" -quiet

def test_picorv32():
    localdir = os.path.dirname(os.path.abspath(__file__))
    source = localdir + "/../../third_party/designs/picorv32/picorv32.v"
    design = "picorv32"
    step = "import"

    chip = siliconcompiler.Chip(loglevel="INFO")

    chip.add('source', source)
    chip.set('design', design)
    chip.set('steplist', ['import'])
    chip.set('mode', 'sim')
    chip.set('arg', 'step', step)
    chip.target('surelog')

    chip.set('steplist', ['import'])
    chip.run()

    assert chip.find_result('v', step=step) is not None

if __name__ == "__main__":
    test_picorv32()
