'''
What is actually inside an image, asked rather than declared.

🔴 **The registry's one unverified claim was `image_contents`.** An operator
typed what an image held and nothing ever opened it to check, so a wrong row
meant a job ran in a container without what it asked for and failed at run time
rather than at submit. This is the other half: ask the image.

**Two mechanisms, and the registry says which applies to which name:**

``python``  ``importlib.metadata.version(<name>)``
``tool``    the driver's ``exe`` and ``vswitch``, read back through its
            ``parse_version`` and ``normalize_version``

🔴 **The command runs in the image and the PARSING happens here, and that split
is the whole design.** An earlier version ran this module inside the image,
which works only for an image that has SiliconCompiler installed -- and most
tool images do not. ``ghcr.io/siliconcompiler/sc_tools`` is the obvious case: it
is the image SiliconCompiler's own CI runs its tools in, and CI installs the
framework into it at test time. Requiring the framework in every image an
operator wants to register is requiring them to rebuild somebody else's image.

So :func:`script` produces a shell script that runs the tools and frames each
answer, and :func:`read_output` turns what came back into versions. The caller
in between is whatever can start a container.

🔴 **Neither the kind nor the driver is guessed.** Both are columns on
``software``, set when the name is registered. A guess would work for
SiliconCompiler's own in-tree drivers and quietly fail for everything else -- a
driver can live in any package, and the in-tree path is not even reliable
in-tree, where ``kepler-formal`` is driven from
``siliconcompiler.tools.keplerformal``.
'''

import argparse
import importlib
import importlib.metadata
import json
import logging
import pkgutil
import re
import shlex
import subprocess
import sys

from typing import Any, Dict, List, Optional, Sequence, Tuple

__all__ = ["KINDS", "MARKER", "command_for", "exe_and_switch",
           "executable_for", "probe", "read_answer", "read_output",
           "script"]


# The closed set, and each half is a mechanism rather than a label.
KINDS = ("python", "tool")

# What a caller greps for when it wants only the answer. One line, JSON after.
MARKER = "sc-probe:"

# 🔴 How one name's answer is framed in the output, and it is framed because a
# version check RUNS the tool: anything the tool prints on its way -- a banner,
# a licence line, a warning -- lands in the same stream. Everything between one
# name's markers belongs to it, and everything outside them belongs to nobody.
_BEGIN = "--sc-probe-begin:"
_END = "--sc-probe-end:"

# 🔴 Emitted only where the thing is THERE, and this is the load-bearing one.
# *Present but would not say* is a legitimate row -- it is what
# `published_date` exists for -- while *not there at all* has to refuse the
# whole image registration, because writing the row says the image holds
# something it does not, and then a node is placed in it and dies.
#
# ⚠️ **Never told apart by the version failing to parse.** An unguarded
# missing tool leaves the shell's own `openroad: not found` in the frame, and
# OpenROAD's `parse_version` takes the last word -- so a parse-failure test
# would register a missing tool at version `0` instead of refusing it, which
# is the exact bug this rule exists to prevent wearing the rule's own clothes.
# Presence is the driver's own check: the executable existing, or
# `PackageNotFoundError` not being raised.
_HERE = "--sc-probe-here:"

# 🔴 What runs a python distribution's version check, and it says PRESENT
# before it says anything else. Absence is `PackageNotFoundError` -- the
# packaging machinery's own answer -- and never a version that failed to parse.
_PYTHON_CHECK = (
    "import importlib.metadata as m\n"
    "try: v = m.version({name!r})\n"
    "except m.PackageNotFoundError: raise SystemExit(0)\n"
    "print({here!r})\n"
    "print(v)\n"
)

# CSI and the rest of the escape sequences a colouring tool emits.
_ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")

logger = logging.getLogger("sc-probe")


