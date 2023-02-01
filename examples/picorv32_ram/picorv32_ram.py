
import importlib
import os
import siliconcompiler

if __name__ == '__main__':
    # Core settings.
    design = 'picorv32'
    target = 'skywater130_demo'
    die_w = 1000
    die_h = 1000

    # Create Chip object.
    chip = siliconcompiler.Chip(design)

    # Set default Skywater130 PDK / standard cell lib / flow.
    target_module = importlib.import_module(f'targets.{target}')
    chip.use(target_module)

    # Set design source files.
    rootdir = os.path.dirname(__file__)
    chip.input(os.path.join(rootdir, f"{design}.v"))
    chip.input(os.path.join(rootdir, f"{design}.sdc"))

    # Optional: Relax linting and/or silence each task's output in the terminal.
    chip.set('option', 'relax', True)
    #chip.set('option', 'quiet', True)

    # Set die outline and core area.
    chip.set('constraint', 'outline', [(0,0), (die_w, die_h)])
    chip.set('constraint', 'corearea', [(10,10), (die_w-10, die_h-10)])

    # Run the build.
    chip.run()

    # Print results.
    chip.summary()

    # Display final result.
    chip.show()
