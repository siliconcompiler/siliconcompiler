import json
import logging

import pytest

from siliconcompiler.remote.server import probe


# What is actually inside an image, asked rather than declared. Nothing here
# needs a server, a store or a container: the probe is the thing that runs
# INSIDE one, so it has to be drivable on its own.


def test_a_python_distribution_is_asked_through_importlib():
    assert probe.python_version("siliconcompiler")
    assert probe.python_version("packaging")


def test_a_distribution_that_is_not_installed_says_nothing():
    '''None and not an exception. It is the ordinary answer for an image that
    does not hold something, and it is what `published_date` records.'''
    assert probe.python_version("definitely-not-installed-here") is None


def test_a_tool_is_asked_by_running_it():
    '''🔴 Through the driver's own `exe`, `vswitch` and `parse_version`.
    OpenROAD answers `-version` with four different shapes and its parser
    knows all of them; anything here that re-implemented the call would be a
    second copy that drifts from the one a real run uses.'''
    import shutil

    # The EXECUTABLE and not the python distribution of the same name: klayout
    # ships bindings and is a tool in SiliconCompiler, and it is the tool this
    # asks about.
    if not shutil.which("klayout"):
        pytest.skip("the klayout executable is not on this machine")

    comparable, reported = probe.tool_version("klayout",
                                              "siliconcompiler.tools.klayout")
    assert comparable and reported


def test_a_tool_with_no_driver_reports_no_version():
    '''⚠️ Legitimate, and not an error: the tool is in the image, this
    deployment lists it, and nothing here can ask its version.'''
    assert probe.tool_version("magic", None) is None


def test_a_driver_that_is_not_in_this_image_reports_no_version():
    assert probe.tool_version("openroad", "not.a.module.here") is None


def test_the_driver_is_never_guessed_from_the_name():
    '''🔴 The convention is already wrong in this tree: `kepler-formal` is
    driven from `siliconcompiler.tools.keplerformal`. A guess would work for
    SiliconCompiler's own drivers and quietly fail for a site library's, which
    is the worst shape a derivation can have -- so the module is recorded at
    registration and handed in.'''
    import importlib.util

    assert importlib.util.find_spec("siliconcompiler.tools.keplerformal")
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("siliconcompiler.tools.kepler-formal")


def test_the_package_of_a_driver_is_walked_for_its_tasks():
    '''⚠️ A package's `__init__` usually holds the ABSTRACT base -- the one
    that calls `set_exe` -- and the buildable tasks are in its submodules. A
    probe that imported only what it was told would find a class it cannot
    build and report no version for a tool that is right there.'''
    found = probe._drivers("klayout", "siliconcompiler.tools.klayout")

    assert len(found) > 1
    assert any(cls.__module__ != "siliconcompiler.tools.klayout" for cls in found)


def test_probe_reports_a_kind_and_a_version_for_each_name():
    found = probe.probe([("siliconcompiler", "python", None),
                         ("magic", "tool", None)])

    assert found["siliconcompiler"]["kind"] == "python"
    assert found["siliconcompiler"]["version"]
    assert found["magic"] == {"kind": "tool", "version": None, "reported": None}


def test_a_kind_outside_the_closed_set_is_refused():
    with pytest.raises(ValueError, match="not a software kind"):
        probe.probe([("siliconcompiler", "library", None)])


@pytest.fixture
def quiet_restored():
    '''`main` quiets logging for the whole process, because it IS the process.

    ⚠️ Put back afterwards, or every later test that asserts on a log message
    sees nothing -- which is a failure three files away with no visible cause.
    '''
    before = logging.root.manager.disable
    try:
        yield
    finally:
        logging.disable(before)


def test_the_answer_is_one_line_behind_a_marker(capsys, quiet_restored):
    '''🔴 A container's output is not this process's alone. A tool that writes
    a banner while being asked its version lands in the same stream as the
    answer, so the caller needs something to find it by.'''
    assert probe.main(["-python", "siliconcompiler", "-tool", "magic"]) == 0

    printed = capsys.readouterr().out.splitlines()
    answers = [line for line in printed if line.startswith(probe.MARKER)]

    assert len(answers) == 1
    body = json.loads(answers[0][len(probe.MARKER):])
    assert set(body) == {"siliconcompiler", "magic"}
    assert body["magic"]["kind"] == "tool"

    # And the noise is off unless asked for, which is cheaper than relying on
    # the marker alone.
    assert logging.root.manager.disable >= logging.CRITICAL


def test_probing_nothing_is_a_usage_error(quiet_restored):
    '''🔴 And it is refused BEFORE the logs are quieted, or the message about
    the usage error goes with them.'''
    with pytest.raises(SystemExit):
        probe.main([])

    assert logging.root.manager.disable < logging.CRITICAL


def test_the_drivers_own_normalisation_is_applied():
    '''🔴 Not cosmetic. OpenROAD reports `26Q3-2418-g3ab04b4dd1`, which is not
    a PEP 440 version at all -- stored raw it can never satisfy a range, so
    `openroad>=26.3` would be refused against an image that plainly has it. Its
    driver knows how to turn that into a comparable one, the same way its
    `parse_version` knows the four shapes the tool answers in.'''
    from packaging.version import Version
    from siliconcompiler.tools.openroad import OpenROADTask

    raw = "26Q3-2418-g3ab04b4dd1"
    assert Version(OpenROADTask.normalize_version(OpenROADTask(), raw))


def test_what_the_tool_said_is_reported_beside_what_compares():
    '''`verilator` says `5.052` and PEP 440 makes that `5.52`. The catalogue
    needs the second; a person reading a log is owed the first.'''
    found = probe.probe([("siliconcompiler", "python", None)])

    assert found["siliconcompiler"]["reported"] == \
        found["siliconcompiler"]["version"]
