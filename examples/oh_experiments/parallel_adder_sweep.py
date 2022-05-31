# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

import siliconcompiler

import os
import multiprocessing

# Setting up the experiment

# unit routine
def run_design(rootdir, design, N, job):

    chip = siliconcompiler.Chip(design)
    chip.set('design', design)
    chip.add('source', 'verilog', rootdir+'/stdlib/hdl/'+design+'.v')
    chip.set('option', 'param', 'N', str(N))
    chip.set('option', 'jobname', job)
    chip.set('option', 'relax', True)
    chip.set('option', 'quiet', True)
    chip.set('option', 'steplist', ['import', 'syn'])
    chip.load_target('freepdk45_demo')
    chip.run()
    #chip.summary()

def main():

    rootdir = (os.path.dirname(os.path.abspath(__file__)) +
           "/../../third_party/designs/oh/")
    design = 'oh_add'
    N = [4, 8, 16, 32, 64, 128]

    # Define parallel processingg
    processes = []
    for i in range(len(N)):
        job = 'job' + str(i)
        processes.append(multiprocessing.Process(target=run_design,
                                                args=(rootdir,
                                                      design,
                                                      str(N[i]),
                                                      job
                                                )))


    # Boiler plate start and join
    for p in processes:
        p.start()
    for p in processes:
        p.join()

    # Post-processing data
    print("-"*80)
    chip = siliconcompiler.Chip()
    for i in range(len(N)):
        jobname = 'job'+str(i)
        chip.read_manifest(f"build/{design}/{jobname}/syn/0/outputs/{design}.pkg.json", job=jobname)
        area = chip.get('metric','syn','0', 'cellarea','real', job=jobname)
        print(design, ", N =", N[i], ", cellarea =",area)

if __name__ == '__main__':
    main()
