# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

import os
import sys
import multiprocessing
import siliconcompiler

# Setting up the experiment
rootdir = (os.path.dirname(os.path.abspath(__file__)) +
           "/../../third_party/designs/oh/")
design = 'oh_add'
library = 'mathlib'
width = 100
height = 100
N = [4, 8, 16, 32, 64, 128]

# unit routine
def run_design(rootdir, design, N, i):

    chip = siliconcompiler.Chip(loglevel='INFO')
    chip.set('design', design)
    chip.add('source', rootdir+'/mathlib/hdl/'+design+'.v')
    chip.set('param', 'N', str(N))
    chip.set('jobid', i)
    chip.set('relax', True)
    chip.set('quiet', True)
    chip.set('steplist', ['import', 'syn'])
    chip.target("asicflow_freepdk45")
    chip.run()
    #chip.summary()

def main():
    # Define parallel processingg
    processes = []
    for i in range(len(N)):
        processes.append(multiprocessing.Process(target=run_design,
                                                args=(rootdir,
                                                    design,
                                                    str(N[i]),
                                                    i
                                                )))


    # Boiler plate start and join
    for p in processes:
        p.start()
    for p in processes:
        p.join()

    # Post-processing data
    print("-"*80)
    for i in range(len(N)):
        chip = siliconcompiler.Chip()
        chip.read_manifest(f"build/{design}/job{str(i)}/syn0/outputs/{design}.pkg.json")
        print(design, ", N =", N[i], ", cellarea =", chip.get('metric','syn','0','cellarea','real'))

if __name__ == '__main__':
    main()
