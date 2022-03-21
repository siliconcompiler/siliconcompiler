import os
import sys
import time
import siliconcompiler

# Setting up the experiment

def main():
    rootdir = os.path.dirname(__file__)
    target = "skywater130_demo"
    jobname = 'job0'

    examples = [{'heartbeat' : 1000},
                {'picorv32' : 1000},
                {'aes' : 1500}]

    results = {}

    for item in examples:
        design = list(item.keys())[0]
        size = list(item.values())[0]
        parent = os.path.abspath("..")
        rootdir = os.path.join(parent, design)
        results[design] = {}
        for n in ['1','2','4','8','16']:
            wall_start = time.time()
            chip = siliconcompiler.Chip(design)
            chip.set('jobname', f"job{n}")
            chip.load_target('skywater130_demo')
            chip.set('relax', True)
            chip.set('quiet', True)
            chip.set('remote',False)

            # load dsign
            chip.add('source', os.path.join(rootdir, f"{design}.v"))
            chip.add('constraint', os.path.join(rootdir, f"{design}.sdc"))
            chip.set('asic', 'diearea', [(0,0), (size,size)])
            chip.set('asic', 'corearea', [(10,10), (size-10,size-10)])

            # load flow
            chip.set('flowarg', 'syn_np', n)
            chip.set('flowarg', 'place_np', n)
            chip.set('flowarg', 'cts_np', n)
            chip.load_flow('asicflow')
            chip.set('flow', 'asicflow')

            # Set router to 1 thread to not interfere with measurement
            for i in range(int(n)):
                chip.set('eda','openroad','threads', 'route',str(i),1)

            #RUN
            chip.run()

            #OBSERVE/RECORD
            chip.summary()
            wall_end = time.time()
            walltime = round((wall_end - wall_start),2)
            results[design][n] = walltime
            with open(f"results.txt", 'w') as f:
                print(results, file=f)

if __name__ == '__main__':
    main()
