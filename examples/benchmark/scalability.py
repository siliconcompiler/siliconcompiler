#!/usr/bin/env python3

'''Benchmark to measure time taken per simple task with large flowgraphs.

$ ./examples/benchmark/scalability.py serial <N> <S>
Runs a serial flowgraph with N tasks and output "done" after S steps.

$ ./examples/benchmark/scalability.py parallel <N>
Runs a parallel flowgraph with N parallel tasks.
'''

import siliconcompiler
import argparse
from siliconcompiler.tools.builtin import nop


def run_long_serial(N, steps_to_run):
    chip = siliconcompiler.Chip('test_long_serial')
    flow = 'test_long_serial'
    pipe = [{'import': nop}]
    pipe += [{f'measured{i}': nop} for i in range(steps_to_run - 1)]
    pipe += [{'done': nop}]
    pipe += [{f'extra{i}': nop} for i in range(N - (steps_to_run + 1))]

    chip.set('option', 'flow', flow)
    chip.set('option', 'mode', 'sim')
    chip.pipe(flow, pipe)
    chip.run()


def run_wide_parallel(N):
    chip = siliconcompiler.Chip('test_long_serial')
    flow = 'test_long_parallel'

    chip.node(flow, 'import', nop)
    chip.node(flow, 'done', nop)
    for n in range(N):
        i = str(n)
        chip.node(flow, 'run', nop, index=i)
        chip.edge(flow, 'import', 'run', head_index=i)
        chip.edge(flow, 'run', 'done', tail_index=i)

    chip.set('option', 'flow', flow)
    chip.set('option', 'mode', 'sim')
    chip.run()


def main():
    parser = argparse.ArgumentParser("scalability")
    parser.add_argument('--type', type=str, choices=('serial', 'parallel'), default='serial')
    parser.add_argument('--num_tasks', type=int, default=2)
    parser.add_argument('--num_steps', type=int, default=2)

    args = parser.parse_args()

    num_tasks = args.num_tasks
    if args.type == 'serial':
        steps_to_run = args.num_steps
        run_long_serial(num_tasks, steps_to_run)
    elif args.type == 'parallel':
        run_wide_parallel(num_tasks)
    return


if __name__ == '__main__':
    main()
