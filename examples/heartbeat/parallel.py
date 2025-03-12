#!/usr/bin/env python3

# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.

import multiprocessing
import time

from siliconcompiler import Chip
from siliconcompiler.targets import freepdk45_demo


# Shared setup routine
def run_design(M, job):
    chip = Chip("heartbeat")
    chip.register_source("heartbeat-example", __file__)
    chip.input("heartbeat.v", package="heartbeat-example")
    chip.input("heartbeat.sdc", package="heartbeat-example")
    chip.set('option', 'jobname', job)
    chip.set('option', 'quiet', True)
    asic_flow_args = {
        'syn_np': M,
        'place_np': M,
        'cts_np': M,
        'route_np': M
    }
    chip.use(freepdk45_demo, **asic_flow_args)
    chip.run()


def all_serial(N=2, M=2):
    serial_start = time.time()
    for i in range(N):
        for j in range(M):
            job = f"serial_{i}_{j}"
            run_design(1, job)
    serial_end = time.time()

    return serial_start, serial_end


def parallel_steps(M=2):
    parastep_start = time.time()
    for i in range(M):
        job = f"parasteps_{i}"
        run_design(M, job)
    parastep_end = time.time()

    return parastep_start, parastep_end


def parallel_flows(N=2, M=2):
    paraflow_start = time.time()

    processes = []

    for i in range(N):
        job = f"paraflows_{i}"
        processes.append(multiprocessing.Process(target=run_design,
                                                 args=(M,
                                                       job)))

    # Boiler plate start and join
    for p in processes:
        p.start()
    for p in processes:
        p.join()

    paraflow_end = time.time()

    return paraflow_start, paraflow_end


def main():

    ####################################
    N = 2  # parallel flows, change based on your machine
    M = 2  # parallel indices, change based on your machine

    ####################################
    # 1. All serial

    serial_start, serial_end = all_serial(N=N, M=M)

    ###################################
    # 2. Parallel steps

    parastep_start, parastep_end = parallel_steps(M=M)

    ###################################
    # 3. Parallel flows

    paraflow_start, paraflow_end = parallel_flows(N=N, M=M)

    ###################################
    # Benchmark calculation

    paraflow_time = round(paraflow_end - paraflow_start, 2)
    parastep_time = round(parastep_end - parastep_start, 2)
    serial_time = round(serial_end - serial_start, 2)

    print(f"Serial = {serial_time}s")
    print(f"Parallel steps = {parastep_time}s")
    print(f"Parallel flows = {paraflow_time}s")


if __name__ == '__main__':
    main()
