'''
What is actually inside an image, asked rather than declared.

🔴 **The registry's one unverified claim was `image_contents`.** An operator
typed what an image held and nothing ever opened it to check, so a wrong row
meant a job ran in a container without what it asked for and failed at run time
rather than at submit. This is the other half: run inside the image and report
what is there.

**Two mechanisms, and the registry says which applies to which name:**

``python``  ``importlib.metadata.version(<name>)``
``tool``    the driver's ``exe`` and ``vswitch``, through its ``parse_version``

🔴 **Neither the kind nor the driver is guessed here.** Both are columns on
``software``, set when the name is registered. A guess would work for
SiliconCompiler's own in-tree drivers and quietly fail for everything else: a
driver can live in any package -- a site library ships its own and a
proprietary tool's never will be in this tree -- and the in-tree path is not
even reliable in-tree, where ``kepler-formal`` is driven from
``siliconcompiler.tools.keplerformal``. There is also nothing to guess FROM:
the process that registers an image is not the process inside it and does not
have its packages.

Run inside the image:

.. code-block:: bash

  python3 -m siliconcompiler.remote.server.probe \\
      -python siliconcompiler \\
      -tool openroad=siliconcompiler.tools.openroad \\
      -tool magic

and it prints one line of JSON behind :data:`MARKER`. The marker is there
because a container's output is not this process's alone -- a tool that writes
to stdout while being asked its version would otherwise be indistinguishable
from the answer.
'''

import argparse
import importlib
import importlib.metadata
import json
import logging
import pkgutil
import sys

from typing import Any, Dict, List, Optional, Sequence, Tuple

__all__ = ["KINDS", "MARKER", "probe", "python_version", "tool_version"]


# The closed set, and each half is a mechanism rather than a label.
KINDS = ("python", "tool")

# What a caller greps for. One line, JSON after it.
MARKER = "sc-probe:"

logger = logging.getLogger("sc-probe")


def python_version(name: str) -> Optional[str]:
    '''What ``importlib.metadata`` says, or None if it is not installed.'''
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None
    except Exception as e:                                       # noqa: BLE001
        logger.debug(f"{name}: importlib could not answer: {e}")
        return None


def tool_version(name: str,
                 driver: Optional[str] = None) -> Optional[Tuple[str, str]]:
    '''Run the tool's executable with its version switch, and parse the output.

    🔴 **`Task.get_exe_version` and not a command of this module's own.** The
    executable name, the switch and the parser are per tool and they live in
    the driver -- OpenROAD answers ``-version`` with four different shapes and
    its `parse_version` knows all of them. Anything here that re-implemented
    the call would be a second copy that drifts from the one a real run uses.

    ``driver`` is the module carrying it, as the registry recorded it. Without
    one there is nothing to run and the answer is None -- which is a real
    answer: it is what ``published_date`` exists to record.

    ⚠️ Every Task class in that module is tried, because the one that sets the
    executable is usually a base the concrete tasks inherit, and an abstract
    base cannot be built.

    Returns ``(comparable, reported)`` -- see `_ask` for why there are two.
    '''
    for task_cls in _drivers(name, driver):
        answer = _ask(task_cls, name)
        if answer:
            return answer
    return None


def probe(wanted: Sequence[Tuple[str, str, Optional[str]]]) -> Dict[str, Dict[str, Any]]:
    '''Ask about each ``(name, kind, driver)``. Returns name to kind and
    version.

    ``version`` is None where nothing reported one. Not an error: a tool this
    deployment lists and nobody drives has no version to read, and saying so is
    the point.
    '''
    found: Dict[str, Dict[str, Any]] = {}
    for name, kind, driver in wanted:
        if kind not in KINDS:
            raise ValueError(f"{kind} is not a software kind")
        if kind == "python":
            version = python_version(name)
            reported = version
        else:
            answer = tool_version(name, driver)
            version, reported = answer if answer else (None, None)

        found[name] = {"kind": kind, "version": version, "reported": reported}
    return found


######################################################################
# Reaching the driver
######################################################################

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
        # Not in this image, which is an ordinary answer for an image that does
        # not hold the tool.
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


def _ask(task_cls, name: str) -> Optional[str]:
    '''Build one task the way the docs build it, bind it, and ask its version.

    🔴 **`make_docs()` does the building, and that is the whole point of using
    it.** What a task needs around it is the task's own knowledge and it
    differs: an OpenROAD task needs an `ASIC` project with a real PDK target
    loaded, a builtin task needs a bare `Project`, and a dozen classes override
    `make_docs` to say so. Scaffolding built here would be a second answer to
    that question, right for the tasks somebody checked and silently wrong for
    the rest -- and it would go stale the first time a driver started needing
    something new.

    ⚠️ **One thing has to be added back: `make_docs` returns an UNBOUND task.**
    `exe` and `vswitch` are set per step and index -- that is what `setup()`
    does -- so `get_exe()` on the returned object reads nothing. The project it
    was built in is reachable as the schema's root, and re-entering a node on
    it is what binds the values `setup()` wrote.

    🔴 **The driver's `normalize_version` is applied, and that is not
    cosmetic.** OpenROAD reports `26Q3-2418-g3ab04b4dd1`, which is not a PEP
    440 version at all -- stored raw it can never satisfy a range, so
    `openroad>=26.3` would be refused against an image that plainly has it. Its
    driver knows how to turn that into `26.3.2418`, the same way its
    `parse_version` knows the four shapes the tool answers in. Where SC has a
    rule for a tool, that is the rule.

    Returns ``(comparable, reported)``: the normalised version, which is what
    gets stored and matched, and what the tool actually printed, which is what
    an operator should see in a log. `verilator` says `5.052` and PEP 440 makes
    that `5.52`; the catalogue needs the second and a person reading it is
    owed the first.
    '''
    from siliconcompiler.scheduler import SchedulerNode

    try:
        built = task_cls.make_docs()
        project = built._parent(root=True)

        node = SchedulerNode(project, "<step>", "<index>")
        with node.task.runtime(node) as task:
            if task.tool() != name:
                return None

            reported = task.get_exe_version()
            if not reported:
                return None

            try:
                return task.normalize_version(reported), reported
            except Exception as e:                               # noqa: BLE001
                # A normaliser that cannot read its own tool's output. The raw
                # string is still true and still selectable by name; what it
                # loses is being matchable against a range.
                logger.debug(f"{name}: could not normalize {reported}: {e}")
                return reported, reported
    except Exception as e:                                       # noqa: BLE001
        # Every one of these is ordinary: an abstract base, a class whose
        # make_docs needs something this image has not got, a tool that is not
        # installed here. The next class is tried, and a name that answers
        # nowhere reports no version.
        logger.debug(f"{name}/{task_cls.__name__}: {e}")
        return None


######################################################################
# Running it inside an image
######################################################################

def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python3 -m siliconcompiler.remote.server.probe",
        description="What is in this image: one JSON line, behind a marker.")
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

    # 🔴 After the arguments are checked, and off by default. A version check
    # runs the tool, and a tool that prints its banner to stdout would
    # otherwise be mixed into the answer -- which is what the marker exists
    # for, and quieting the noise is cheaper than relying on it.
    #
    # ⚠️ It is process-wide and nothing puts it back, which is right for a
    # process whose whole job is this and wrong for anything else: a usage
    # error that had already quieted the logs would take the message about
    # itself with it.
    if not args.verbose:
        logging.disable(logging.CRITICAL)

    sys.stdout.write(MARKER + json.dumps(probe(wanted)) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