def command_for(name: str, kind: str, driver: Optional[str] = None,
                version_package: Optional[str] = None) -> Optional[List[str]]:
    '''What to run inside the image to make this name answer.

    ⚠️ **Read without `shutil.which`.** `Task.get_exe` resolves the executable
    against THIS machine's PATH and raises when it is missing, which is the
    right behaviour for a run and the wrong one here: the tool is in the image,
    not here, and its absence locally says nothing at all.

    None where nothing can ask: a python name needs no driver and always has a
    command, a tool with no driver has no executable to name, and a driver this
    process cannot import cannot be read.
    '''
    if kind not in KINDS:
        raise ValueError(f"{kind} is not a software kind")

    # 🔴 A tool can have no executable at all -- slang drives pyslang in this
    # process -- and its version is then the distribution's. The marker still
    # carries the TOOL's name, because that is what the registry calls it.
    if kind == "python" or version_package:
        return ["python3", "-c",
                _PYTHON_CHECK.format(name=version_package or name,
                                     here=_HERE + name)]

    exe, vswitch = exe_and_switch(name, driver)
    if not exe or not vswitch:
        # A tool whose driver names no version switch cannot be ASKED its
        # version. ⚠️ It can still be found -- see `executable_for` -- and
        # those are two different questions: `kepler-formal`, `icepack` and
        # `vcd2fst` all name an executable and no switch, so they are present
        # and mute rather than absent.
        return None
    return [exe, *vswitch]


def exe_and_switch(name: str, driver: Optional[str]):
    '''What the driver says to run, and how to ask it its version.'''
    asked = _ask_driver(name, driver, lambda task: (task.get("exe"),
                                                    task.get("vswitch")))
    return asked if asked else (None, None)


def executable_for(name: str, kind: str, driver: Optional[str] = None,
                   version_package: Optional[str] = None) -> Optional[str]:
    '''The program whose existence means this name is THERE.

    🔴 **Separate from the version command, and that separation is the bug
    fix.** Tying presence to being able to ask a version made every tool whose
    driver names no version switch untestable -- so nothing declared it, no
    image held it, and a flow reaching for it was refused although the binary
    was right there. That is the `bsc` failure inverted: refusing a tool the
    image has.

    None where presence is decided some other way -- a python distribution
    answers for itself -- or cannot be decided at all.
    '''
    if kind == "python" or version_package:
        return None
    return exe_and_switch(name, driver)[0]


def read_answer(name: str, kind: str, output: str,
                driver: Optional[str] = None) -> Optional[Tuple[str, str]]:
    '''One name's captured output, as ``(comparable, reported)``.

    🔴 **Two numbers, because they differ and both are wanted.** The comparable
    one is what gets stored and matched; what the tool actually printed is what
    an operator should see in a log. `verilator` says `5.052` and PEP 440 makes
    that `5.52`; OpenROAD says `26Q3-2418-g3ab04b4dd1` and its own normaliser
    makes that `26.3.2418`.

    🔴 **The driver's `parse_version` and `normalize_version`, never a rule of
    this module's own.** OpenROAD answers `-version` in four different shapes
    and its parser knows all of them. Anything here that re-implemented the
    reading would be a second copy that drifts from the one a real run uses.
    '''
    text = output or ""
    if not text.strip():
        return None

    if kind == "python":
        # The LAST line, because anything the interpreter warned about on its
        # way comes first. A distribution's version needs no normalising: it
        # is PEP 440 already, by the packaging that declared it.
        said = text.strip().splitlines()[-1].strip()
        return (said, said) if said else None

    def read(task):
        reported = task.parse_version(text)
        if not reported:
            return None
        try:
            return task.normalize_version(reported), reported
        except Exception as e:                                   # noqa: BLE001
            # A normaliser that cannot read its own tool's output. The raw
            # string is still true and still selectable by name; what it loses
            # is being matchable against a range.
            logger.debug(f"{name}: could not normalize {reported}: {e}")
            return reported, reported

    return _ask_driver(name, driver, read)


