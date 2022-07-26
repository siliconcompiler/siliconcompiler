# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

import os
import sys
import multiprocessing
import siliconcompiler
import time

# Shared setup routine
def run_design(design, M, job):

    chip = siliconcompiler.Chip(design, loglevel='INFO')
    chip.add('input', 'verilog', design+'.v')
    chip.set('option', 'jobname', job)
    chip.set('option', 'relax', True)
    chip.set('option', 'quiet', True)
    chip.set('arg', 'flow','syn_np', str(M))
    chip.set('arg', 'flow','place_np', str(M))
    chip.set('arg', 'flow','cts_np', str(M))
    chip.set('arg', 'flow','route_np', str(M))
    chip.load_target("freepdk45_demo")
    chip.run()

def main():

    ####################################
    design = 'heartbeat'
    N = 2 # parallel flows, change based on your machine
    M = 2 # parallel indices, change based on your machine

    ####################################
    # 1. All serial

    serial_start = time.time()
    for i in range(N):
        for j in range(M):
            job = f"serial_{i}_{j}"
            run_design(design, 1, job)
    serial_end = time.time()

    ###################################
    # 2. Parallel steps

    parastep_start = time.time()
    for i in range(M):
        job = f"parasteps_{i}"
        run_design(design, M, job)
    parastep_end = time.time()

    ###################################
    # 3. Parallel flows

    paraflow_start = time.time()

    processes = []

    for i in range(N):
        job = f"paraflows_{i}"
        processes.append(multiprocessing.Process(target=run_design,
                                                 args=(design,
                                                       M,
                                                       job)))

    # Boiler plate start and join
    for p in processes:
        p.start()
    for p in processes:
        p.join()

    paraflow_end = time.time()


    ###################################
    # Benchmark calculation

    paraflow_time = round(paraflow_end - paraflow_start,2)
    parastep_time = round(parastep_end - parastep_start,2)
    serial_time = round(serial_end - serial_start,2)

    print(f" Serial = {serial_time}s\n",
          f"Parallel steps = {parastep_time}s\n",
          f"Parallel flows = {paraflow_time}s\n")

if __name__ == '__main__':
    main()
