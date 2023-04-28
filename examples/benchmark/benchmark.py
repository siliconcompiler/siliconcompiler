import os
import time
import siliconcompiler
from siliconcompiler.flows import asicflow

# Setting up the experiment

def main():
    rootdir = os.path.dirname(__file__)

    examples = [{'heartbeat': 1000},
                {'picorv32': 1000},
                {'aes': 1500}]

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
            chip.load_target("skywater130_demo")
            chip.set('relax', True)
            chip.set('quiet', True)
            chip.set('remote',False)

            # load dsign
            chip.input(os.path.join(rootdir, f"{design}.v"))
            chip.input(os.path.join(rootdir, f"{design}.sdc"))
            chip.set('constraint', 'outline', [(0,0), (size,size)])
            chip.set('constraint', 'corearea', [(10,10), (size-10,size-10)])

            # load flow
            chip.set('flowarg', 'syn_np', n)
            chip.set('flowarg', 'place_np', n)
            chip.set('flowarg', 'cts_np', n)
            chip.use(asicflow)
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
            with open("results.txt", 'w') as f:
                f.write(results)

if __name__ == '__main__':
    main()
