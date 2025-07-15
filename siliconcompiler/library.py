from typing import final

from siliconcompiler.design import DesignSchema

from siliconcompiler.schema import EditableSchema, Parameter, Scope, PerNode
from siliconcompiler.schema.utils import trim


class LibrarySchema(DesignSchema):
    def __init__(self, name: str = None):
        super().__init__()
        self.set_name(name)

    @final
    def define_tool_parameter(self, tool: str, name: str, type: str, help: str, **kwargs):
        """
        Define a new tool parameter for the library

        Args:
            tool (str): name of the tool
            name (str): name of the parameter
            type (str): type of parameter, see :class:`.Parameter`.
            help (str): help information for this parameter
            kwargs: passthrough for :class:`.Parameter`.
        """
        if isinstance(help, str):
            # grab first line for short help
            help = trim(help)
            shorthelp = help.splitlines()[0].strip()
        else:
            raise TypeError("help must be a string")

        kwargs["scope"] = Scope.GLOBAL
        kwargs["pernode"] = PerNode.NEVER
        kwargs["shorthelp"] = shorthelp
        kwargs["help"] = help

        EditableSchema(self).insert(
            "tool", tool, name,
            Parameter(type, **kwargs)
        )
