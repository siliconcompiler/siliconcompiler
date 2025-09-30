#!/usr/bin/env python3

import cProfile
import pstats
from pstats import SortKey
import graphviz
import argparse
import tempfile
import os
import gprof2dot

from siliconcompiler import ASIC, Project, Flowgraph, Design
from siliconcompiler.demos import asic_demo


def print_stats(pr):
    ps = pstats.Stats(pr).sort_stats(SortKey.CUMULATIVE)
    ps.print_stats(20)


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


def run_read_manifest(pr, extra):
    remove_path = False
    if not extra:
        demo = asic_demo.ASICDemo()

        fd, path = tempfile.mkstemp(prefix='read_manifest', suffix='.json')
        os.close(fd)

        demo.write_manifest(path)
        remove_path = True
    else:
        path = extra

    proj = ASIC()

    pr.enable()
    proj.read_manifest(path)
    pr.disable()

    if remove_path:
        os.remove(path)


def run_write_manifest(pr, extra):
    proj = asic_demo.ASICDemo()

    fd, path = tempfile.mkstemp(prefix='write_manifest', suffix='.json')
    os.close(fd)

    pr.enable()
    proj.write_manifest(path)
    pr.disable()

    os.remove(path)


def run_check_filepaths(pr, extra):
    proj = asic_demo.ASICDemo()

    proj.check_filepaths()
    pr.enable()
    for _ in range(10):
        proj.check_filepaths()
    pr.disable()


def run_asic_demo(pr, extra):

    pr.enable()
    proj = asic_demo.ASICDemo()
    proj.run()
    proj.summary()
    pr.disable()


def run_large_flowgraph(pr, extra):
    from siliconcompiler.tools.builtin import nop

    try:
        simulations = int(extra)
    except (ValueError, TypeError):
        simulations = 50

    print(f'Setting up {2 + 2 * simulations} nodes')

    pr.enable()
    design = Design("dummy")
    design.set_topmodule("top", "rtl")
    proj = Project(design)
    proj.add_fileset("rtl")

    flow = Flowgraph("large_flowgraph")

    flow.node('comp', nop.NOPTask())
    flow.node('elab', nop.NOPTask())
    flow.edge(tail='comp', head='elab')

    for i in range(simulations):
        flow.node(step='pre_sim', task=nop.NOPTask(), index=i)

    for i in range(simulations):
        flow.node(step='sim', task=nop.NOPTask(), index=i)
        flow.edge(tail='pre_sim', head='sim', tail_index=i, head_index=i)
        flow.edge(tail='elab', head='sim', tail_index=0, head_index=i)

    proj.set_flow(flow)

    proj.run()
    pr.disable()


if __name__ == "__main__":
    tests = {
        'read_manifest': run_read_manifest,
        'write_manifest': run_write_manifest,
        'asic_demo': run_asic_demo,
        'check_filepaths': run_check_filepaths,
        'large_flowgraph': run_large_flowgraph,
        'all': None
    }

    parser = argparse.ArgumentParser(
        description='Utility tool to aide in profiling SiliconCompiler')
    parser.add_argument(
        '--print',
        action='store_true',
        help='Print the time stats from the profile')
    parser.add_argument(
        '--profile',
        choices=tests.keys(),
        default='all',
        help='Profile test to run')
    parser.add_argument(
        '--extra',
        metavar='<payload>',
        help='extra payload information for test')

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
        func(pr, args.extra)
        generate_graph(pr, test)
        if args.print:
            print_stats(pr)
