from typing import List, Tuple, Optional, Union
from siliconcompiler import Task


class PlusArgs(Task):
    '''Mixin task for tools that support Verilog-style plusargs.

    Provides a ``plusargs`` parameter and convenience methods for
    setting, adding, and retrieving plusarg values. Each plusarg is
    a ``(name, value)`` tuple that maps to ``+name+value`` on the
    tool command line.

    Intended to be used via multiple inheritance alongside a concrete
    task class that defines :meth:`tool` and :meth:`task`.
    '''

    def __init__(self):
        super().__init__()

        self.add_parameter("plusargs", "[(str,str)]",
                           'List of plusarg (name, value) tuples to pass to '
                           'the tool.')

    def set_plusargs(
        self, plusargs: List[Tuple[str, str]],
        step: Optional[str] = None,
        index: Optional[Union[str, int]] = None
    ):
        """
        Sets the plusargs list, replacing any existing values.

        Args:
            plusargs: List of (name, value) plusarg tuples.
            step (str, optional): The specific step to apply this configuration to.
            index (str or int, optional): The specific index to apply this
                configuration to.
        """
        self.set("var", "plusargs", plusargs, step=step, index=index)

    def add_plusargs(
        self, plusarg: Tuple[str, str],
        step: Optional[str] = None,
        index: Optional[Union[str, int]] = None
    ):
        """
        Appends a single plusarg to the existing list.

        Args:
            plusarg: A (name, value) plusarg tuple.
            step (str, optional): The specific step to apply this configuration to.
            index (str or int, optional): The specific index to apply this
                configuration to.
        """
        self.add("var", "plusargs", plusarg, step=step, index=index)

    def get_plusargs(self) -> List[Tuple[str, str]]:
        """
        Returns the current list of plusargs.

        Returns:
            list: List of (name, value) plusarg tuples.
        """
        return self.get("var", "plusargs")

    def setup(self):
        super().setup()

        if self.get("var", "plusargs"):
            self.add_required_key("var", "plusargs")
