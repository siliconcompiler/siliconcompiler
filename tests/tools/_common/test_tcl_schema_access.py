# Copyright 2026 Silicon Compiler Authors. All Rights Reserved.
import pytest

# These procs are pure Tcl operating on a global ``sc_cfg`` dict, so we
# exercise them through Python's embedded Tcl interpreter (tkinter.Tcl()) with
# a synthetic configuration. Skip when tkinter / Tk is unavailable.
tkinter = pytest.importorskip("tkinter")


@pytest.fixture
def cfg(tcl_interp):
    '''Interpreter with sc_schema_access.tcl sourced and an empty sc_cfg.'''
    interp = tcl_interp("sc_schema_access.tcl")
    interp.eval("set sc_cfg [dict create]")
    return interp


def test_cfg_get_and_exists(cfg):
    cfg.eval("dict set sc_cfg foo bar baz hello")

    assert cfg.eval("sc_cfg_get foo bar baz") == "hello"
    assert cfg.eval("sc_cfg_exists foo bar baz") == "1"
    assert cfg.eval("sc_cfg_exists foo bar missing") == "0"


def test_cfg_get_missing_raises(cfg):
    with pytest.raises(tkinter.TclError, match="is not in the siliconcompiler configuration"):
        cfg.eval("sc_cfg_get foo bar missing")


@pytest.fixture
def tool_task_cfg(cfg):
    '''sc_cfg wired up so the tool/task shortcut resolves to a known leaf.'''
    cfg.eval(
        """
        dict set sc_cfg arg step place
        dict set sc_cfg arg index 0
        dict set sc_cfg option flow asicflow
        dict set sc_cfg flowgraph asicflow place 0 task placetask
        dict set sc_cfg flowgraph asicflow place 0 tool placetool
        """
    )
    return cfg


def test_cfg_tool_task_get(tool_task_cfg):
    tool_task_cfg.eval("dict set sc_cfg tool placetool task placetask var foo myval")

    assert tool_task_cfg.eval("sc_cfg_tool_task_get var foo") == "myval"
    assert tool_task_cfg.eval("sc_cfg_tool_task_exists var foo") == "1"
    assert tool_task_cfg.eval("sc_cfg_tool_task_exists var bar") == "0"


def test_cfg_tool_task_check_in_list(tool_task_cfg):
    tool_task_cfg.eval("dict set sc_cfg tool placetool task placetask var things {a b c}")

    assert tool_task_cfg.eval("sc_cfg_tool_task_check_in_list b var things") == "1"
    assert tool_task_cfg.eval("sc_cfg_tool_task_check_in_list z var things") == "0"


def test_section_banner(cfg):
    cfg.eval("set ::lines {}")
    cfg.eval("proc capture { line } { lappend ::lines $line }")
    cfg.eval("sc_section_banner {Hello World} capture")

    lines = [str(line) for line in cfg.tk.splitlist(cfg.eval("set ::lines"))]
    assert len(lines) == 3
    assert lines[1] == "| Hello World"
    assert set(lines[0]) == {"="}
    assert lines[0] == lines[2]


def test_get_libraries_resolves_and_dedups(cfg):
    # lib_a depends on lib_c; every library needs an (possibly empty) entry.
    cfg.eval(
        """
        dict set sc_cfg option library {lib_a lib_b}
        dict set sc_cfg library lib_a option library {lib_c}
        dict set sc_cfg library lib_b option library {}
        dict set sc_cfg library lib_c option library {}
        """
    )

    libs = [str(lib) for lib in cfg.tk.splitlist(cfg.eval("sc_get_libraries"))]
    assert libs == ["lib_a", "lib_b", "lib_c"]


def test_get_libraries_empty(cfg):
    cfg.eval("dict set sc_cfg option library {}")
    assert cfg.eval("sc_get_libraries") == ""


def test_get_asic_libraries(cfg):
    cfg.eval(
        """
        dict set sc_cfg option library {}
        dict set sc_cfg asic logiclib {std_a std_b}
        """
    )

    libs = [str(lib) for lib in cfg.tk.splitlist(cfg.eval("sc_get_asic_libraries logic"))]
    assert libs == ["std_a", "std_b"]


def test_cfg_get_fileset(cfg):
    cfg.eval(
        """
        dict set sc_cfg library lib_a fileset rtl file verilog {a.v b.v}
        dict set sc_cfg library lib_b fileset rtl file verilog {c.v}
        """
    )

    files = [
        str(f)
        for f in cfg.tk.splitlist(cfg.eval("sc_cfg_get_fileset {lib_a lib_b} rtl verilog"))
    ]
    assert files == ["a.v", "b.v", "c.v"]


def test_cfg_get_fileset_missing_is_skipped(cfg):
    # Libraries/filesets without the requested filetype contribute nothing.
    cfg.eval("dict set sc_cfg library lib_a fileset rtl file verilog {only.v}")

    files = [
        str(f)
        for f in cfg.tk.splitlist(
            cfg.eval("sc_cfg_get_fileset {lib_a lib_missing} rtl verilog"))
    ]
    assert files == ["only.v"]
