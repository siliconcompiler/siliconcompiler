# Copyright 2026 Silicon Compiler Authors. All Rights Reserved.
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

    def _make(*files):
        interp = tkinter.Tcl()
        for name in files:
            path = os.path.join(
                scroot, "siliconcompiler", "tools", "_common", "tcl", name)
            # Tcl accepts forward slashes on every platform; backslashes in a
            # Windows path would be read as escapes.
            interp.eval("source {%s}" % path.replace(os.sep, "/"))
        return interp

    return _make