def script(wanted: Sequence[Tuple[str, str, Optional[str]]]) -> str:
    '''A shell script that asks every name, framed so the answers can be told
    apart.

    ⚠️ One script and one container rather than one each. A container start
    per tool is a second of nothing eleven times over, and the framing already
    does what separate runs would have bought.
    '''
    lines = ["#!/bin/sh"]
    for name, kind, driver, package in map(_want, wanted):
        command = command_for(name, kind, driver, package)
        exe = executable_for(name, kind, driver, package)
        lines.append(f"echo {shlex.quote(_BEGIN + name)}")

        if kind == "python" or package:
            # The python check reports its own presence: it prints the marker
            # only once `importlib.metadata` has answered, so absence is
            # `PackageNotFoundError` and nothing else.
            if command:
                lines.append(f"{shlex.join(command)} 2>&1 || true")
        elif exe:
            # 🔴 Guarded on the executable EXISTING, and this is not
            # belt-and-braces. Without it a missing tool leaves the shell's own
            # `openroad: not found` inside the frame, and OpenROAD's
            # `parse_version` takes the last word of what it is given -- so an
            # absent tool was registered at version `0`, parsed out of the
            # error message saying it was absent. An empty frame is the honest
            # answer and the one that ends in `published_date`.
            #
            # `2>&1` because a tool is as likely to answer on stderr, and
            # `|| true` because a non-zero exit is ordinary: several print
            # their version and then complain about having nothing to do.
            lines.append(f"if command -v {shlex.quote(exe)} "
                         "> /dev/null 2>&1; then")
            lines.append(f"  echo {shlex.quote(_HERE + name)}")
            # ⚠️ The version is asked INSIDE the presence guard and only where
            # there is a switch to ask with. A tool that names an executable
            # and no switch is present and mute, which is a row --
            # `published_date` -- and not an absence.
            if command:
                lines.append(f"  {shlex.join(command)} 2>&1 || true")
            lines.append("fi")
        lines.append(f"echo {shlex.quote(_END + name)}")
    return "\n".join(lines) + "\n"


def read_output(wanted: Sequence[Tuple[str, str, Optional[str]]],
                output: str) -> Dict[str, Dict[str, Any]]:
    '''What :func:`script` printed, as name to kind and version.

    ``version`` is None where nothing answered. Not an error: a tool this
    deployment lists and nobody drives, or one that is not in this image, has
    no version to read -- and saying so is what ``published_date`` is for.
    '''
    captured, present = _split(output or "")

    found: Dict[str, Dict[str, Any]] = {}
    for name, kind, driver, package in map(_want, wanted):
        # A version read through a distribution is read the python way,
        # whatever the registry calls the name.
        answer = read_answer(name, "python" if package else kind,
                             captured.get(name, ""), driver)
        version, reported = answer if answer else (None, None)
        found[name] = {"kind": kind, "version": version, "reported": reported,
                       # 🔴 Three outcomes, not two. `present` and no version
                       # is legitimate and is what `published_date` records;
                       # absent means the image does not hold what a row would
                       # claim it does, and that refuses the registration.
                       #
                       # ⚠️ None where presence could not be TESTED at all --
                       # a tool nobody drives, which stays legitimate -- and
                       # that is not the same as absent and must not be
                       # treated as it. Only a test that ran and said no is
                       # grounds to refuse an image.
                       "present": (present.get(name, False)
                                   if _testable(name, kind, driver, package)
                                   else None)}
    return found


def _testable(name: str, kind: str, driver: Optional[str],
              package: Optional[str]) -> bool:
    """Whether presence could be asked about at all.

    ⚠️ Not the same as whether a VERSION could be. A tool naming an executable
    and no version switch is testable and mute; one naming neither cannot be
    tested, and untestable is not absent.
    """
    if kind == "python" or package:
        return command_for(name, kind, driver, package) is not None
    return executable_for(name, kind, driver, package) is not None


