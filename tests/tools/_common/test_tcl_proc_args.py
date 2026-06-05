# Copyright 2026 Silicon Compiler Authors. All Rights Reserved.
import pytest

# The parser is pure Tcl, so we exercise it through Python's embedded Tcl
# interpreter (tkinter.Tcl()). Skip the whole module when tkinter / the Tk
# libraries are unavailable rather than failing the suite.
tkinter = pytest.importorskip("tkinter")


@pytest.fixture
def parse(tcl_interp):
    '''Returns a helper that parses argv against a spec via the Tcl parser.

    The helper returns the result as a Python dict (all values are strings;
    list-valued entries can be split further with ``split_list``).
    '''
    interp = tcl_interp("sc_proc_args.tcl")
    interp.eval(
        """
        proc _sc_parse_test { spec args } {
            global _opts
            sc::parse_args _opts $spec $args
        }
        """
    )

    def _parse(spec, *argv):
        # interp.call handles quoting of each argv token. Values are read back
        # one key at a time via "dict get" so nested list values come through
        # as clean scalar strings (splitting the whole dict at once mangles
        # single-element sublists into Python tuples).
        interp.call("_sc_parse_test", spec, *argv)
        keys = interp.tk.splitlist(interp.eval("dict keys $::_opts"))
        return {str(k): str(interp.eval(f"dict get $::_opts {k}")) for k in keys}

    _parse.split_list = lambda value: [str(v) for v in interp.tk.splitlist(value)]
    return _parse


SPEC = """
    -name      {default top}
    -threads   {default 1}
    -mode      {default fast choices {fast slow}}
    -outdir    {required}
    -verbose   {flag}
    positional {min 1 max 3 name files}
"""


def test_loads(parse):
    # Sourcing the file and a minimal parse succeeds.
    opts = parse("-x {default 1}", "-x", "5")
    assert opts["x"] == "5"


def test_defaults_applied(parse):
    opts = parse(SPEC, "-outdir", "/out", "only.v")
    assert opts["name"] == "top"
    assert opts["threads"] == "1"
    assert opts["mode"] == "fast"
    assert opts["outdir"] == "/out"
    assert opts["verbose"] == "0"
    assert parse.split_list(opts["files"]) == ["only.v"]


def test_keyword_and_flag(parse):
    opts = parse(SPEC, "-outdir", "/tmp", "-verbose", "-mode", "slow", "a.v", "b.v")
    assert opts["mode"] == "slow"
    assert opts["verbose"] == "1"
    assert parse.split_list(opts["files"]) == ["a.v", "b.v"]


def test_flag_is_zero_when_absent(parse):
    opts = parse(SPEC, "-outdir", "/tmp", "a.v")
    assert opts["verbose"] == "0"


def test_double_dash_terminates_options(parse):
    # -name consumes "-weird"; everything after -- is positional.
    opts = parse(SPEC, "-outdir", "/out", "-name", "-weird", "--", "-looks-positional")
    assert opts["name"] == "-weird"
    assert parse.split_list(opts["files"]) == ["-looks-positional"]


def test_value_option_consumes_dash_value(parse):
    # A value option grabs the next token even if it starts with "-".
    opts = parse("-n {default 0}", "-n", "-5")
    assert opts["n"] == "-5"


def test_missing_required_raises(parse):
    with pytest.raises(tkinter.TclError, match='missing required option "-outdir"'):
        parse(SPEC, "a.v")


def test_too_few_positionals_raises(parse):
    with pytest.raises(tkinter.TclError, match="at least 1 positional"):
        parse(SPEC, "-outdir", "/out")


def test_too_many_positionals_raises(parse):
    with pytest.raises(tkinter.TclError, match="at most 3 positional"):
        parse(SPEC, "-outdir", "/out", "a", "b", "c", "d")


def test_invalid_choice_raises(parse):
    with pytest.raises(tkinter.TclError, match='invalid value "turbo" for "-mode"'):
        parse(SPEC, "-outdir", "/out", "-mode", "turbo", "a")


def test_unknown_option_raises(parse):
    with pytest.raises(tkinter.TclError, match='unknown option "-bogus"'):
        parse(SPEC, "-outdir", "/out", "-bogus", "a")


def test_value_option_without_value_raises(parse):
    with pytest.raises(tkinter.TclError, match='option "-outdir" requires a value'):
        parse(SPEC, "a.v", "-outdir")


def test_invalid_spec_key_raises(parse):
    with pytest.raises(tkinter.TclError, match='invalid spec key "bogus"'):
        parse("bogus {default 1}", "a")


def test_caller_name_in_error(parse):
    # The error is prefixed with the calling proc's name.
    with pytest.raises(tkinter.TclError, match="_sc_parse_test:"):
        parse(SPEC, "a.v")
