from typing import Union

from siliconcompiler.schema import BaseSchema
from siliconcompiler.schema import EditableSchema, Parameter, PerNode, Scope
from siliconcompiler.schema.utils import trim

from siliconcompiler import Project

from siliconcompiler.constraints import \
    ASICTimingConstraintSchema, ASICAreaConstraint, \
    ASICComponentConstraints, ASICPinConstraints
from siliconcompiler.metrics import ASICMetricsSchema

from siliconcompiler import PDKSchema
from siliconcompiler import StdCellLibrarySchema


class ASICProject(Project):
    """
    The ASICProject class extends the base Project class to provide
    specialized functionality and schema parameters for Application-Specific
    Integrated Circuit (ASIC) design flows.

    It includes specific constraints (timing, component, pin, area) and
    ASIC-related options such as PDK selection, main logic library,
    additional ASIC libraries, delay models, and routing layer limits.
    """

    def __init__(self):
        super().__init__()

        schema = EditableSchema(self)
        schema.insert("constraint", "timing", ASICTimingConstraintSchema())
        schema.insert("constraint", "component", ASICComponentConstraints())
        schema.insert("constraint", "pin", ASICPinConstraints())
        schema.insert("constraint", "area", ASICAreaConstraint())

        # Replace metrics with asic metrics
        schema.insert("metric", ASICMetricsSchema(), clobber=True)

        schema.insert(
            "asic", "pdk",
            Parameter(
                "str",
                scope=Scope.GLOBAL,
                shorthelp="ASIC: PDK target",
                example=["api: project.set('asic', 'pdk', 'freepdk45')"],
                help=trim("""Target PDK used during compilation.""")))
        schema.insert(
            "asic", "mainlib",
            Parameter(
                "str",
                scope=Scope.GLOBAL,
                shorthelp="ASIC: main logic library",
                example=["api: project.set('asic', 'mainlib', 'nangate45')"],
                help=trim("""Main logic library to use during the run""")))
        schema.insert(
            "asic", "asiclib",
            Parameter(
                "[str]",
                scope=Scope.GLOBAL,
                shorthelp="ASIC: logic libraries",
                example=["api: chip.set('asic', 'asiclib', 'nangate45')"],
                help=trim("""List of all selected logic libraries
                    to use for optimization for a given library architecture
                    (9T, 11T, etc).""")))
        schema.insert(
            "asic", "delaymodel",
            Parameter(
                "str",
                scope=Scope.GLOBAL,
                shorthelp="ASIC: delay model",
                example=["api: chip.set('asic', 'delaymodel', 'ccs')"],
                help=trim("""Delay model to use for the target libs. Commonly supported values
                    are nldm and ccs.""")))

        schema.insert(
            "asic", "minlayer",
            Parameter(
                "str",
                scope=Scope.GLOBAL,
                shorthelp="ASIC: Minimum routing layer",
                example=["api: project.set('asic', 'minlayer', 'M2')"],
                help=trim("""Minimum metal layer to be used for automated place and route""")))
        schema.insert(
            "asic", "maxlayer",
            Parameter(
                "str",
                scope=Scope.GLOBAL,
                shorthelp="ASIC: maximum routing layer",
                example=["api: project.set('asic', 'maxlayer', 'M7')"],
                help=trim("""Maximum metal layer to be used for automated place and route""")))

    @classmethod
    def _getdict_type(cls) -> str:
        """
        Returns the meta data for getdict, specifically the class name
        'ASICProject'.

        This method overrides the parent `Project._getdict_type` to ensure
        that when an `ASICProject` instance is serialized or deserialized,
        it is correctly identified as an `ASICProject` type.

        Returns:
            str: The name of the `ASICProject` class.
        """

        return ASICProject.__name__

    def add_dep(self, obj):
        """
        Adds a dependency object to the ASIC project, with specialized handling
        for PDK and standard cell libraries.

        This method extends the base `Project.add_dep` functionality. If the
        object is a `StdCellLibrarySchema` or `PDKSchema`, it is inserted
        into the project's library schema, potentially clobbering existing
        entries. For other dependency types, it defers to the parent class's
        `add_dep` method. It also ensures that internal dependencies are
        imported.

        Args:
            obj (Union[StdCellLibrarySchema, PDKSchema, DesignSchema, FlowgraphSchema,
                       LibrarySchema, ChecklistSchema, List, Set, Tuple]):
                The dependency object(s) to add.
        """
        if isinstance(obj, (list, set, tuple)):
            for iobj in obj:
                self.add_dep(iobj)
            return

        if isinstance(obj, StdCellLibrarySchema):
            if not self.has_library(obj.name):
                EditableSchema(self).insert("library", obj.name, obj, clobber=True)
        elif isinstance(obj, PDKSchema):
            if not self.has_library(obj.name):
                EditableSchema(self).insert("library", obj.name, obj, clobber=True)
        else:
            return super().add_dep(obj)

        self._import_dep(obj)

    def check_manifest(self) -> bool:
        """
        Performs a comprehensive check of the ASIC project's manifest
        for consistency and validity, extending the base Project checks.

        This method first calls the `Project.check_manifest` method.
        Then, it performs additional ASIC-specific validations:
        - Asserts that `[asic,pdk]` is set and refers to a loaded PDK library.
        - Checks if `[asic,mainlib]` is set and refers to a loaded library (warns if not set).
        - Asserts that `[asic,asiclib]` contains at least one library and all
          listed libraries are loaded.
        - Ensures that the `mainlib` is included in the `asiclib` list if both are set.
        - Asserts that `[asic,delaymodel]` is set.

        Returns:
            bool: True if the manifest is valid and all checks pass, False otherwise.
        """
        error = not super().check_manifest()

        pdk = self.get("asic", "pdk")
        if not pdk:
            # assert pdk is set
            self.logger.error("[asic,pdk] has not been set")
            error = True
        else:
            # Assert mainlib exists
            if pdk not in self.getkeys("library"):
                error = True
                self.logger.error(f"{pdk} library has not been loaded")
            elif not isinstance(self.get("library", pdk, field="schema"), PDKSchema):
                error = True
                self.logger.error(f"{pdk} must be a PDK")

        mainlib = self.get("asic", "mainlib")
        if not mainlib:
            # soft - assert mainlib is set
            self.logger.warning("[asic,mainlib] has not been set, this will be inferred")
        else:
            # Assert mainlib exists
            if mainlib not in self.getkeys("library"):
                error = True
                self.logger.error(f"{mainlib} library has not been loaded")

        # Assert asiclib is set
        if not self.get("asic", "asiclib"):
            error = True
            self.logger.error("[asic,asiclib] does not contain any libraries")

        # Assert asiclibs exist
        for lib in self.get("asic", "asiclib"):
            if lib not in self.getkeys("library"):
                error = True
                self.logger.error(f"{lib} library has not been loaded")

        # Assert mainlib in asiclib exist
        if mainlib and mainlib not in self.get("asic", "asiclib"):
            error = True
            self.logger.error(f"{mainlib} library must be added to [asic,asiclib]")

        # Assert asiclibs exist
        if not self.get("asic", "delaymodel"):
            error = True
            self.logger.error("[asic,delaymodel] has not been set")

        # Assert asic,pdk is set in libraries and all point the same pdk-ish
        # Assert stackups align in libraries

        return not error

    def set_mainlib(self, library: Union[StdCellLibrarySchema, str]):
        """
        Sets the main standard cell library for the ASIC project.

        This library is typically the primary logic library used during the ASIC flow.
        If a `StdCellLibrarySchema` object is provided, it is first added as a dependency.

        Args:
            library (Union[StdCellLibrarySchema, str]): The standard cell library object
                                                        or its name (string) to be set as the main
                                                        library.

        Returns:
            Any: The result of setting the parameter in the schema.

        Raises:
            TypeError: If the provided `library` is not a string or a `StdCellLibrarySchema` object.
        """
        if isinstance(library, StdCellLibrarySchema):
            self.add_dep(library)
            library = library.name
        elif not isinstance(library, str):
            raise TypeError("main library must be string or standard cell library object")

        return self.set("asic", "mainlib", library)

    def set_pdk(self, pdk: Union[PDKSchema, str]):
        """
        Sets the Process Design Kit (PDK) for the ASIC project.

        The PDK defines the technology-specific information required for ASIC compilation.
        If a `PDKSchema` object is provided, it is first added as a dependency.

        Args:
            pdk (Union[PDKSchema, str]): The PDK object or its name (string)
                                         to be set as the project's PDK.

        Returns:
            Any: The result of setting the parameter in the schema.

        Raises:
            TypeError: If the provided `pdk` is not a string or a `PDKSchema` object.
        """
        if isinstance(pdk, PDKSchema):
            self.add_dep(pdk)
            pdk = pdk.name
        elif not isinstance(pdk, str):
            raise TypeError("pdk must be string or PDK object")

        return self.set("asic", "pdk", pdk)

    def add_asiclib(self, library: Union[StdCellLibrarySchema, str], clobber: bool = False):
        """
        Adds one or more ASIC logic libraries to be used in the project.

        These libraries are typically used for optimization during the ASIC flow,
        complementing the main library.

        Args:
            library (Union[StdCellLibrarySchema, str]): The standard cell library object
                                                        or its name (string) to add.
            clobber (bool): If True, existing ASIC libraries will be replaced by the new ones.
                            If False, new libraries will be added to the existing list.
                            Defaults to False.

        Returns:
            Any: The result of adding the parameter to the schema.

        Raises:
            TypeError: If the provided `library` is not a string or a `StdCellLibrarySchema` object.
        """
        if isinstance(library, StdCellLibrarySchema):
            self.add_dep(library)
            library = library.name
        elif not isinstance(library, str):
            raise TypeError("asic library must be string or standard cell library object")

        if clobber:
            return self.set("asic", "asiclib", library)
        else:
            return self.add("asic", "asiclib", library)

    def set_asic_routinglayers(self, min: str = None, max: str = None):
        """
        Sets the minimum and/or maximum metal layers to be used for automated
        place and route in the ASIC flow.

        Args:
            min (str, optional): The name of the minimum metal layer (e.g., 'M2').
                                 Defaults to None.
            max (str, optional): The name of the maximum metal layer (e.g., 'M7').
                                 Defaults to None.
        """
        if min:
            self.set("asic", "minlayer", min)
        if max:
            self.set("asic", "maxlayer", max)

    def get_timingconstraints(self) -> ASICTimingConstraintSchema:
        """
        Retrieves the ASIC timing constraint schema for the project.

        Returns:
            ASICTimingConstraintSchema: The timing constraint schema object.
        """
        return self.get("constraint", "timing", field="schema")

    def get_pinconstraints(self) -> ASICPinConstraints:
        """
        Retrieves the ASIC pin constraint schema for the project.

        Returns:
            ASICPinConstraints: The pin constraint schema object.
        """
        return self.get("constraint", "pin", field="schema")

    def get_componentconstraints(self) -> ASICComponentConstraints:
        """
        Retrieves the ASIC component constraint schema for the project.

        Returns:
            ASICComponentConstraints: The component constraint schema object.
        """
        return self.get("constraint", "component", field="schema")

    def get_areaconstraints(self) -> ASICAreaConstraint:
        """
        Retrieves the ASIC area constraint schema for the project.

        Returns:
            ASICAreaConstraint: The area constraint schema object.
        """
        return self.get("constraint", "area", field="schema")

    def run(self, raise_exception=False):
        """
        Executes the ASIC compilation flow, with pre-run setup for ASIC-specific
        parameters, then defers to the base Project's run method.

        This method ensures that if `[asic,mainlib]` or `[asic,pdk]` are not
        explicitly set but can be inferred (e.g., from `asiclib` or the main
        library's PDK), they are automatically configured. It also verifies
        that the `mainlib` is included in the `asiclib` list. After these
        pre-run adjustments, it calls the `run` method of the parent `Project` class.

        Args:
            raise_exception (bool): If True, will rethrow errors that the flow raises,
                                    otherwise will report the error and return False.

        Returns:
            bool: True if the execution completes successfully, False otherwise.
        """
        # Ensure mainlib is set
        if not self.get("asic", "mainlib") and self.get("asic", "asiclib"):
            mainlib = self.get("asic", "asiclib")[0]
            self.logger.warning(f"Setting main library to: {mainlib}")
            self.set_mainlib(mainlib)

        if not self.get("asic", "pdk") and self.get("asic", "mainlib"):
            mainlib = None
            try:
                mainlib = self.get("library", self.get("asic", "mainlib"), field="schema")
            except KeyError:
                pass
            if mainlib:
                mainlib_pdk = mainlib.get("asic", "pdk")
                if mainlib_pdk:
                    # Infer from main library
                    self.logger.warning(f"Setting pdk to: {mainlib_pdk}")
                    self.set("asic", "pdk", mainlib_pdk)

        if self.get("asic", "mainlib") not in self.get("asic", "asiclib"):
            # Ensure mainlib is added to asiclib
            self.logger.warning(f'Adding {self.get("asic", "mainlib")} to [asic,asiclib]')
            self.add("asic", "asiclib", self.get("asic", "mainlib"))

        return super().run(raise_exception)

    def _summary_headers(self):
        """
        Generates a list of key-value pairs representing ASIC-specific headers
        to be included in the summary report.

        This method extends the base `Project._summary_headers` by adding
        information about the selected PDK, main logic library, and a list of
        all ASIC logic libraries used in the project.

        Returns:
            List[Tuple[str, str]]: A list of tuples, where each tuple contains
                                   a header name (str) and its corresponding value (str).
        """
        headers = super()._summary_headers()

        headers.append(("pdk", self.get("asic", "pdk")))
        headers.append(("mainlib", self.get("asic", "mainlib")))

        asiclib = self.get("asic", "asiclib")
        if len(asiclib) > 1:
            headers.append(("asiclib", ", ".join(asiclib)))

        return headers


