# Copyright 2026 Silicon Compiler Authors. All Rights Reserved.
import gc
import os.path

import pytest

from siliconcompiler import Design, Flowgraph, Sim
from siliconcompiler.tools._common.cocotb import cocotb_task
from siliconcompiler.utils.curation import collect


@pytest.fixture
def tcl_interp(scroot):
    '''Factory returning a fresh embedded Tcl interpreter (tkinter.Tcl()) with
    the named siliconcompiler ``tools/_common/tcl`` file(s) sourced.

    Skips the test when tkinter / the Tk libraries are unavailable.

        interp = tcl_interp("sc_schema_access.tcl")
    '''
    tkinter = pytest.importorskip("tkinter")

    created = []

    def _make(*files):
        interp = tkinter.Tcl()
        created.append(interp)
        for name in files:
            path = os.path.join(
                scroot, "siliconcompiler", "tools", "_common", "tcl", name)
            # Tcl accepts forward slashes on every platform; backslashes in a
            # Windows path would be read as escapes.
            interp.eval("source {%s}" % path.replace(os.sep, "/"))
        return interp

    try:
        yield _make
    finally:
        # A Tcl interpreter is bound to the thread that created it: delete it
        # from another thread and Tcl does not raise, it calls abort() and takes
        # the process with it. Dropping the references here finalizes them on
        # the test thread rather than leaving the timing to whichever thread
        # next triggers a collection. Fixtures depending on this one tear down
        # first, so these are the last references by the time this runs.
        created.clear()
        gc.collect()


@pytest.fixture
def cocotb_project():
    '''Sim project running one cocotb exec task on a single test module.'''
    def _make(task, copy=False, compile_task=None, source="# cocotb test module\n"):
        with open("test_mod.py", "w") as f:
            f.write(source)
        with open("top.v", "w") as f:
            f.write("module top();\nendmodule\n")

        design = Design("tb")
        design.set_dataroot("root", os.getcwd())
        with design.active_dataroot("root"), design.active_fileset("tb"):
            design.set_topmodule("top")
            design.add_file("test_mod.py", filetype="python")
            design.add_file("top.v")

        proj = Sim(design)
        proj.add_fileset("tb")

        flow = Flowgraph("testflow")
        flow.node("simulate", task)
        if compile_task:
            flow.node("compile", compile_task)
            flow.edge("compile", "simulate")
        proj.set_flow(flow)

        if copy:
            # Only the test module, as a cluster collects a file it cannot share
            collect(proj, keys=[(key, None, None) for key in proj.allkeys()
                                if key[-2:] == ("file", "python")])

        return proj
    return _make


@pytest.fixture
def cocotb_installed(monkeypatch):
    '''Lets setup() run where the cocotb extra is not installed.'''
    monkeypatch.setattr(cocotb_task, "_has_cocotb", True)
