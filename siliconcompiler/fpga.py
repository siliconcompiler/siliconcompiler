"""
Schema definitions for FPGA-related configurations in SiliconCompiler.

This module defines classes and functions for managing FPGA-specific
parameters, such as part names, LUT sizes, and vendor information,
within the SiliconCompiler schema. It includes schemas for both
tool-library and temporary configurations.
"""

from siliconcompiler import Project

from siliconcompiler.schema import EditableSchema, Parameter, Scope
from siliconcompiler.schema.utils import trim

from siliconcompiler.library import ToolLibrarySchema

from siliconcompiler.constraints import \
    FPGATimingConstraintSchema, FPGAComponentConstraints, FPGAPinConstraints
from siliconcompiler.metrics import FPGAMetricsSchema


class FPGA(ToolLibrarySchema):
    """
    A schema for configuring FPGA-related parameters.

    This class extends ToolLibrarySchema to provide a structured way
    to define and access FPGA-specific settings like part name and LUT size.
    """
    def __init__(self, name: str = None):
        """
        Initializes the FPGA.

        Args:
            name (str, optional): The name of the schema. Defaults to None.
        """
        super().__init__()
        self.set_name(name)

        schema = EditableSchema(self)
        schema.insert(
            "fpga", 'partname',
            Parameter(
                'str',
                scope=Scope.GLOBAL,
                shorthelp="FPGA: part name",
                switch="-fpga_partname <str>",
                example=["cli: -fpga_partname fpga64k",
                         "api: fpga.set('fpga', 'partname', 'fpga64k')"],
                help=trim("""
                Complete part name used as a device target by the FPGA compilation
                tool. The part name must be an exact string match to the partname
                hard coded within the FPGA EDA tool.""")))

        schema.insert(
            "fpga", 'lutsize',
            Parameter(
                'int',
                scope=Scope.GLOBAL,
                shorthelp="FPGA: lutsize",
                switch="-fpga_lutsize 'partname <int>'",
                example=["cli: -fpga_lutsize 'fpga64k 4'",
                         "api: fpga.set('fpga', 'fpga64k', 'lutsize', '4')"],
                help=trim("""
                Specify the number of inputs in each lookup table (LUT) for the
                FPGA partname.  For architectures with fracturable LUTs, this is
                the number of inputs of the unfractured LUT.""")))

    def set_partname(self, name: str):
        """
        Sets the FPGA part name.

        Args:
            name (str): The name of the FPGA part.

        Returns:
            Any: The result of the `set` operation.
        """
        return self.set("fpga", "partname", name)

    def set_lutsize(self, lut: int):
        """
        Sets the LUT size for the FPGA.

        Args:
            lut (int): The number of inputs for the lookup table.

        Returns:
            Any: The result of the `set` operation.
        """
        return self.set("fpga", "lutsize", lut)

    @classmethod
    def _getdict_type(cls) -> str:
        """
        Returns the meta data for getdict.

        Returns:
            str: The name of the class.
        """

        return FPGA.__name__


class FPGAProject(Project):
    """
    A class for managing FPGA projects, inheriting from the base Project class.

    This class extends the base project with FPGA-specific schema for constraints,
    metrics, and device selection. It provides methods to configure and validate

    an FPGA design project.
    """

    def __init__(self, design=None):
        """
        Initialize an FPGAProject with FPGA-specific schemas and parameters.

        Creates the base Project, inserts an FPGAConstraint container at "constraint",
        adds FPGA metrics under "metric" (clobber allowed), and registers the
        string parameter :keypath:`FPGAProject,fpga,device` for selecting the target FPGA device.

        Parameters:
            design (optional): Optional project design data passed to the base Project.
        """
        super().__init__(design)

        schema = EditableSchema(self)
        schema.insert("constraint", "timing", FPGATimingConstraintSchema())
        schema.insert("constraint", "component", FPGAComponentConstraints())
        schema.insert("constraint", "pin", FPGAPinConstraints())

        schema.insert("metric", FPGAMetricsSchema(), clobber=True)

        schema.insert("fpga", "device", Parameter("str"))

    @classmethod
    def _getdict_type(cls):
        return FPGAProject.__name__

    def add_dep(self, obj):
        """
        Adds a dependency to the project.

        If the dependency is an FPGA object, it is registered as a library.
        Otherwise, the request is passed to the parent class's implementation.

        Args:
            obj: The dependency object to add. Can be an FPGA instance
                 or another type supported by the base Project class.
        """
        if isinstance(obj, (list, set, tuple)):
            for iobj in obj:
                self.add_dep(iobj)
            return

        if isinstance(obj, FPGA):
            EditableSchema(self).insert("library", obj.name, obj, clobber=True)
        else:
            return super().add_dep(obj)

        self._import_dep(obj)

    def set_fpga(self, fpga):
        """
        Sets the target FPGA device for the project.

        This method can accept either an FPGA object or a string
        representing the name of the FPGA device. If an object is provided,
        it is first added as a dependency.

        Args:
            fpga (FPGA or str): The FPGA device to target.

        Raises:
            TypeError: If the provided fpga is not an FPGA object or a string.
        """
        if isinstance(fpga, FPGA):
            self.add_dep(fpga)
            fpga = fpga.name
        elif not isinstance(fpga, str):
            raise TypeError("fpga must be an FPGA object or a string.")

        return self.set("fpga", "device", fpga)

    def check_manifest(self):
        """
        Validate the project manifest for FPGA configuration and library availability.

        Runs the base project manifest checks, verifies that the :keypath:`FPGAProject,fpga,device`
        parameter is set, and confirms the corresponding FPGA library has been
        loaded into the project.

        Returns:
            bool: `True` if the manifest is valid, `False` otherwise.
        """
        error = not super().check_manifest()

        if not self.get("fpga", "device"):
            self.logger.error("[fpga,device] has not been set.")
            error = True
        else:
            fpga_device = self.get("fpga", "device")
            if not self._has_library(fpga_device):
                self.logger.error(f"FPGA library '{fpga_device}' has not been loaded.")
                error = True

        return not error

    def get_timingconstraints(self) -> FPGATimingConstraintSchema:
        """
        Retrieves the FPGA timing constraint schema for the project.

        Returns:
            FPGATimingConstraintSchema: The timing constraint schema object.
        """
        return self.get("constraint", "timing", field="schema")

    def get_pinconstraints(self) -> FPGAPinConstraints:
        """
        Retrieves the FPGA pin constraint schema for the project.

        Returns:
            FPGAPinConstraints: The pin constraint schema object.
        """
        return self.get("constraint", "pin", field="schema")

    def get_componentconstraints(self) -> FPGAComponentConstraints:
        """
        Retrieves the FPGA component constraint schema for the project.

        Returns:
            FPGAComponentConstraints: The component constraint schema object.
        """
        return self.get("constraint", "component", field="schema")

    def _summary_headers(self):
        """
        Generates headers for the project summary.

        This internal method extends the base summary headers by appending
        the name of the target FPGA device.

        Returns:
            list: A list of tuples representing the summary headers.
        """
        headers = super()._summary_headers()
        headers.append(("fpga", self.get("fpga", "device")))
        return headers
