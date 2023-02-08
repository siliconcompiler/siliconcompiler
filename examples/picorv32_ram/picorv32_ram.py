import os
import siliconcompiler

def build_top(remote=False):
    # Core settings.
    design = 'picorv32_top'
    target = 'skywater130_demo'
    die_w = 1000
    die_h = 1000

    # Create Chip object.
    chip = siliconcompiler.Chip(design)

    # Set default Skywater130 PDK / standard cell lib / flow.
    chip.load_target(target)

    # Set design source files.
    rootdir = os.path.dirname(__file__)
    chip.input(os.path.join(rootdir, f"{design}.v"))
    chip.input(os.path.join(rootdir, "../picorv32/picorv32.v"))
    chip.input(os.path.join(rootdir, "sky130_sram_2k.bb.v"))
    chip.input(os.path.join(rootdir, f"{design}.sdc"))

    # Optional: Relax linting and/or silence each task's output in the terminal.
    chip.set('option', 'relax', True)
    chip.set('option', 'quiet', True)

    # Set die outline and core area.
    chip.set('constraint', 'outline', [(0,0), (die_w, die_h)])
    chip.set('constraint', 'corearea', [(10,10), (die_w-10, die_h-10)])

    # Setup SRAM macro library.
    from sram import sky130_sram_2k
    chip.use(sky130_sram_2k)
    chip.add('asic', 'macrolib', 'sky130_sram_2k')

    # SRAM pins are inside the macro boundary; no routing blockage padding is needed.
    chip.set('tool', 'openroad', 'task', 'route', 'var', 'grt_macro_extension', '0')
    # Disable CDL file generation until we can find a CDL file for the SRAM block.
    chip.set('tool', 'openroad', 'task', 'export', 'var', 'write_cdl', 'false')
    # Reduce placement density a bit to ease routing congestion and hopefully speed up the route step.
    chip.set('tool', 'openroad', 'task', 'place', 'var', 'place_density', '0.5')

    # Place macro instance.
    chip.set('constraint', 'component', 'sram', 'placement', (500.0, 250.0, 0.0))
    chip.set('constraint', 'component', 'sram', 'rotation', 270)

    # Optional: build remotely.
    chip.set('option', 'remote', remote)

    return chip

if __name__ == '__main__':
    # Prepare Chip object.
    chip = build_top()
    # Run the build.
    chip.run()
    # Print results.
    chip.summary()
    # Display results.
    chip.show()
