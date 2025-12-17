from typing import Union, List, Tuple, Optional

from siliconcompiler.schema import NamedSchema, EditableSchema, Parameter, \
    PerNode, Scope
from siliconcompiler import Design


class TimingModeSchema(NamedSchema):
    """
    Represents a single timing mode for design constraints.

    This class encapsulates the SDC filesets used for a specific timing mode.
    """

    def __init__(self, name: Optional[str] = None):
        super().__init__()
        self.set_name(name)

        schema = EditableSchema(self)
        schema.insert(
            'sdcfileset',
            Parameter(
                '[(str,str)]',
                pernode=PerNode.OPTIONAL,
                scope=Scope.GLOBAL,
                shorthelp="Constraint: SDC files",
                switch="-constraint_timing_file 'scenario <file>'",
                example=["api: mode.set('constraint', 'timing', 'worst', 'file', 'hello.sdc')"],
                help="""List of timing constraint sets files to use for the scenario. The
                values are combined with any constraints specified by the design
                'constraint' parameter. If no constraints are found, a default
                constraint file is used based on the clock definitions."""))

    def add_sdcfileset(self,
                       design: Union[Design, str],
                       fileset: str,
                       clobber: bool = False,
                       step: Optional[str] = None, index: Optional[Union[str, int]] = None):
        """
        Adds an SDC fileset for a given design.

        Args:
            design (:class:`Design` or str): The design object or the name of the design to
                associate the fileset with.
            fileset (str): The name of the SDC fileset to add.
            clobber (bool): If True, existing SDC filesets for the design at the specified
                    step/index will be overwritten.
                    If False (default), the SDC fileset will be added.
            step (str, optional): step name.
            index (str, optional): index name.

        Raises:
            TypeError: If `design` is not a Design object or a string, or if `fileset` is not
                a string.
        """
        if isinstance(design, Design):
            design = design.name

        if not isinstance(design, str):
            raise TypeError("design must be a design object or string")

        if not isinstance(fileset, str):
            raise TypeError("fileset must be a string")

        if clobber:
            return self.set("sdcfileset", (design, fileset), step=step, index=index)
        else:
            return self.add("sdcfileset", (design, fileset), step=step, index=index)

    def get_sdcfileset(self, step: Optional[str] = None, index: Optional[Union[str, int]] = None) \
            -> List[Tuple[str, str]]:
        """
        Gets the list of SDC filesets.

        Args:
            step (str, optional): step name.
            index (str, optional): index name.

        Returns:
            A list of tuples, where each tuple contains the design name and the SDC fileset name.
        """
        return self.get("sdcfileset", step=step, index=index)
