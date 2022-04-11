import os
import signal
import subprocess
import time

import pytest

@pytest.fixture
def run_scalability_test(scroot):
    # TODO: I think we're just about at a point where we can pull in code from
    # scalability.py and call it directly, instead of using this weird
    # subprocess hack. This was originally done b/c running an entire big
    # flowgraph was too slow, but with the optimizations we've applied that
    # shouldn't be the case anymore.
    test_path = os.path.join(scroot, 'examples', 'benchmark', 'scalability.py')

    def _run(task, trials, steps_to_run=None):
        results = {}
        for num_tasks in trials:
            cmd = ['python', test_path, task, str(num_tasks)]
            if steps_to_run:
                cmd.append(str(steps_to_run))
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
            for line in proc.stdout:
                line = line.decode('ascii')
                if line.startswith('import0'):
                    start = time.time()
                if line.startswith('done'):
                    end = time.time()
                    proc.send_signal(signal.SIGINT)
                    proc.wait()
                    break

            results[num_tasks] = end - start

        return results

    return _run

# Note: the thresholds here are meant to flag major performance regressions. I
# gave a bit of overhead to account for normal variation run-to-run, but we
# might need to tune these more to not get false positives.

# These tests don't require EDA tools installed, but marking them as EDA so they
# only run daily on our runner (which is also faster than GH machines).

@pytest.mark.eda
def test_long_serial(run_scalability_test):
    steps_to_run = 10
    results = run_scalability_test('serial', (10, 100, 250), steps_to_run)

    for n, total_time in results.items():
        time_per_task = total_time / steps_to_run
        print(f'{n}, {time_per_task}')

        # Should take <1 sec per task for each trial
        assert time_per_task < 1

@pytest.mark.eda
def test_wide_parallel(run_scalability_test):
    results = run_scalability_test('parallel', (10, 100, 250))
    for n, total_time in results.items():
        print(f'{n}, {total_time}')
        if n <= 10:
            assert total_time < 1
        elif n <= 100:
            assert total_time < 10
        else:
            assert total_time < 60
