#!/usr/bin/env python3

from siliconcompiler import Chip
import cProfile
import pstats
from pstats import SortKey
import graphviz
import argparse
import tempfile
import os
import gprof2dot


def print_stats(pr):
    ps = pstats.Stats(pr).sort_stats(SortKey.CUMULATIVE)
    ps.print_stats()


def generate_graph(pr, name):
    with tempfile.TemporaryDirectory() as d:
        stats = os.path.join(d, 'profile.pstats')
        dot_file = os.path.join(d, 'profile.dot')

        pr.dump_stats(stats)

        gprof2dot.main(argv=['-f', 'pstats', stats, '-o', dot_file])

        with open(dot_file) as f:
            dot = graphviz.Source(f.read())

    try:
        dot.render(filename=name, format='png', cleanup=True)
    except graphviz.ExecutableNotFound:
        pass


def run_read_manifest(pr):
    chip = Chip('')

    pr.enable()
    chip.read_manifest('manifest.pkg.json')
    pr.disable()


def run_asic_demo(pr):
    chip = Chip('')

    pr.enable()
    chip.load_target('asic_demo')
    chip.run()
    chip.summary()
    pr.disable()


if __name__ == "__main__":
    tests = {
        'read_manifest': run_read_manifest,
        'run_asic_demo': run_asic_demo,
        'all': None
    }

    parser = argparse.ArgumentParser()
    parser.add_argument('--print', action='store_true')
    parser.add_argument('--profile', choices=tests.keys(), default='all')

    args = parser.parse_args()

    test_set = args.profile
    if test_set == 'all':
        test_set = [t for t in tests.keys() if t != 'all']
    else:
        test_set = [test_set]

    for test in test_set:
        print(f'Running {test}')
        func = tests[test]
        pr = cProfile.Profile()
        func(pr)
        generate_graph(pr, test)
        if args.print:
            print_stats(pr)
