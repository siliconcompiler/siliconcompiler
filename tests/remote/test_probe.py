import json
import logging
import shutil
import subprocess

import pytest

from siliconcompiler.remote.server.software import probe


# What is inside an image, asked rather than declared: the command runs in the
# image and the parsing happens here, since most tool images hold no SC.

KLAYOUT = "siliconcompiler.tools.klayout"
OPENROAD = "siliconcompiler.tools.openroad"


@pytest.fixture
def quiet_restored():
    '''`main` quiets logging for the whole process; put it back, or later tests
    asserting on a log message see nothing.'''
    before = logging.root.manager.disable
    try:
        yield
    finally:
        logging.disable(before)


def framed(name, *lines, here=True):
    '''One name's frame as the script prints it.'''
    return "".join([f"--sc-probe-begin:{name}\n", f"--sc-probe-here:{name}\n" if here else "",
                    *(f"{line}\n" for line in lines), f"--sc-probe-end:{name}\n"])


###########################
# What to run
###########################

@pytest.mark.parametrize("name,driver,expected", [
    ("klayout", KLAYOUT, ["klayout", "-zz", "-v"]),
    ("openroad", OPENROAD, ["openroad", "-version"]),
    # A tool nothing here drives: what `published_date` records.
    ("magic", None, None),
    ("openroad", "not.a.module.here", None),
])
def test_a_tool_is_asked_through_its_driver_or_not_at_all(name, driver, expected):
    '''⚠️ Built without the tool on this machine's PATH (`Task.get_exe` would
    raise): the tool is in the image, and its absence here says nothing.'''
    assert probe.command_for(name, "tool", driver) == expected


def test_a_python_name_needs_no_driver_and_reports_absence_as_package_not_found():
    command = probe.command_for("siliconcompiler", "python", None)

    assert command[:2] == ["python3", "-c"]
    assert "siliconcompiler" in command[2]
    assert "PackageNotFoundError" in command[2]
    assert "--sc-probe-here:siliconcompiler" in command[2]


def test_a_kind_outside_the_closed_set_is_refused():
    with pytest.raises(ValueError, match="not a software kind"):
        probe.command_for("openroad", "library", OPENROAD)


###########################
# Reading what came back
###########################

@pytest.mark.parametrize("name,kind,said,driver,expected", [
    # 🔴 The driver's own parser and normaliser: `26Q3-...` is not PEP 440.
    ("openroad", "tool", "1 26Q3-2418-g3ab04b4dd1\n", OPENROAD,
     ("26.3.2418", "26Q3-2418-g3ab04b4dd1")),
    ("openroad", "tool", "", OPENROAD, None),
    ("openroad", "tool", "   \n", OPENROAD, None),
    # A python version is the last line, after anything the interpreter warned.
    ("x", "python", "some warning\n1.2.3\n", None, ("1.2.3", "1.2.3")),
])
def test_an_answer_is_read_by_the_drivers_parser(name, kind, said, driver, expected):
    assert probe.read_answer(name, kind, said, driver) == expected


###########################
# The script, and the framing
###########################

def test_the_script_frames_every_name_and_guards_it_on_the_executable():
    '''🔴 Unguarded, a missing tool leaves the shell's `not found` in the frame
    and OpenROAD's parser registered it at version `0`. The presence marker is
    inside the guard; a tool with nothing to run still gets an empty frame; and
    each answer is cut to its share in the image.'''
    text = probe.script([("openroad", "tool", OPENROAD), ("magic", "tool", None)])

    assert "--sc-probe-begin:openroad" in text
    assert "--sc-probe-end:openroad" in text
    assert "--sc-probe-begin:magic" in text
    assert text.index("command -v openroad") < text.index("--sc-probe-here:openroad")
    assert f"tail -c {probe.ANSWER_BYTES}" in text


def test_the_frame_survives_a_tool_that_colours_its_output():
    '''🔴 klayout's ANSI escape before the closing marker left the frame open,
    so a tool that answered read as absent.'''
    output = ("--sc-probe-begin:klayout\r\n"
              "\x1b[32mKLayout 0.30.12\r\n"
              "\x1b[0m--sc-probe-end:klayout\r\n")

    assert probe.read_output([("klayout", "tool", KLAYOUT)],
                             output)["klayout"]["version"] == "0.30.12"


@pytest.mark.parametrize("output,expected", [
    # 🔴 The trailing newline is kept: bambu's parser takes `split()[-3]`.
    ("--sc-probe-begin:x\nfirst\nsecond\n--sc-probe-end:x\n", {"x": "first\nsecond\n"}),
    # Output outside any frame belongs to nobody.
    ("noise\n--sc-probe-begin:x\nmine\n--sc-probe-end:x\nmore noise\n", {"x": "mine\n"}),
    # An unclosed frame is a tool that never returned; what followed is not its.
    ("--sc-probe-begin:x\nhalf", {}),
])
def test_a_frame_is_split_out_exactly(output, expected):
    assert probe._split(output)[0] == expected


###########################
# End to end, on this machine
###########################

