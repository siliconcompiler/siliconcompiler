'''Benchmark to measure time taken per simple task with large flowgraphs.

Running this file determines the average time taken per task on long serial
flowgraphs of 10, 100, 250, and 500 simple "echo" tasks.

Since it would take too long to measure the entire run with a flowgraph of such
a length, we perform a weird trick to measure just the first "STEPS_TO_RUN"
tasks. Instead of calling "run_long_serial()" directly, this file calls back into
itself using "subprocess", using a CLI argument to change the codepath. That way,
it can monitor stdout to start timing when it sees the initial "import" echo (so
that it doesn't measure start-up time), and finish timing and end the process
when it sees the "done" echo.

While it would be more straightforward to do this with a steplist, using a
steplist removes some of the overhead we're trying to measure (e.g. the flooding
scheduler only launches processes based on what's in the steplist).
'''
import siliconcompiler

import os
import signal
import subprocess
import sys
import time

STEPS_TO_RUN = 10

def run_long_serial(N):
    chip = siliconcompiler.Chip()
    flow = 'test_long_serial'
    pipe = [{'import': 'echo'}]
    pipe += [{f'measured{i}': 'echo'} for i in range(STEPS_TO_RUN - 1)]
    pipe += [{'done': 'echo'}]
    pipe += [{f'extra{i}': 'echo'} for i in range(N - (STEPS_TO_RUN + 1))]

    chip.set('design', 'test_long_serial')
    chip.set('flow', flow)
    chip.set('mode', 'sim')
    chip.set('skipcheck', True)
    chip.pipe(flow, pipe)
    chip.run()

def main():
    if len(sys.argv) > 1:
        # Running this file with an argument executes the "run_long_serial"
        # benchmark.
        N = int(sys.argv[1])
        run_long_serial(N)
        return

    # Without an argument, we loop over a set of values to try, and re-run this
    # script with those values provided as arguments.
    results = {}
    for N in (10, 100, 250, 500):
        proc = subprocess.Popen(['python', sys.argv[0], str(N)],
                                 stdout=subprocess.PIPE)
        for line in proc.stdout:
            line = line.decode('ascii')
            if line.startswith('import0'):
                start = time.time()
            if line.startswith('done'):
                end = time.time()
                proc.send_signal(signal.SIGINT)
                proc.wait()
                break

        time_per_task = (end - start) / STEPS_TO_RUN
        results[N] = time_per_task

    for N, time_per_task in results.items():
        print(f'{N}, {time_per_task}')

if __name__ == '__main__':
    main()
