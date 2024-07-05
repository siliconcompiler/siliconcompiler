# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import re
import siliconcompiler


def main(limit=0):
    # Setting up the experiment
    design = 'oh_add'
    N = 8

    # Plugging design into SC
    chip = siliconcompiler.Chip(design)
    chip.register_source('oh',
                         'git+https://github.com/aolofsson/oh',
                         '23b26c4a938d4885a2a340967ae9f63c3c7a3527')
    chip.input('mathlib/hdl/' + design + '.v', package='oh')
    chip.set('option', 'param', 'N', str(N))
    chip.set('option', 'quiet', True)
    chip.load_target("freepdk45_demo")

    # First run (import + run)
    chip.set('option', 'to', ['syn'])
    chip.run()

    itr = 0
    # Setting up the rest of the runs
    while True:

        # design experiment, width of adder
        N = N * 2
        chip.set('option', 'param', 'N', str(N), clobber=True)

        # Running syn only
        index = '0'
        step = 'syn'
        chip.set('option', 'from', ['syn'])
        chip.set('option', 'to', ['syn'])

        # Setting a unique jobid
        oldid = chip.get('option', 'jobname')
        match = re.match(r'(.*)(\d+)$', oldid)
        newid = match.group(1) + str(int(match.group(2)) + 1)
        chip.set('option', 'jobname', newid)

        # Specifying that imports are copied from job0
        chip.set('option', 'jobinput', step, index, 'job0')

        # Make a run
        chip.run()

        # Query current run and last run
        new_area = chip.get('metric', 'cellarea', step=step, index=index)
        old_area = chip.get('metric', 'cellarea', job=oldid, step=step, index=index)

        # compare result
        print(N, new_area, old_area, newid, chip.get('option', 'jobname'))
        if (new_area / old_area) > 2.1:
            print("Stopping, area is exploding")
            break

        if limit > 0 and itr > limit:
            break

        itr += 1


if __name__ == '__main__':
    main()
