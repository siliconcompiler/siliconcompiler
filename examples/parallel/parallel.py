#!/usr/bin/env python3
"""Three ways to get parallelism out of the same sweep: synthesizing ``adder.v``
at several datawidths.

``serial`` and ``processes`` do identical work and differ only in scheduling, so
their times compare directly. ``indexed`` deliberately does *more* -- four
synthesis variants per datawidth instead of one -- because that is what index
parallelism is for: exploring alternatives inside a job, not splitting fixed
work. Compare it on time-per-variant, not on total time.

Run one approach at a time::

    ./parallel.py serial
    ./parallel.py indexed
    ./parallel.py processes

See the "Parallel Job Execution" tutorial for the accompanying discussion.

Requires: yosys; freepdk45 (via lambdapdk)
"""

import sys
import time

from concurrent.futures import ProcessPoolExecutor

from siliconcompiler import ASIC, Design
from siliconcompiler.flows.synflow import SynthesisFlow
from siliconcompiler.targets import freepdk45_demo
from siliconcompiler.utils.multiprocessing import get_process_context

DATAWIDTHS = (8, 16, 32, 64)


def make_design():
    """Build one design carrying an "rtl.<n>" fileset per datawidth."""
    design = Design("adder")
    design.set_dataroot("parallel", __file__)

    for n in DATAWIDTHS:
        with design.active_dataroot("parallel"), design.active_fileset(f"rtl.{n}"):
            design.set_topmodule("adder")
            design.add_file("adder.v")
            design.set_param("N", str(n))

    return design


def make_project(design, n, syn_np=1):
    """Configure a project to synthesize one datawidth."""
    project = ASIC(design)
    project.add_fileset(f"rtl.{n}")
    freepdk45_demo(project)

    # syn_np controls how many synthesis variants the flow creates. Each one is
    # a separate index of the same step, and indices have no edges between them,
    # so the scheduler is free to run them at the same time.
    #
    # Give the flow its own name. The target has already registered a flow
    # called "synflow-verilog"; constructing another with the default name
    # resolves back to the target's copy, which has syn_np=1, and the extra
    # indices silently never appear.
    project.set_flow(SynthesisFlow(name="sweep", syn_np=syn_np))
    project.option.set_jobname(f"N{n}")
    return project


# ---------------------------------------------------------------------------
# 1. Serial: one node at a time.
# ---------------------------------------------------------------------------
def run_serial():
    design = make_design()

    for n in DATAWIDTHS:
        project = make_project(design, n)
        # Pin the scheduler to a single node so nothing overlaps. This is the
        # baseline, not a recommendation.
        project.option.scheduler.set_maxnodes(1)
        project.run()


# ---------------------------------------------------------------------------
# 2. Indexed: parallel *within* a job.
# ---------------------------------------------------------------------------
def run_indexed():
    design = make_design()

    for n in DATAWIDTHS:
        # Four synthesis indices per job. The jobs still run one after another,
        # but each one now uses several cores instead of one -- and produces four
        # variants rather than one, which is why this run is not a like-for-like
        # timing comparison against the other two.
        project = make_project(design, n, syn_np=4)
        project.run()


# ---------------------------------------------------------------------------
# 3. Processes: parallel *across* jobs.
# ---------------------------------------------------------------------------
def _run_one(n):
    """Worker body: a complete, independent run in its own process."""
    project = make_project(make_design(), n)
    project.run()
    return n, project.history(f"N{n}").get(
        "metric", "cellarea", step="synthesis", index="0")


def run_processes():
    # Each datawidth is an independent flow with no data shared between them,
    # so they can run as separate processes.
    #
    # Two constraints shape this, and both come from run() starting processes of
    # its own inside each worker:
    #
    # ProcessPoolExecutor, not multiprocessing.Pool -- Pool's workers are
    # daemonic, and a daemonic process may not have children, so run() dies with
    # "daemonic processes are not allowed to have children".
    #
    # get_process_context(), not the interpreter default -- SiliconCompiler pins
    # the same context for its own workers, and the default changed to forkserver
    # on Linux in Python 3.14.
    with ProcessPoolExecutor(len(DATAWIDTHS), mp_context=get_process_context()) as pool:
        for n, area in pool.map(_run_one, DATAWIDTHS):
            print(f"N={n:<3} cellarea={area}")


APPROACHES = {
    "serial": run_serial,
    "indexed": run_indexed,
    "processes": run_processes,
}


# The guard is required. SiliconCompiler forks its own node workers on Linux, but a
# script that itself starts processes must still be import-safe: on macOS
# and Windows the child re-imports this file, and without the guard it would
# recurse instead of running.
if __name__ == "__main__":
    choice = sys.argv[1] if len(sys.argv) > 1 else "serial"
    if choice not in APPROACHES:
        sys.exit(f"usage: {sys.argv[0]} [{'|'.join(APPROACHES)}]")

    start = time.monotonic()
    APPROACHES[choice]()
    print(f"{choice}: {time.monotonic() - start:.1f}s")
