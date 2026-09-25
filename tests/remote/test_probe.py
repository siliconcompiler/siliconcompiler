import json
import logging
import shutil

import pytest

from siliconcompiler.remote.server import probe


# What is actually inside an image, asked rather than declared.
#
# 🔴 The command runs in the image and the PARSING happens here. An earlier
# version ran this module inside the image, which works only where
# SiliconCompiler is installed -- and most tool images are not SC images:
# `ghcr.io/siliconcompiler/sc_tools` is the one SC's own CI runs tools in, and
# CI installs the framework into it at test time.

KLAYOUT = "siliconcompiler.tools.klayout"
OPENROAD = "siliconcompiler.tools.openroad"


@pytest.fixture
def quiet_restored():
    '''`main` quiets logging for the whole process, because it IS the process.

    ⚠️ Put back afterwards, or every later test that asserts on a log message
    sees nothing -- a failure three files away with no visible cause.
    '''
    before = logging.root.manager.disable
    try:
        yield
    finally:
        logging.disable(before)


###########################
# What to run
###########################

def test_a_tool_is_asked_through_its_driver():
    assert probe.command_for("klayout", "tool", KLAYOUT) == \
        ["klayout", "-zz", "-v"]
    assert probe.command_for("openroad", "tool", OPENROAD) == \
        ["openroad", "-version"]


def test_the_command_is_built_without_the_tool_being_here():
    '''⚠️ `Task.get_exe` resolves against THIS machine's PATH and raises when
    the tool is missing, which is right for a run and wrong here: the tool is
    in the image, and its absence locally says nothing at all.'''
    if shutil.which("openroad"):
        pytest.skip("openroad is installed here, so this proves nothing")

    assert probe.command_for("openroad", "tool", OPENROAD)


def test_a_tool_with_no_driver_has_nothing_to_run():
    '''Legitimate: the tool is in the image, the deployment lists it, and
    nothing here can ask its version. That is what `published_date` records.'''
    assert probe.command_for("magic", "tool", None) is None


def test_a_driver_this_process_cannot_import_has_nothing_to_run():
    assert probe.command_for("openroad", "tool", "not.a.module.here") is None


def test_a_python_name_needs_no_driver():
    command = probe.command_for("siliconcompiler", "python", None)

    assert command[:2] == ["python3", "-c"]
    assert "siliconcompiler" in command[2]


def test_a_kind_outside_the_closed_set_is_refused():
    with pytest.raises(ValueError, match="not a software kind"):
        probe.command_for("openroad", "library", OPENROAD)


###########################
# Reading what came back
###########################

def test_the_drivers_own_parser_and_normaliser_are_used():
    '''🔴 OpenROAD answers `-version` in four shapes and its parser knows all
    of them; `26Q3-2418-g3ab04b4dd1` is not a PEP 440 version at all, and
    stored raw it can never satisfy a range.'''
    answer = probe.read_answer("openroad", "tool",
                               "1 26Q3-2418-g3ab04b4dd1\n", OPENROAD)

    assert answer == ("26.3.2418", "26Q3-2418-g3ab04b4dd1")


def test_nothing_said_is_no_version():
    assert probe.read_answer("openroad", "tool", "", OPENROAD) is None
    assert probe.read_answer("openroad", "tool", "   \n", OPENROAD) is None


def test_a_python_version_is_the_last_line():
    '''Anything the interpreter warned about on its way comes first.'''
    assert probe.read_answer("x", "python", "some warning\n1.2.3\n", None) == \
        ("1.2.3", "1.2.3")


###########################
# The script, and the framing
###########################

def test_every_name_is_framed_so_the_answers_can_be_told_apart():
    text = probe.script([("openroad", "tool", OPENROAD),
                         ("magic", "tool", None)])

    assert "--sc-probe-begin:openroad" in text
    assert "--sc-probe-end:openroad" in text
    # A tool with nothing to run still gets a frame, and it is empty.
    assert "--sc-probe-begin:magic" in text


def test_the_command_is_guarded_on_the_executable_existing():
    '''🔴 Without this a missing tool leaves the shell's own `not found`
    inside the frame, and OpenROAD's `parse_version` takes the last word -- so
    an absent tool was registered at version `0`, parsed out of the error
    message saying it was absent.'''
    text = probe.script([("openroad", "tool", OPENROAD)])

    assert "command -v openroad" in text


def test_a_tool_that_is_not_there_reports_nothing(quiet_restored):
    if shutil.which("openroad"):
        pytest.skip("openroad is installed here, so this proves nothing")

    found = probe.probe([("openroad", "tool", OPENROAD)])

    assert found["openroad"] == {"kind": "tool", "version": None,
                                 "reported": None, "present": False}


def test_the_frame_survives_a_tool_that_colours_its_output():
    '''🔴 klayout wraps its version in ANSI colour when it thinks it is on a
    terminal, which put an escape in front of the marker closing its own
    frame: the frame never closed and a tool that had answered read as
    absent.'''
    output = ("--sc-probe-begin:klayout\r\n"
              "\x1b[32mKLayout 0.30.12\r\n"
              "\x1b[0m--sc-probe-end:klayout\r\n")

    assert probe.read_output([("klayout", "tool", KLAYOUT)],
                             output)["klayout"]["version"] == "0.30.12"


