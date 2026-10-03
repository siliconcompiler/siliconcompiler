'''
What is actually inside an image, asked rather than declared.

🔴 `image_contents` is the registry's one unverified claim, so this asks the
image: ``setup/server/bootstrap.py`` runs it in each image it registers.

``python``       ``importlib.metadata.version(<name>)``
``tool``         the driver's ``exe`` and ``vswitch``, read back through its
                 ``parse_version`` and ``normalize_version``
``interpreter``  the image's own ``python3``, as ``X.Y.Z`` (surface D293)

🔴 The command runs in the image and the parsing happens here: most tool images
(``sc_tools`` included) have no SiliconCompiler. :func:`script` writes the shell
script, :func:`read_output` reads what came back; the kind and driver are
registered columns, never guessed.
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

__all__ = ["ANSWER_BYTES", "INTERPRETER", "KINDS", "MARKER", "MAX_OUTPUT", "command_for",
           "exe_and_switch", "executable_for", "probe", "read_answer",
           "read_output", "script"]


KINDS = ("python", "tool", "interpreter")

# The one name of the interpreter kind: the image's own Python (surface D293).
INTERPRETER = "python"

# What a caller greps for: one line, JSON after.
MARKER = "sc-probe:"

# 🔴 Each name's answer is framed: a version check runs the tool, which may print
# banners into the same stream.
_BEGIN = "--sc-probe-begin:"
_END = "--sc-probe-end:"

# 🔴 Emitted only where the thing is there. Present and mute is a row
# (`published_date`); absent refuses the registration. ⚠️ Never inferred from
# a version failing to parse.
_HERE = "--sc-probe-here:"

# Absence is `PackageNotFoundError`, never a version that failed to parse.
_PYTHON_CHECK = (
    "import importlib.metadata as m\n"
    "try: v = m.version({name!r})\n"
    "except m.PackageNotFoundError: raise SystemExit(0)\n"
    "print({here!r})\n"
    "print(v)\n"
)

_INTERPRETER_CHECK = (
    "import sys\n"
    "print({here!r})\n"
    "print('%d.%d.%d' % sys.version_info[:3])\n"
)

# 🔴 Bounded: the output comes from somebody else's image. `ANSWER_BYTES` is the
# end of one name's answer (parsers read the last lines), cut in the image and
# here; past `MAX_OUTPUT` the probe is not believed at all.
ANSWER_BYTES = 16384
MAX_OUTPUT = 1 << 20

_UNPARSED_CHARS = 200

_ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")

logger = logging.getLogger("sc-probe")


def command_for(name: str, kind: str, driver: Optional[str] = None,
                version_package: Optional[str] = None) -> Optional[List[str]]:
    '''What to run inside the image to make this name answer, or None where nothing can ask.

    ⚠️ Not `Task.get_exe`, which checks this machine's PATH, not the image's.
    '''
    if kind not in KINDS:
        raise ValueError(f"{kind} is not a software kind")

    if kind == "interpreter":
        return ["python3", "-c", _INTERPRETER_CHECK.format(here=_HERE + name)]

    # 🔴 An exe-less tool (slang) takes its distribution's version, under the tool's name.
    if kind == "python" or version_package:
        return ["python3", "-c",
                _PYTHON_CHECK.format(name=version_package or name,
                                     here=_HERE + name)]

    exe, vswitch = exe_and_switch(name, driver)
    if not exe or not vswitch:
        # ⚠️ No switch: present and mute (`executable_for`), not absent.
        return None
    return [exe, *vswitch]


def exe_and_switch(name: str, driver: Optional[str]):
    '''What the driver says to run, and how to ask it its version.'''
    asked = _ask_driver(name, driver, lambda task: (task.get("exe"),
                                                    task.get("vswitch")))
    return asked if asked else (None, None)


def executable_for(name: str, kind: str, driver: Optional[str] = None,
                   version_package: Optional[str] = None) -> Optional[str]:
    '''The program whose existence means this name is there, or None.

    🔴 Separate from the version command, or a tool with no version switch
    could never be found present.
    '''
    if kind in ("python", "interpreter") or version_package:
        return None
    return exe_and_switch(name, driver)[0]


def read_answer(name: str, kind: str, output: str,
                driver: Optional[str] = None) -> Optional[Tuple[str, str]]:
    '''One name's captured output, as ``(comparable, reported)``.

    Stored and matched vs. printed: `verilator` prints `5.052`, stored `5.52`.
    🔴 Read by the driver's own `parse_version` and `normalize_version`, never
    a second copy here that drifts.
    '''
    text = output or ""
    if not text.strip():
        return None

    if kind in ("python", "interpreter"):
        # The last line: warnings come first.
        said = text.strip().splitlines()[-1].strip()
        return (said, said) if said else None

    def read(task):
        reported = task.parse_version(text)
        if not reported:
            return None
        try:
            return task.normalize_version(reported), reported
        except Exception as e:                                   # noqa: BLE001
            # The raw string stays true; it just cannot match a range.
            logger.debug(f"{name}: could not normalize {reported}: {e}")
            return reported, reported

    return _ask_driver(name, driver, read)


def script(wanted: Sequence[Tuple[str, str, Optional[str]]]) -> str:
    '''A shell script that asks every name in one container, each answer framed.'''
    lines = ["#!/bin/sh"]
    for name, kind, driver, package in map(_want, wanted):
        command = command_for(name, kind, driver, package)
        exe = executable_for(name, kind, driver, package)
        lines.append(f"echo {shlex.quote(_BEGIN + name)}")

        if kind in ("python", "interpreter") or package:
            # Reports its own presence; ⚠️ a wrapper's program is not asked for.
            if command:
                lines.append(_bounded(command))
        elif exe:
            # 🔴 Guarded on the executable existing: otherwise OpenROAD's parser
            # reads version `0` out of the shell's `openroad: not found`.
            lines.append(f"if command -v {shlex.quote(exe)} "
                         "> /dev/null 2>&1; then")
            lines.append(f"  echo {shlex.quote(_HERE + name)}")
            if command:
                lines.append(f"  {_bounded(command)}")
            lines.append("fi")
        lines.append(f"echo {shlex.quote(_END + name)}")
    return "\n".join(lines) + "\n"


def _bounded(command: List[str]) -> str:
    '''One command, stderr included and exit ignored, cut to the last `ANSWER_BYTES`.'''
    return f"{{ {shlex.join(command)} 2>&1 || true; }} | tail -c {ANSWER_BYTES}"


def read_output(wanted: Sequence[Tuple[str, str, Optional[str]]],
                output: str) -> Dict[str, Dict[str, Any]]:
    '''What :func:`script` printed, as name to kind, version and presence.

    ValueError past `MAX_OUTPUT`: a truncated frame would read as an absent tool.
    '''
    if output and len(output) > MAX_OUTPUT:
        raise ValueError(f"the probe printed more than {MAX_OUTPUT} bytes")
    captured, present = _split(output or "")

    found: Dict[str, Dict[str, Any]] = {}
    for name, kind, driver, package in map(_want, wanted):
        answer = read_answer(name, "python" if package else kind,
                             captured.get(name, ""), driver)
        version, reported = answer if answer else (None, None)

        # 🔴 Not PEP 440 is no version, kept in `unparsed` rather than
        # rewritten (`images.register_version`).
        unparsed = None
        from siliconcompiler.remote.server.software.images import _is_pep440

        if version is not None and not _is_pep440(version):
            version, unparsed = None, (reported or version)[:_UNPARSED_CHARS]

        # ⚠️ Whether presence could be tested; untestable is not absent.
        testable = (command_for(name, kind, driver, package)
                    if kind in ("python", "interpreter") or package
                    else executable_for(name, kind, driver, package)) is not None

        found[name] = {"kind": kind, "version": version, "reported": reported,
                       "unparsed": unparsed,
                       # 🔴 Three outcomes: only False refuses an image; None
                       # is untested.
                       "present": present.get(name, False) if testable else None}
    return found


def _want(entry):
    """One `(name, kind, driver[, version_package])`, filled out."""
    name, kind, driver = entry[0], entry[1], entry[2]
    return name, kind, driver, (entry[3] if len(entry) > 3 else None)


def probe(wanted: Sequence[Tuple[str, str, Optional[str]]],
          run=None) -> Dict[str, Dict[str, Any]]:
    '''Ask about each ``(name, kind, driver)``; ``run`` runs the script (default: here).

    🔴 One path for this host and for an image, so neither rots.
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
    '''``(captured, present)``: everything between each name's markers, and whether it was there.'''
    captured: Dict[str, str] = {}
    present: Dict[str, bool] = {}
    name: Optional[str] = None
    lines: List[str] = []

    for line in output.splitlines():
        # ⚠️ Escapes stripped first: klayout puts `\x1b[0m` before its closing marker.
        stripped = _ANSI.sub("", line).strip()
        if stripped.startswith(_BEGIN):
            name, lines = stripped[len(_BEGIN):], []
            present.setdefault(name, False)
        elif stripped.startswith(_HERE):
            if name is not None and stripped[len(_HERE):] == name:
                present[name] = True
        elif stripped.startswith(_END):
            if name is not None and stripped[len(_END):] == name:
                # 🔴 The trailing newline is kept, as a real run passes it:
                # bambu's parser takes `split('\n')[-3]`. Cut here too, for an
                # image with no `tail`.
                captured[name] = ("\n".join(lines) + "\n")[-ANSWER_BYTES:]
            name, lines = None, []
        elif name is not None:
            lines.append(line)

    return captured, present


