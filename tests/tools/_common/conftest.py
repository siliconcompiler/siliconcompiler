# Copyright 2026 Silicon Compiler Authors. All Rights Reserved.
import gc
import os.path

import pytest


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
