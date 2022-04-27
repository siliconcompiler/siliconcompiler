'''Benchmark to measure time taken per simple task with large flowgraphs.

$ ./examples/benchmark/scalability.py serial <N> <S>
Runs a serial flowgraph with N tasks and output "done" after S steps.

$ ./examples/benchmark/scalability.py parallel <N>
Runs a parallel flowgraph with N parallel tasks.
'''

import siliconcompiler

import sys

def run_long_serial(N, steps_to_run):
    chip = siliconcompiler.Chip()
    flow = 'test_long_serial'
    pipe = [{'import': 'echo'}]
    pipe += [{f'measured{i}': 'echo'} for i in range(steps_to_run - 1)]
    pipe += [{'done': 'echo'}]
    pipe += [{f'extra{i}': 'echo'} for i in range(N - (steps_to_run + 1))]

    chip.set('design', 'test_long_serial')
    chip.set('flow', flow)
    chip.set('mode', 'sim')
    chip.pipe(flow, pipe)
    chip.run()

def run_wide_parallel(N):
    chip = siliconcompiler.Chip()
    flow = 'test_long_parallel'

    chip.node(flow, 'import', 'echo')
    chip.node(flow, 'done', 'echo')
    for n in range(N):
        i = str(n)
        chip.node(flow, 'run', 'echo', index=i)
        chip.edge(flow, 'import', 'run', head_index=i)
        chip.edge(flow, 'run', 'done', tail_index=i)

    chip.set('design', 'test_long_serial')
    chip.set('flow', flow)
    chip.set('mode', 'sim')
    chip.run()

def main():
    num_tasks = int(sys.argv[2])
    if sys.argv[1] == 'serial':
        steps_to_run = int(sys.argv[3])
        run_long_serial(num_tasks, steps_to_run)
    elif sys.argv[1] == 'parallel':
        run_wide_parallel(num_tasks)
    return

if __name__ == '__main__':
    main()