def _ask_driver(name: str, driver: Optional[str], read):
    '''Hand the first Task in a driver module that builds and matches to ``read``.'''
    for task_cls in _drivers(name, driver):
        try:
            answer = _with_task(task_cls, name, read)
        except Exception as e:                                   # noqa: BLE001
            # Ordinary: an abstract base, or one whose make_docs needs more.
            logger.debug(f"{name}/{task_cls.__name__}: {e}")
            continue
        if answer:
            return answer
    return None


def _with_task(task_cls, name: str, read):
    '''Build one task the way the docs do, bind it, and read from it.

    🔴 `make_docs()` knows what each task needs around it; scaffolding here would
    drift. ⚠️ It returns an unbound task, so a node is re-entered to bind `exe`.
    '''
    from siliconcompiler.scheduler import SchedulerNode

    built = task_cls.make_docs()
    node = SchedulerNode(built._parent(root=True), "<step>", "<index>")

    with node.task.runtime(node) as task:
        if task.tool() != name:
            return None
        return read(task)


def _drivers(name: str, driver: Optional[str]) -> List[Any]:
    '''The Task classes in the registered driver module, never a search.'''
    from siliconcompiler import Task

    if not driver:
        return []

    try:
        module = importlib.import_module(driver)
    except Exception as e:                                       # noqa: BLE001
        logger.debug(f"{name}: could not import {driver}: {e}")
        return []

    # ⚠️ Walked: `__init__` usually holds only the abstract base.
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
        prog="python3 -m siliconcompiler.remote.server.software.probe",
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

    # 🔴 After argument checks, so a usage error is still shown. ⚠️ Process-wide.
    if not args.verbose:
        logging.disable(logging.CRITICAL)

    if args.script:
        sys.stdout.write(script(wanted))
        return 0

    sys.stdout.write(MARKER + json.dumps(probe(wanted)) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
