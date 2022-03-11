# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

import os
import re
import siliconcompiler

def main():
    # Setting up the experiment
    rootdir = (os.path.dirname(os.path.abspath(__file__)) +
               "/../../third_party/designs/oh/")

    design = 'oh_add'
    N = 8

    # Plugging design into SC
    chip = siliconcompiler.Chip(loglevel='INFO')
    chip.set('design', design)
    chip.add('source', rootdir+'/stdlib/hdl/'+design+'.v')
    chip.set('param', 'N', str(N))
    chip.set('relax', True)
    chip.set('quiet', True)
    chip.load_target('freepdk45_demo')

    # First run (import + run)
    steplist = ['import', 'syn']
    chip.set('steplist', steplist)
    chip.run()


    # Setting up the rest of the runs
    while True:

        # design experiment, width of adder
        N = N * 2
        chip.set('param', 'N', str(N), clobber=True)

        # Running syn only
        index = '0'
        step = 'syn'
        chip.set('steplist', ['syn'])

        # Setting a unique jobid
        oldid = chip.get('jobname')
        match = re.match(r'(.*)(\d+)$', oldid)
        newid = match.group(1) + str(int(match.group(2))+1)
        chip.set('jobname', newid)

        # Specifying that imports are copied from job0
        chip.set('jobinput', newid, step, index, 'job0')

        # Make a run
        chip.run()

        # Query current run and last run
        new_area = chip.get('metric', step, index, 'cellarea','real')
        old_area = chip.get('metric', step, index, 'cellarea','real', job=oldid)

        # compare result
        print(N, new_area, old_area, newid, chip.get('jobname'))
        if (new_area/old_area) > 2.1:
            print("Stopping, area is exploding")
            break

if __name__ == '__main__':
    main()
