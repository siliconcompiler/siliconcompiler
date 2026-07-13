# Copyright 2026 Silicon Compiler Authors. All Rights Reserved.
import pytest

# These procs are pure Tcl operating on a global ``sc_cfg`` dict, so we
# exercise them through Python's embedded Tcl interpreter (tkinter.Tcl()) with
# a synthetic configuration. Skip when tkinter / Tk is unavailable.
tkinter = pytest.importorskip("tkinter")


@pytest.fixture
def cfg(tcl_interp):
    '''Interpreter with sc_schema_access.tcl sourced and an empty sc_cfg.

    sc_proc_args.tcl is sourced first since sc_get_filesets parses its keyword
    arguments through sc::parse_args.
    '''
    interp = tcl_interp("sc_proc_args.tcl", "sc_schema_access.tcl")
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


def _pairs(cfg, tcl):
    '''Evaluate ``tcl`` and return its {library fileset} pairs as tuples.'''
    return [
        tuple(str(p) for p in cfg.tk.splitlist(pair))
        for pair in cfg.tk.splitlist(cfg.eval(tcl))
    ]


def test_get_filesets_no_dependencies(cfg):
    cfg.eval("dict set sc_cfg library lib_a fileset rtl topmodule top")

    assert _pairs(cfg, "sc_get_filesets -library lib_a -filesets rtl") == [("lib_a", "rtl")]


def test_get_filesets_orders_dependencies_first(cfg):
    # lib_a/rtl depends on lib_b/rtl which depends on lib_c/rtl.
    cfg.eval(
        """
        dict set sc_cfg library lib_a fileset rtl depfileset {{lib_b rtl}}
        dict set sc_cfg library lib_b fileset rtl depfileset {{lib_c rtl}}
        dict set sc_cfg library lib_c fileset rtl topmodule c
        """
    )

    # Post-order: deepest dependency first, requesting fileset last.
    assert _pairs(cfg, "sc_get_filesets -library lib_a -filesets rtl") == [
        ("lib_c", "rtl"),
        ("lib_b", "rtl"),
        ("lib_a", "rtl"),
    ]


def test_get_filesets_dedups_diamond(cfg):
    # lib_a depends on both lib_b and lib_c, which both depend on lib_d.
    cfg.eval(
        """
        dict set sc_cfg library lib_a fileset rtl depfileset {{lib_b rtl} {lib_c rtl}}
        dict set sc_cfg library lib_b fileset rtl depfileset {{lib_d rtl}}
        dict set sc_cfg library lib_c fileset rtl depfileset {{lib_d rtl}}
        dict set sc_cfg library lib_d fileset rtl topmodule d
        """
    )

    pairs = _pairs(cfg, "sc_get_filesets -library lib_a -filesets rtl")
    # lib_d appears exactly once, before both of its dependents.
    assert pairs == [
        ("lib_d", "rtl"),
        ("lib_b", "rtl"),
        ("lib_c", "rtl"),
        ("lib_a", "rtl"),
    ]


def test_get_filesets_crosses_filesets(cfg):
    # A dependency may pull in a differently-named fileset.
    cfg.eval(
        """
        dict set sc_cfg library lib_a fileset rtl depfileset {{lib_b models}}
        dict set sc_cfg library lib_b fileset models topmodule b
        """
    )

    assert _pairs(cfg, "sc_get_filesets -library lib_a -filesets rtl") == [
        ("lib_b", "models"),
        ("lib_a", "rtl"),
    ]


def test_get_filesets_defaults_to_project_selection(cfg):
    # With no arguments the design and selected filesets are pulled from option.
    cfg.eval(
        """
        dict set sc_cfg option design lib_a
        dict set sc_cfg option fileset rtl
        dict set sc_cfg library lib_a fileset rtl depfileset {{lib_b rtl}}
        dict set sc_cfg library lib_b fileset rtl topmodule b
        """
    )

    assert _pairs(cfg, "sc_get_filesets") == [
        ("lib_b", "rtl"),
        ("lib_a", "rtl"),
    ]


def test_get_filesets_multiple_top_filesets(cfg):
    # filesets is a list: each requested fileset is traversed in order and its
    # dependencies pulled in ahead of it.
    cfg.eval(
        """
        dict set sc_cfg library lib_a fileset rtl depfileset {{lib_b rtl}}
        dict set sc_cfg library lib_a fileset sdc topmodule top
        dict set sc_cfg library lib_b fileset rtl topmodule b
        """
    )

    assert _pairs(cfg, "sc_get_filesets -library lib_a -filesets {rtl sdc}") == [
        ("lib_b", "rtl"),
        ("lib_a", "rtl"),
        ("lib_a", "sdc"),
    ]


def test_get_filesets_alias_swaps_library_and_fileset(cfg):
    # option,alias replaces the (lib_b, rtl) dependency edge with (lib_c, alt).
    cfg.eval(
        """
        dict set sc_cfg option alias {{lib_b rtl lib_c alt}}
        dict set sc_cfg library lib_a fileset rtl depfileset {{lib_b rtl}}
        dict set sc_cfg library lib_b fileset rtl topmodule b
        dict set sc_cfg library lib_c fileset alt topmodule c
        """
    )

    assert _pairs(cfg, "sc_get_filesets -library lib_a -filesets rtl") == [
        ("lib_c", "alt"),
        ("lib_a", "rtl"),
    ]


def test_get_filesets_alias_empty_library_drops_dependency(cfg):
    # An empty destination library removes the dependency entirely.
    cfg.eval(
        """
        dict set sc_cfg option alias {{lib_b rtl {} {}}}
        dict set sc_cfg library lib_a fileset rtl depfileset {{lib_b rtl}}
        dict set sc_cfg library lib_b fileset rtl topmodule b
        """
    )

    assert _pairs(cfg, "sc_get_filesets -library lib_a -filesets rtl") == [("lib_a", "rtl")]


def test_get_filesets_alias_empty_fileset_preserves_original(cfg):
    # An empty destination fileset keeps the original fileset name, swapping
    # only the library.
    cfg.eval(
        """
        dict set sc_cfg option alias {{lib_b rtl lib_c {}}}
        dict set sc_cfg library lib_a fileset rtl depfileset {{lib_b rtl}}
        dict set sc_cfg library lib_b fileset rtl topmodule b
        dict set sc_cfg library lib_c fileset rtl topmodule c
        """
    )

    assert _pairs(cfg, "sc_get_filesets -library lib_a -filesets rtl") == [
        ("lib_c", "rtl"),
        ("lib_a", "rtl"),
    ]


def test_get_filesets_alias_noop_when_source_equals_destination(cfg):
    # A self-referential alias is ignored.
    cfg.eval(
        """
        dict set sc_cfg option alias {{lib_b rtl lib_b rtl}}
        dict set sc_cfg library lib_a fileset rtl depfileset {{lib_b rtl}}
        dict set sc_cfg library lib_b fileset rtl topmodule b
        """
    )

    assert _pairs(cfg, "sc_get_filesets -library lib_a -filesets rtl") == [
        ("lib_b", "rtl"),
        ("lib_a", "rtl"),
    ]