class ASICSchema(BaseSchema):
    def __init__(self):
        super().__init__()

        schema_asic(self)

    @classmethod
    def _getdict_type(cls) -> str:
        """
        Returns the meta data for getdict
        """

        return ASICSchema.__name__


###############################################################################
# ASIC
###############################################################################
def schema_asic(schema):
    schema = EditableSchema(schema)

    schema.insert(
        'logiclib',
        Parameter(
            '[str]',
            scope=Scope.JOB,
            pernode=PerNode.OPTIONAL,
            shorthelp="ASIC: logic libraries",
            switch="-asic_logiclib <str>",
            example=["cli: -asic_logiclib nangate45",
                     "api: chip.set('asic', 'logiclib', 'nangate45')"],
            help=trim("""List of all selected logic libraries libraries
            to use for optimization for a given library architecture
            (9T, 11T, etc).""")))

    schema.insert(
        'macrolib',
        Parameter(
            '[str]',
            scope=Scope.JOB,
            pernode=PerNode.OPTIONAL,
            shorthelp="ASIC: macro libraries",
            switch="-asic_macrolib <str>",
            example=["cli: -asic_macrolib sram64x1024",
                     "api: chip.set('asic', 'macrolib', 'sram64x1024')"],
            help=trim("""
            List of macro libraries to be linked in during synthesis and place
            and route. Macro libraries are used for resolving instances but are
            not used as targets for logic synthesis.""")))

    schema.insert(
        'delaymodel',
        Parameter(
            'str',
            scope=Scope.JOB,
            pernode=PerNode.OPTIONAL,
            shorthelp="ASIC: delay model",
            switch="-asic_delaymodel <str>",
            example=["cli: -asic_delaymodel ccs",
                     "api: chip.set('asic', 'delaymodel', 'ccs')"],
            help=trim("""
            Delay model to use for the target libs. Commonly supported values
            are nldm and ccs.""")))

    # TODO: Expand on the exact definitions of these types of cells.
    # minimize typing
    names = ['decap',
             'tie',
             'hold',
             'clkbuf',
             'clkgate',
             'clklogic',
             'dontuse',
             'filler',
             'tap',
             'endcap',
             'antenna']

    for item in names:
        schema.insert(
            'cells', item,
            Parameter(
                '[str]',
                pernode=PerNode.OPTIONAL,
                shorthelp=f"ASIC: {item} cell list",
                switch=f"-asic_cells_{item} '<str>'",
                example=[
                    f"cli: -asic_cells_{item} '*eco*'",
                    f"api: chip.set('asic', 'cells', '{item}', '*eco*')"],
                help=trim("""
                List of cells grouped by a property that can be accessed
                directly by the designer and tools. The example below shows how
                all cells containing the string 'eco' could be marked as dont use
                for the tool.""")))

    schema.insert(
        'libarch',
        Parameter(
            'str',
            pernode=PerNode.OPTIONAL,
            shorthelp="ASIC: library architecture",
            switch="-asic_libarch '<str>'",
            example=[
                "cli: -asic_libarch '12track'",
                "api: chip.set('asic', 'libarch', '12track')"],
            help=trim("""
            The library architecture (e.g. library height) used to build the
            design. For example a PDK with support for 9 and 12 track libraries
            might have 'libarchs' called 9t and 12t.""")))

    libarch = 'default'
    schema.insert(
        'site', libarch,
        Parameter(
            '[str]',
            pernode=PerNode.OPTIONAL,
            shorthelp="ASIC: library sites",
            switch="-asic_site 'libarch <str>'",
            example=[
                "cli: -asic_site '12track Site_12T'",
                "api: chip.set('asic', 'site', '12track', 'Site_12T')"],
            help=trim("""
            Site names for a given library architecture.""")))
