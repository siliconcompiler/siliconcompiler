from typing import List, Tuple, Optional, Union
from siliconcompiler import Task


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