def test_probing_this_machine_answers_for_what_is_here(quiet_restored):
    '''⚠️ magic's `present` is None, not False: nobody drives it, so presence
    was not tested, and only a test that ran and said no refuses a row.'''
    found = probe.probe([("siliconcompiler", "python", None), ("magic", "tool", None),
                         ("openroad", "tool", OPENROAD)])

    assert found["siliconcompiler"]["kind"] == "python"
    assert found["siliconcompiler"]["version"]
    assert found["magic"] == {"kind": "tool", "version": None, "reported": None,
                              "unparsed": None, "present": None}
    if not shutil.which("openroad"):
        assert found["openroad"] == {"kind": "tool", "version": None, "reported": None,
                                     "unparsed": None, "present": False}


def test_the_answer_is_one_line_behind_a_marker(capsys, quiet_restored):
    '''🔴 A container's output is shared with any banner a tool prints.'''
    assert probe.main(["-python", "siliconcompiler", "-tool", "magic"]) == 0

    answers = [line for line in capsys.readouterr().out.splitlines()
               if line.startswith(probe.MARKER)]

    assert len(answers) == 1
    body = json.loads(answers[0][len(probe.MARKER):])
    assert set(body) == {"siliconcompiler", "magic"}


def test_the_script_can_be_printed_for_somebody_else_to_run(capsys, quiet_restored):
    assert probe.main(["-script", "-tool", f"openroad={OPENROAD}"]) == 0

    printed = capsys.readouterr().out
    assert printed.startswith("#!/bin/sh")
    assert "openroad -version" in printed


def test_probing_nothing_is_a_usage_error(quiet_restored):
    '''🔴 Refused BEFORE the logs are quieted, or its message goes with them.'''
    with pytest.raises(SystemExit):
        probe.main([])

    assert logging.root.manager.disable < logging.CRITICAL


###########################
# Three outcomes, not two
###########################

def test_present_and_silent_is_told_apart_from_not_there():
    '''🔴 Decides whether a registration is refused, and by the presence
    marker, NEVER by a parse failing (an unguarded `not found` parses as `0`).'''
    wanted = [("openroad", "tool", OPENROAD)]

    silent = probe.read_output(wanted, framed("openroad", "it printed something unparsable"))
    absent = probe.read_output(wanted, framed("openroad", here=False))

    assert silent["openroad"]["present"] is True
    assert absent["openroad"]["present"] is False


def test_a_tool_read_through_a_distribution_is_asked_the_python_way():
    '''🔴 `slang` has no executable (its driver runs pyslang); the marker
    carries the TOOL's name, which is what the registry calls it.'''
    command = probe.command_for("slang", "tool", None, "pyslang")

    assert command[:2] == ["python3", "-c"]
    assert "'pyslang'" in command[2]
    assert "--sc-probe-here:slang" in command[2]

    found = probe.read_output([("slang", "tool", None, "pyslang")],
                              framed("slang", "11.0.0"))

    assert found["slang"] == {"kind": "tool", "version": "11.0.0", "reported": "11.0.0",
                              "unparsed": None, "present": True}


@pytest.mark.parametrize("said,version,unparsed", [
    # 🔴 Not a version: dropped, kept for the operator, never coerced.
    ("initialize", None, "initialize"),
    ("1.2.3", "1.2.3", None),
    # Cut again here, for an image whose `tail` is missing or is not `tail`.
    ("noise\n" * 10000 + "1.2.3", "1.2.3", None),
])
def test_an_answer_is_a_version_or_is_kept_as_unparsed(said, version, unparsed):
    found = probe.read_output([("x", "python", None)], framed("x", said))["x"]

    assert (found["version"], found["unparsed"], found["present"]) == \
        (version, unparsed, True)


###########################
# 🔴 Bounded: the output is somebody else's image's
###########################

def test_each_answer_is_cut_to_its_share_in_the_image():
    '''The END is kept, since parsers read the last lines.'''
    fragment = probe._bounded(["sh", "-c", "yes noise | head -c 100000; echo 1.2.3"])
    said = subprocess.run(["sh", "-c", fragment], stdout=subprocess.PIPE).stdout

    assert len(said) <= probe.ANSWER_BYTES
    assert said.endswith(b"1.2.3\n")


def test_a_probe_that_printed_too_much_is_not_believed():
    '''Refused rather than read up to the cut, where a frame reads as absent.'''
    with pytest.raises(ValueError, match="more than"):
        probe.read_output([("x", "python", None)], "x" * (probe.MAX_OUTPUT + 1))


def test_the_interpreter_is_asked_by_running_it():
    '''surface D293: the image's own Python (`python`, kind `interpreter`) is
    present when it answered, and read back as `X.Y.Z`.'''
    wanted = [(probe.INTERPRETER, "interpreter", None)]
    output = subprocess.run(["sh", "-c", probe.script(wanted)], capture_output=True,
                            text=True, check=True).stdout
    found = probe.read_output(wanted, output)[probe.INTERPRETER]

    here = subprocess.run(["python3", "-c", "import sys; print('%d.%d.%d' % "
                                            "sys.version_info[:3])"],
                          capture_output=True, text=True, check=True).stdout.strip()
    assert (found["kind"], found["present"], found["version"]) == ("interpreter", True, here)