def _want(entry):
    """One `(name, kind, driver[, version_package])`, filled out."""
    name, kind, driver = entry[0], entry[1], entry[2]
    return name, kind, driver, (entry[3] if len(entry) > 3 else None)


def probe(wanted: Sequence[Tuple[str, str, Optional[str]]],
          run=None) -> Dict[str, Dict[str, Any]]:
    '''Ask about each ``(name, kind, driver)``, running the script somewhere.

    ``run`` takes the script and returns what it printed; it defaults to this
    machine, which is what makes the CLI useful for *what does this host hold*.
    A caller with an image passes something that starts a container.

    🔴 One path for both. The alternative -- a local implementation beside a
    container one -- is two answers to the same question, and the one nobody
    runs is the one that rots.
    '''
    return read_output(wanted, (run or _locally)(script(wanted)))


def _locally(text: str) -> str:
    done = subprocess.run(["sh"], input=text, stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT, universal_newlines=True)
    return done.stdout


######################################################################
# Reaching the driver
######################################################################

def _split(output: str):
    '''Everything between each name's markers, and whether it was there.

    Returns ``(captured, present)``. A name with no presence marker inside its
    frame either was not there, or could not be tested -- the caller knows
    which, because it knows whether it asked for a presence test.
    '''
    captured: Dict[str, str] = {}
    present: Dict[str, bool] = {}
    name: Optional[str] = None
    lines: List[str] = []

    for line in output.splitlines():
        # ⚠️ Escapes stripped before the marker is looked for. A tool that
        # thinks it is on a terminal colours its output, and klayout put
        # `\x1b[0m` in front of the marker closing its own frame -- so the
        # frame never closed and a tool that had answered read as absent.
        # Giving the container no TTY is the real fix and this is the belt:
        # nothing says a tool checks before colouring.
        stripped = _ANSI.sub("", line).strip()
        if stripped.startswith(_BEGIN):
            name, lines = stripped[len(_BEGIN):], []
            present.setdefault(name, False)
        elif stripped.startswith(_HERE):
            if name is not None and stripped[len(_HERE):] == name:
                present[name] = True
        elif stripped.startswith(_END):
            if name is not None and stripped[len(_END):] == name:
                # 🔴 The trailing newline is kept, and it is not cosmetic.
                # `subprocess.run` hands `parse_version` output that ends in
                # one, and a parser is entitled to count on that: bambu's
                # takes `stdout.split('\n')[-3]`, so dropping it reads the
                # line above the version and returns nothing. Whatever this
                # reconstructs has to be what a real run would have passed.
                captured[name] = "\n".join(lines) + "\n"
            name, lines = None, []
        elif name is not None:
            lines.append(line)

    return captured, present


def _ask_driver(name: str, driver: Optional[str], read):
    '''Build each Task in a driver module and hand the first that matches to
    ``read``.

    More than one class is tried, because the one that sets the executable is
    usually a base the concrete tasks inherit and an abstract base cannot be
    built.
    '''
    for task_cls in _drivers(name, driver):
        try:
            answer = _with_task(task_cls, name, read)
        except Exception as e:                                   # noqa: BLE001
            # Ordinary: an abstract base, or a class whose make_docs needs
            # something this machine has not got. The next one is tried.
            logger.debug(f"{name}/{task_cls.__name__}: {e}")
            continue
        if answer:
            return answer
    return None


