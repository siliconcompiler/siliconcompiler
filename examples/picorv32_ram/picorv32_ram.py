#!/usr/bin/env python3

from siliconcompiler import Chip
from siliconcompiler.targets import skywater130_demo

try:
    from . import sky130_sram_2k
except:  # noqa E722
    import sky130_sram_2k


def build_top():
    # Core settings.
    target = skywater130_demo
    die_w = 1000
    die_h = 1000

    # Create Chip object.
    chip = Chip('picorv32_top')

    # Set default Skywater130 PDK / standard cell lib / flow.
    chip.use(target)

    # Set design source files.
    chip.register_source("picorv-ram-example", __file__)
    chip.input("picorv32_top.v", package="picorv-ram-example")
    chip.register_source(name='picorv32',
                         path='git+https://github.com/YosysHQ/picorv32.git',
                         ref='c0acaebf0d50afc6e4d15ea9973b60f5f4d03c42')
    chip.input("picorv32.v", package='picorv32')

    # Optional: silence each task's output in the terminal.
    chip.set('option', 'quiet', True)

    # Set die outline and core area.
    margin = 10
    chip.set('constraint', 'outline', [(0, 0), (die_w, die_h)])
    chip.set('constraint', 'corearea', [(margin, margin),
                                        (die_w - margin, die_h - margin)])

    # Setup SRAM macro library.
    chip.use(sky130_sram_2k, stackup=chip.get('option', 'stackup'))
    chip.add('asic', 'macrolib', 'sky130_sram_2k')

    # SRAM pins are inside the macro boundary; no routing blockage padding is needed.
    chip.set('tool', 'openroad', 'task', 'route', 'var', 'grt_macro_extension', '0')
    # Disable CDL file generation until we can find a CDL file for the SRAM block.
    chip.set('tool', 'openroad', 'task', 'export', 'var', 'write_cdl', 'false')
    # Reduce placement density a bit to ease routing congestion and to speed up the route step.
    chip.set('tool', 'openroad', 'task', 'place', 'var', 'place_density', '0.5')

    # Place macro instance.
    chip.set('constraint', 'component', 'sram', 'placement', (150, 150))
    chip.set('constraint', 'component', 'sram', 'rotation', 'R180')

    # Set clock period, so that we won't need to provide an SDC constraints file.
    chip.clock('clk', period=30)

    # Run the build.
    chip.set('option', 'remote', False)
    chip.set('option', 'quiet', False)

    chip.run()

    # Print results.
    chip.summary()

    return chip


if __name__ == '__main__':
    build_top()
