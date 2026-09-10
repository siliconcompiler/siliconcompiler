import os

from typing import Dict, List, Tuple, Optional, Union
from siliconcompiler import Task


def distinct(values: List[str]) -> List[str]:
    """Return ``values`` with duplicates removed, preserving first-seen order.

    Frontend command lines are assembled by iterating over every selected
    fileset, so the same include directory, define, or source file can be
    contributed more than once (e.g. by a library shared between filesets).
    Passing duplicates to a tool is at best wasteful and at worst an error, so
    the collected lists are run through this helper before being emitted.
    """
    return list(dict.fromkeys(values))


class CCache(Task):
    '''Mixin task for tools that drive ccache, pointing it at the tool cache.

    Verilator's ``verilated.mk`` sets ``OBJCACHE ?= ccache`` and invokes it
    unconditionally, so every C++ build it drives shells out to ccache whether or
    not anyone asked for it -- including the ones a tool starts on its own
    behalf, the way bambu does when it simulates. Left to itself ccache writes to
    ``~/.cache/ccache``: outside :keypath:`option,cachedir`, so nothing
    SiliconCompiler manages ever sees it, and not among the volumes mounted into
    a task container, so a containerised build starts from a cold cache every
    single time. :attr:`.Task.cachedir` is inside the mounted cache directory and
    is shared across designs, which is the whole point of a compiler cache.
    ccache creates the directory itself and enforces its own size cap, so there
    is nothing to set up and nothing to collect.

    Intended to be used via multiple inheritance alongside a concrete task class,
    and listed *first*: the check below reads the environment the rest of the
    chain assembled, so it has to run last.
    '''

    def get_runtime_environmental_variables(self, include_path: bool = True) \
            -> Dict[str, str]:
        envvars = super().get_runtime_environmental_variables(include_path=include_path)

        # Anyone who has already said where their ccache goes keeps it, whether
        # that is [option,env] / the task's own env or the ambient environment.
        # An empty value is not one of those: it names no directory, so ccache
        # falls back to its own default, which is the outcome this exists to
        # avoid. Neither is a value equal to the one this would set -- the node
        # exports these variables into its own environment before asking again,
        # to write the replay script, so testing for mere presence would by then
        # be answering about this method's own previous return and the replay
        # script would go out without it.
        toolcache = self.cachedir
        preset = envvars.get("CCACHE_DIR", os.environ.get("CCACHE_DIR"))
        if not preset or preset == toolcache:
            envvars["CCACHE_DIR"] = toolcache

        return envvars


class PlusArgs(Task):
    '''Mixin task for tools that support Verilog-style plusargs.

    Provides a ``plusargs`` parameter and convenience methods for
    setting, adding, and retrieving plusarg values. Each plusarg is
    a ``(name, value)`` tuple that maps to ``+name=value`` on the
    tool command line.

    Intended to be used via multiple inheritance alongside a concrete
    task class that defines :meth:`tool` and :meth:`task`.
    '''

    def __init__(self):
        super().__init__()

        self.add_parameter("plusargs", "[(str,str)]",
                           'List of plusarg (name, value) tuples to pass to '
                           'the tool.')

    def add_plusarg(
        self, name: str, value: str,
        step: Optional[str] = None,
        index: Optional[Union[str, int]] = None,
        clobber: bool = False
    ):
        """
        Appends a single plusarg to the existing list.

        Args:
            name (str): The plusarg name.
            value (str): The plusarg value.
            step (str, optional): The specific step to apply this configuration to.
            index (str or int, optional): The specific index to apply this
                configuration to.
            clobber (bool, optional): If True, replaces the current value.
                Defaults to False.
        """
        if clobber:
            self.set("var", "plusargs", (name, value), step=step, index=index)
        else:
            self.add("var", "plusargs", (name, value), step=step, index=index)

    def get_plusargs(
        self,
        step: Optional[str] = None,
        index: Optional[Union[str, int]] = None
    ) -> List[Tuple[str, str]]:
        """
        Returns the current list of plusargs.

        Args:
            step (str, optional): The specific step to retrieve configuration from.
            index (str or int, optional): The specific index to retrieve
                configuration from.

        Returns:
            list: List of (name, value) plusarg tuples.
        """
        return self.get("var", "plusargs", step=step, index=index)

    def setup(self):
        super().setup()

        if self.get("var", "plusargs"):
            self.add_required_key("var", "plusargs")