def _with_task(task_cls, name: str, read):
    '''Build one task the way the docs build it, bind it, and read from it.

    🔴 **`make_docs()` does the building, and that is the point of using it.**
    What a task needs around it is the task's own knowledge and it differs: an
    OpenROAD task needs an `ASIC` project with a real PDK target loaded, a
    builtin task needs a bare `Project`, and a dozen classes override
    `make_docs` to say so. Scaffolding built here would be a second answer to
    that question -- right for the tasks somebody checked, silently wrong for
    the rest, and stale the first time a driver needed something new.

    ⚠️ **One thing has to be added back: `make_docs` returns an UNBOUND task.**
    `exe` and `vswitch` are set per step and index -- that is what `setup()`
    does -- so reading them off the returned object gets nothing. The project
    it was built in is reachable as the schema's root, and re-entering a node
    on it binds what `setup()` wrote.
    '''
    from siliconcompiler.scheduler import SchedulerNode

    built = task_cls.make_docs()
    node = SchedulerNode(built._parent(root=True), "<step>", "<index>")

    with node.task.runtime(node) as task:
        if task.tool() != name:
            return None
        return read(task)


def _drivers(name: str, driver: Optional[str]) -> List[Any]:
    '''The Task classes in one module that drive one tool.

    Bounded by the module the registry named, so nothing here searches: what is
    imported is what was recorded, and the only filter is what each class says
    it drives.
    '''
    from siliconcompiler import Task

    if not driver:
        return []

    try:
        module = importlib.import_module(driver)
    except Exception as e:                                       # noqa: BLE001
        logger.debug(f"{name}: could not import {driver}: {e}")
        return []

    # ⚠️ A package's `__init__` usually holds the ABSTRACT base -- the one that
    # calls `set_exe` -- and the buildable tasks are in its submodules. So a
    # package is walked: importing only what was named finds a class that
    # cannot be instantiated and reports no version for a tool that is right
    # there.
    for found in pkgutil.walk_packages(getattr(module, "__path__", []),
                                       prefix=f"{driver}."):
        try:
            importlib.import_module(found.name)
        except Exception as e:                                   # noqa: BLE001
            logger.debug(f"{found.name}: {e}")

    return [task_cls for task_cls in _subclasses(Task)
            if (task_cls.__module__ or "").startswith(driver)]


def _subclasses(cls) -> List[Any]:
    found: List[Any] = []
    for child in cls.__subclasses__():
        if child not in found:
            found.append(child)
        for grandchild in _subclasses(child):
            if grandchild not in found:
                found.append(grandchild)
    return found


######################################################################
# Asking this machine
######################################################################

def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python3 -m siliconcompiler.remote.server.probe",
        description="What this machine holds: one JSON line, behind a marker.")
    parser.add_argument(
        "-python", dest="python", action="append", default=[], metavar="<name>",
        help="a distribution in the interpreter, asked through "
             "importlib.metadata. Repeatable")
    parser.add_argument(
        "-tool", dest="tools", action="append", default=[],
        metavar="<name>[=<driver module>]",
        help="an executable, asked through its Task driver. Repeatable. "
             "Without a driver module it is reported with no version, which "
             "is the honest answer for a tool nobody here drives")
    parser.add_argument(
        "-script", action="store_true",
        help="print the shell script instead of running it, for a caller that "
             "will run it somewhere else -- inside an image, say")
    parser.add_argument("-verbose", action="store_true",
                        help="let SiliconCompiler's own logging through")
    args = parser.parse_args(argv)

    wanted: List[Tuple[str, str, Optional[str]]] = [
        (name, "python", None) for name in args.python]
    for entry in args.tools:
        name, _, driver = entry.partition("=")
        if not name:
            parser.error(f"{entry!r} is not <name>[=<driver module>]")
        wanted.append((name.strip(), "tool", driver.strip() or None))

    if not wanted:
        parser.error("nothing to probe: give at least one -python or -tool")

    # 🔴 After the arguments are checked, and off by default: a usage error
    # that had already quieted the logs would take the message about itself
    # with it.
    #
    # ⚠️ Process-wide and nothing puts it back, which is right for a process
    # whose whole job is this and wrong for anything else.
    if not args.verbose:
        logging.disable(logging.CRITICAL)

    if args.script:
        sys.stdout.write(script(wanted))
        return 0

    sys.stdout.write(MARKER + json.dumps(probe(wanted)) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