def test_the_trailing_newline_is_kept():
    '''🔴 `subprocess.run` hands `parse_version` output ending in one, and a
    parser is entitled to count on it: bambu's takes `stdout.split()[-3]`, so
    dropping it reads the line above the version and returns nothing.'''
    captured, _ = probe._split("--sc-probe-begin:x\nfirst\nsecond\n"
                               "--sc-probe-end:x\n")

    assert captured == {"x": "first\nsecond\n"}


def test_output_outside_any_frame_belongs_to_nobody():
    captured, _ = probe._split("noise\n--sc-probe-begin:x\nmine\n"
                               "--sc-probe-end:x\nmore noise\n")

    assert captured == {"x": "mine\n"}


def test_an_unclosed_frame_is_not_read():
    '''A tool that never returned leaves its frame open, and taking what
    followed would attribute the next tool's output to it.'''
    assert probe._split("--sc-probe-begin:x\nhalf")[0] == {}


###########################
# End to end, on this machine
###########################

def test_probing_this_machine_answers_for_what_is_here(quiet_restored):
    found = probe.probe([("siliconcompiler", "python", None),
                         ("magic", "tool", None)])

    assert found["siliconcompiler"]["kind"] == "python"
    assert found["siliconcompiler"]["version"]
    # ⚠️ `present` is None and NOT False: nobody drives magic, so presence
    # could not be tested -- which is not the same as the image not holding it,
    # and only a test that ran and said no refuses a registration.
    assert found["magic"] == {"kind": "tool", "version": None,
                              "reported": None, "present": None}


def test_the_answer_is_one_line_behind_a_marker(capsys, quiet_restored):
    '''🔴 A container's output is not this process's alone. A tool that writes
    a banner while being asked its version lands in the same stream as the
    answer, so the caller needs something to find it by.'''
    assert probe.main(["-python", "siliconcompiler", "-tool", "magic"]) == 0

    answers = [line for line in capsys.readouterr().out.splitlines()
               if line.startswith(probe.MARKER)]

    assert len(answers) == 1
    body = json.loads(answers[0][len(probe.MARKER):])
    assert set(body) == {"siliconcompiler", "magic"}


def test_the_script_can_be_printed_for_somebody_else_to_run(capsys,
                                                            quiet_restored):
    '''What a caller with an image needs: the asking happens there, the
    reading happens where SiliconCompiler is.'''
    assert probe.main(["-script", "-tool", f"openroad={OPENROAD}"]) == 0

    printed = capsys.readouterr().out
    assert printed.startswith("#!/bin/sh")
    assert "openroad -version" in printed


def test_probing_nothing_is_a_usage_error(quiet_restored):
    '''🔴 And it is refused BEFORE the logs are quieted, or the message about
    the usage error goes with them.'''
    with pytest.raises(SystemExit):
        probe.main([])

    assert logging.root.manager.disable < logging.CRITICAL


###########################
# Three outcomes, not two
###########################

def test_present_and_silent_is_told_apart_from_not_there():
    """🔴 The rule that decides whether a registration is refused. *Present but
    would not say* is legitimate and is what `published_date` records; *not
    there at all* means a row would claim the image holds something it does
    not, and a node placed there dies.

    ⚠️ Told apart by the driver's own presence check and NEVER by the version
    failing to parse: an unguarded missing tool leaves the shell's own
    `openroad: not found` in the frame, and OpenROAD's parser takes the last
    word -- so a parse-failure test would register a missing tool at version
    `0` instead of refusing it.
    """
    wanted = [("openroad", "tool", OPENROAD)]

    silent = probe.read_output(wanted, "--sc-probe-begin:openroad\n"
                                       "--sc-probe-here:openroad\n"
                                       "it printed something unparsable\n"
                                       "--sc-probe-end:openroad\n")
    assert silent["openroad"]["present"] is True

    absent = probe.read_output(wanted, "--sc-probe-begin:openroad\n"
                                       "--sc-probe-end:openroad\n")
    assert absent["openroad"]["present"] is False


def test_the_presence_marker_is_emitted_only_where_the_thing_is():
    text = probe.script([("openroad", "tool", OPENROAD)])

    assert "command -v openroad" in text
    # Inside the guard, so it is printed only when the guard passes.
    assert text.index("command -v openroad") < text.index("--sc-probe-here:openroad")


def test_a_python_name_reports_absence_as_package_not_found():
    """✅ The packaging machinery's own answer, not a parse that failed."""
    command = probe.command_for("x", "python", None)

    assert "PackageNotFoundError" in command[2]
    assert "--sc-probe-here:x" in command[2]


def test_a_tool_read_through_a_distribution_is_asked_the_python_way():
    """🔴 `slang` has no executable at all -- its driver runs pyslang in this
    process -- and still has to be placed in an image holding it. The marker
    carries the TOOL's name, because that is what the registry calls it."""
    command = probe.command_for("slang", "tool", None, "pyslang")

    assert command[:2] == ["python3", "-c"]
    assert "'pyslang'" in command[2]
    assert "--sc-probe-here:slang" in command[2]

    found = probe.read_output(
        [("slang", "tool", None, "pyslang")],
        "--sc-probe-begin:slang\n--sc-probe-here:slang\n11.0.0\n"
        "--sc-probe-end:slang\n")

    assert found["slang"] == {"kind": "tool", "version": "11.0.0",
                              "reported": "11.0.0", "present": True}
