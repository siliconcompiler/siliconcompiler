#!/usr/bin/env python3
"""
Manual scenario-validation tool for the CLI dashboard logging behavior.

A persistent developer utility: run it by hand in a REAL terminal (a TTY) to
eyeball the dashboard scenarios that automated tests can only assert on
indirectly (they run headless, with no live screen). Keep it around for
verifying dashboard/logging changes.

    python scripts/check_dashboard.py            # dashboard on (the interesting case)
    python scripts/check_dashboard.py --lines 60 # more log lines to overflow the pane
    python scripts/check_dashboard.py --nodashboard   # baseline: plain terminal logging
    python scripts/check_dashboard.py --hang     # then hit Ctrl+C — see below
    python scripts/check_dashboard.py --multi    # several runs sharing ONE dashboard
    python scripts/check_dashboard.py --multi --jobs 4 --nodes 6  # bigger multi run

What it does
------------
Builds a one-node flow whose task logs many lines and then FAILS during setup(),
i.e. "a run that fails immediately after the dashboard opens". A few lines are
also logged BEFORE run() to exercise history-seeding of the dashboard log pane.

What to look for (Issue #2 — "log truncated when the dashboard is open")
------------------------------------------------------------------------
* While running, the live pane shows only the last handful of "noisy line N".
* When it fails, the dashboard tears down and — under a "Full log" rule — the
  ENTIRE tail (all noisy lines + the failure messages) is reprinted to normal
  scrollback, followed by the "Run failed" error and the RuntimeError.
* The "pre-run banner" lines logged before run() should appear in the dashboard
  log pane from the very start (history seeding), not just after run() begins.

Before the fix the dashboard only reprinted the ~dozen visible lines, so the
tail that explains the failure was lost.

What to look for (Ctrl+C — "an interrupt is not a failure")
-----------------------------------------------------------
Run with --hang; the task logs the noisy lines and then sleeps. Press Ctrl+C.
The dashboard should tear down WITHOUT printing a "Full log" dump — an
interrupt is a clean exit, not a failure, so the tail is not reprinted.

What to look for (--multi — several SC runs in ONE dashboard)
-------------------------------------------------------------
The CLI dashboard Board is a process-wide singleton (MPManager.get_dashboard())
keyed by design/jobname, so several Project.run() calls in the SAME process
render as separate rows/progress bars in ONE live view. Because the Board and
its render thread live entirely in the main process, the concurrency here is
threads — each run still forks its own node workers internally, but they all
feed the one main-process dashboard. Expect --jobs progress bars advancing
together, each labelled design_k/job0, then all completing.
"""

import argparse
import logging
import threading
import time

from siliconcompiler import Project, Design, Flowgraph, Task


class WorkTask(Task):
    """A no-exe Python task that logs a little and sleeps, to simulate work
    so the dashboard shows progress advancing over time."""

    _work = 0.4

    def tool(self):
        return "demo_tool"

    def task(self):
        return "work"

    def run(self):
        design = self.project.option.get_design()
        for i in range(3):
            self.logger.info(f"[{design}] working ({i + 1}/3) on {self.step}/{self.index}")
            time.sleep(WorkTask._work / 3)
        return 0


class NoisyFailTask(Task):
    """A task that floods the log, then either fails or hangs during setup()."""

    _lines = 40
    _hang = False

    def tool(self):
        return "demo_tool"

    def task(self):
        return "noisy_fail"

    def setup(self):
        super().setup()
        for i in range(NoisyFailTask._lines):
            self.logger.info(f"noisy line {i:02d} — this is tool output that scrolls by")
        if NoisyFailTask._hang:
            self.logger.info("sleeping — press Ctrl+C now (should NOT dump the full log)")
            while True:
                time.sleep(0.5)
        self.logger.warning("something looks wrong...")
        self.logger.error("fatal: the widget frobnicator exploded")
        # Fail right here, while the dashboard owns the screen.
        raise RuntimeError("NoisyFailTask blew up during setup")


def _build_work_project(name, nodes):
    """A project with an `nodes`-long chained flow of WorkTasks."""
    design = Design(name)
    design.set_topmodule("top", fileset="rtl")
    proj = Project(design)
    proj.add_fileset("rtl")

    flow = Flowgraph("workflow")
    prev = None
    for i in range(nodes):
        step = f"step{i}"
        flow.node(step, WorkTask())
        if prev is not None:
            flow.edge(prev, step)
        prev = step
    proj.set_flow(flow)
    proj.logger.setLevel(logging.INFO)
    return proj


def run_multi(jobs, nodes):
    """Launch `jobs` concurrent runs that share the one singleton dashboard.

    Threads (not processes) so every run feeds the same main-process Board;
    each run still forks its own node workers internally.
    """
    projects = [_build_work_project(f"design_{k}", nodes) for k in range(jobs)]

    errors = {}

    def _run(idx, proj):
        try:
            proj.run()
        except Exception as e:  # noqa BLE001 - demo: report, don't crash the thread
            errors[idx] = e

    threads = [threading.Thread(target=_run, args=(k, p), name=f"run-{k}")
               for k, p in enumerate(projects)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    if errors:
        print(f"\n>>> {len(errors)} run(s) errored: {errors}")
        return 1
    print(f"\n>>> all {jobs} runs completed in one shared dashboard view")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lines", type=int, default=40,
                        help="number of noisy log lines to emit before failing")
    parser.add_argument("--nodashboard", action="store_true",
                        help="disable the dashboard (baseline plain-terminal behavior)")
    parser.add_argument("--hang", action="store_true",
                        help="sleep after logging so you can test Ctrl+C (no dump expected)")
    parser.add_argument("--multi", action="store_true",
                        help="run several SCs concurrently in ONE shared dashboard")
    parser.add_argument("--jobs", type=int, default=3,
                        help="--multi: number of concurrent runs (default 3)")
    parser.add_argument("--nodes", type=int, default=4,
                        help="--multi: chained nodes per run (default 4)")
    args = parser.parse_args()

    if args.multi:
        return run_multi(args.jobs, args.nodes)

    NoisyFailTask._lines = args.lines
    NoisyFailTask._hang = args.hang

    design = Design("demodesign")
    design.set_topmodule("top", fileset="rtl")
    proj = Project(design)
    proj.add_fileset("rtl")

    if args.nodashboard:
        proj.set("option", "nodashboard", True)

    flow = Flowgraph("demoflow")
    flow.node("build", NoisyFailTask())
    proj.set_flow(flow)

    proj.logger.setLevel(logging.INFO)

    # Logged BEFORE run(): should be seeded into the dashboard log pane so it
    # shows continuity from the start rather than a blank pane.
    for i in range(5):
        proj.logger.info(f"pre-run banner line {i} (should be seeded into the pane)")

    try:
        proj.run()
    except RuntimeError as e:
        print("\n>>> demo caught the expected failure:", e)
        return 0
    except KeyboardInterrupt:
        print("\n>>> interrupted (no full-log dump should have printed)")
        return 0
    if args.hang:
        print("\n>>> run returned after interrupt (no full-log dump should have printed)")
        return 0
    print("\n>>> demo did NOT fail as expected (unexpected)")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
