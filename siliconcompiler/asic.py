import json
import re

from typing import Union, Tuple

from siliconcompiler.schema import EditableSchema, Parameter, Scope, BaseSchema
from siliconcompiler.schema.utils import trim

from siliconcompiler import Project, sc_open
from siliconcompiler import Task

from siliconcompiler.constraints import \
    ASICTimingConstraintSchema, ASICAreaConstraint, \
    ASICComponentConstraints, ASICPinConstraints
from siliconcompiler.metrics import ASICMetricsSchema
from siliconcompiler.flowgraph import RuntimeFlowgraph
from siliconcompiler.utils import units

from siliconcompiler import PDK
from siliconcompiler import StdCellLibrary


class ASICConstraint(BaseSchema):
    """A container for ASIC (Application-Specific Integrated Circuit) design constraints.

    This class aggregates various types of constraints necessary for the physical
    design flow, such as timing, component placement, pin assignments, and
    floorplan area.
    """
    def __init__(self):
        """Initializes the ASICConstraint schema."""
        super().__init__()

        schema = EditableSchema(self)
        schema.insert("timing", ASICTimingConstraintSchema())
        schema.insert("component", ASICComponentConstraints())
        schema.insert("pin", ASICPinConstraints())
        schema.insert("area", ASICAreaConstraint())

    @property
    def timing(self) -> ASICTimingConstraintSchema:
        """Provides access to the timing constraints.

        Returns:
            ASICTimingConstraintSchema: The schema object for timing constraints.
        """
        return self.get("timing", field="schema")

    @property
    def component(self) -> ASICComponentConstraints:
        """Provides access to the component placement constraints.

        Returns:
            ASICComponentConstraints: The schema object for component constraints.
        """
        return self.get("component", field="schema")

    @property
    def pin(self) -> ASICPinConstraints:
        """Provides access to pin assignment constraints.

        Returns:
            ASICPinConstraints: The schema object for pin constraints.
        """
        return self.get("pin", field="schema")

    @property
    def area(self) -> ASICAreaConstraint:
        """Provides access to the floorplan/area constraints.

        Returns:
            ASICAreaConstraint: The schema object for area constraints.
        """
        return self.get("area", field="schema")


class ASIC(Project):
    """
    The ASIC class extends the base Project class to provide
    specialized functionality and schema parameters for Application-Specific
    Integrated Circuit (ASIC) design flows.

    It includes specific constraints (timing, component, pin, area) and
    ASIC-related options such as PDK selection, main logic library,
    additional ASIC libraries, delay models, and routing layer limits.
    """

    def __init__(self, design=None):
        """
        Initialize an ASIC and register ASIC-specific schemas, metrics, and
        global ASIC parameters.

        This constructor sets up an EditableSchema for the project that:
        - Adds an aggregated `constraint` schema for timing, component, pin, and area constraints.
        - Replaces the default `metric` schema with ASIC-specific metrics.
        - Registers global ASIC parameters: `pdk`, `mainlib`, `asiclib`, `delaymodel`, `minlayer`,
            and `maxlayer`.

        Parameters:
            design (optional): Initial design context passed to the base Project initializer;
                               may be a design object or identifier used by Project.
        """
        super().__init__(design)

        schema = EditableSchema(self)
        schema.insert("constraint", ASICConstraint())

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
                "{str}",
                scope=Scope.GLOBAL,
                shorthelp="ASIC: logic libraries",
                example=["api: asic.set('asic', 'asiclib', 'nangate45')"],
                help=trim("""List of all selected logic libraries
                    to use for optimization for a given library architecture
                    (9T, 11T, etc).""")))
        schema.insert(
            "asic", "delaymodel",
            Parameter(
                "str",
                scope=Scope.GLOBAL,
                shorthelp="ASIC: delay model",
                example=["api: asic.set('asic', 'delaymodel', 'ccs')"],
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
        'ASIC'.

        This method overrides the parent `Project._getdict_type` to ensure
        that when an `ASIC` instance is serialized or deserialized,
        it is correctly identified as an `ASIC` type.

        Returns:
            str: The name of the `ASIC` class.
        """

        return ASIC.__name__

    def add_dep(self, obj):
        """
        Adds a dependency object to the ASIC project, with specialized handling
        for PDK and standard cell libraries.

        This method extends the base `Project.add_dep` functionality. If the
        object is a `StdCellLibrary` or `PDK`, it is inserted
        into the project's library schema, potentially clobbering existing
        entries. For other dependency types, it defers to the parent class's
        `add_dep` method. It also ensures that internal dependencies are
        imported.

        Args:
            obj (Union[
                StdCellLibrary, PDK, Design, Flowgraph,
                LibrarySchema, Checklist, List, Set, Tuple
            ]):
                The dependency object(s) to add.
        """
        if isinstance(obj, (list, set, tuple)):
            for iobj in obj:
                self.add_dep(iobj)
            return

        if isinstance(obj, StdCellLibrary):
            if not self._has_library(obj.name):
                EditableSchema(self).insert("library", obj.name, obj)
        elif isinstance(obj, PDK):
            if not self._has_library(obj.name):
                EditableSchema(self).insert("library", obj.name, obj)
        else:
            return super().add_dep(obj)

        self._import_dep(obj)

    def check_manifest(self) -> bool:
        """
        Performs a comprehensive check of the ASIC project's manifest
        for consistency and validity, extending the base Project checks.

        This method first calls the :meth:`.Project.check_manifest()` method.
        Then, it performs additional ASIC-specific validations:

            - Asserts that :keypath:`ASIC,asic,pdk` is set and refers to a
              loaded PDK library.
            - Checks if :keypath:`ASIC,asic,mainlib` is set and refers to a loaded
              library (warns if not set).
            - Asserts that :keypath:`ASIC,asic,asiclib` contains at least one library
              and all listed libraries are loaded.
            - Ensures that the `mainlib` is included in the `asiclib` list if both are set.
            - Asserts that :keypath:`ASIC,asic,delaymodel` is set.

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
            elif not isinstance(self.get("library", pdk, field="schema"), PDK):
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

    def set_mainlib(self, library: Union[StdCellLibrary, str]):
        """
        Sets the main standard cell library for the ASIC project.

        This library is typically the primary logic library used during the ASIC flow.
        If a `StdCellLibrary` object is provided, it is first added as a dependency.

        Args:
            library (Union[StdCellLibrary, str]): The standard cell library object
                                                        or its name (string) to be set as the main
                                                        library.

        Returns:
            Any: The result of setting the parameter in the schema.

        Raises:
            TypeError: If the provided `library` is not a string or a `StdCellLibrary` object.
        """
        if isinstance(library, StdCellLibrary):
            self.add_dep(library)
            library = library.name
        elif not isinstance(library, str):
            raise TypeError("main library must be string or standard cell library object")

        return self.set("asic", "mainlib", library)

    def set_pdk(self, pdk: Union[PDK, str]):
        """
        Sets the Process Design Kit (PDK) for the ASIC project.

        The PDK defines the technology-specific information required for ASIC compilation.
        If a `PDK` object is provided, it is first added as a dependency.

        Args:
            pdk (Union[PDK, str]): The PDK object or its name (string)
                                         to be set as the project's PDK.

        Returns:
            Any: The result of setting the parameter in the schema.

        Raises:
            TypeError: If the provided `pdk` is not a string or a `PDK` object.
        """
        if isinstance(pdk, PDK):
            self.add_dep(pdk)
            pdk = pdk.name
        elif not isinstance(pdk, str):
            raise TypeError("pdk must be string or PDK object")

        return self.set("asic", "pdk", pdk)

    def add_asiclib(self, library: Union[StdCellLibrary, str], clobber: bool = False):
        """
        Adds one or more ASIC logic libraries to be used in the project.

        These libraries are typically used for optimization during the ASIC flow,
        complementing the main library.

        Args:
            library (Union[StdCellLibrary, str]): The standard cell library object
                                                        or its name (string) to add.
            clobber (bool): If True, existing ASIC libraries will be replaced by the new ones.
                            If False, new libraries will be added to the existing list.
                            Defaults to False.

        Returns:
            Any: The result of adding the parameter to the schema.

        Raises:
            TypeError: If the provided `library` is not a string or a `StdCellLibrary` object.
        """
        if isinstance(library, (list, set, tuple)):
            if clobber:
                self.unset("asic", "asiclib")

            ret = []
            for lib in library:
                ret.append(self.add_asiclib(lib))
            return ret

        if isinstance(library, StdCellLibrary):
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

    def set_asic_delaymodel(self, model: str):
        """
        Set the timing delay model used for ASIC timing analysis.

        Parameters:
            model (str): Delay model name (e.g., "nldm", "ccs").
        """
        self.set("asic", "delaymodel", model)

    @property
    def constraint(self) -> ASICConstraint:
        """Provides access to the project's ASIC design constraints.

        Returns:
            ASICConstraint: The schema object containing all design constraints.
        """
        return self.get("constraint", field="schema")

    def _init_run(self):
        """
        Infer and ensure ASIC project main library and PDK are configured, and make sure the
        main library is listed in `asiclib`.

        If :keypath:`ASIC,asic,mainlib` is unset but :keypath:`ASIC,asic,asiclib`
        contains entries, sets `mainlib` from the first `asiclib` entry.
        If :keypath:`ASIC,asic,pdk` is unset but the resolved main library declares a PDK,
        sets :keypath:`ASIC,asic,pdk` from that declaration.
        Ensures the value of :keypath:`ASIC,asic,mainlib` is present in
        :keypath:`ASIC,asic,asiclib` and adds it if missing.
        """
        super()._init_run()

        # Ensure mainlib is set
        if not self.get("asic", "mainlib") and self.get("asic", "asiclib"):
            mainlib = self.get("asic", "asiclib")[0]
            self.logger.warning(f"Setting main library to: {mainlib}")
            self.set_mainlib(mainlib)

        if not self.get("asic", "pdk") and self.get("asic", "mainlib"):
            mainlib = None
            if self._has_library(self.get("asic", "mainlib")):
                mainlib = self.get("library", self.get("asic", "mainlib"), field="schema")
            if mainlib:
                mainlib_pdk = mainlib.get("asic", "pdk")
                if mainlib_pdk:
                    # Infer from main library
                    self.logger.warning(f"Setting pdk to: {mainlib_pdk}")
                    self.set("asic", "pdk", mainlib_pdk)

        if self.get("asic", "mainlib") not in self.get("asic", "asiclib"):
            # Ensure mainlib is added to asiclib
            self.logger.warning(f'Adding {self.get("asic", "mainlib")} to [asic,asiclib]')
            asiclibs = [self.get("asic", "mainlib"), *self.get("asic", "asiclib")]
            self.set("asic", "asiclib", asiclibs)

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

    def _snapshot_info(self):
        info = super()._snapshot_info()

        if self.get("asic", "pdk"):
            info.append(("PDK", self.get("asic", "pdk")))

        # get search ordering
        flow_name = self.get("option", 'flow')
        flow = self.get("flowgraph", flow_name, field="schema")
        to_steps = self.get('option', 'to')
        prune_nodes = self.get('option', 'prune')
        run_nodes = RuntimeFlowgraph(flow, to_steps=to_steps, prune_nodes=prune_nodes).get_nodes()
        nodes = []
        for node_group in flow.get_execution_order(reverse=True):
            for node in node_group:
                if node in run_nodes:
                    nodes.append(node)

        def format_area(value, unit):
            prefix = units.get_si_prefix(unit)
            mm_area = units.convert(value, from_unit=prefix, to_unit='mm^2')
            if mm_area < 10:
                return units.format_si(value, 'um') + 'um^2'
            else:
                return units.format_si(mm_area, 'mm') + 'mm^2'

        def format_freq(value, unit):
            value = units.convert(value, from_unit=unit)
            return units.format_si(value, 'Hz') + 'Hz'

        for text, metric, formatter in (
                ("Area", "totalarea", format_area),
                ("Fmax", "fmax", format_freq)):
            for step, index in nodes:
                value = self.get("metric", metric, step=step, index=index)
                if value is None:
                    continue
                if formatter:
                    value = formatter(value, self.get("metric", metric, field="unit"))
                else:
                    value = str(value)
                info.append((text, value))
                break

        return info


class ASICTask(Task):
    """
    A Task with helper methods for tasks in a standard ASIC flow,
    providing easy access to PDK and standard cell library information.
    """
    @property
    def mainlib(self) -> StdCellLibrary:
        """The main standard cell library schema object."""
        mainlib = self.project.get("asic", "mainlib")
        if not mainlib:
            raise ValueError("mainlib has not been defined in [asic,mainlib]")
        if mainlib not in self.project.getkeys("library"):
            raise LookupError(f"{mainlib} has not been loaded")
        return self.project.get("library", mainlib, field="schema")

    @property
    def pdk(self) -> PDK:
        """The Process Design Kit (PDK) schema object."""
        pdk = self.project.get("asic", "pdk")
        if not pdk:
            raise ValueError("pdk has not been defined in [asic,pdk]")
        if pdk not in self.project.getkeys("library"):
            raise LookupError(f"{pdk} has not been loaded")
        return self.project.get("library", pdk, field="schema")

    def set_asic_var(self,
                     key: str,
                     defvalue=None,
                     check_pdk: bool = True,
                     require_pdk: bool = False,
                     pdk_key: str = None,
                     check_mainlib: bool = True,
                     require_mainlib: bool = False,
                     mainlib_key: str = None,
                     require: bool = False):
        '''
        Set an ASIC parameter based on a prioritized lookup order.

        This method attempts to set a parameter identified by `key` by checking
        values in a specific order:
        1. The main library
        2. The PDK
        3. A provided default value (`defvalue`)

        The first non-empty or non-None value found in this hierarchy will be
        used to set the parameter. If no value is found and `defvalue` is not
        provided, the parameter will not be set unless explicitly required.

        Args:
            key: The string key for the parameter to be set. This key is used
                to identify the parameter within the current object (`self`)
                and, by default, within the main library and PDK.
            defvalue: An optional default value to use if the parameter is not
                found in the main library or PDK. If `None` and the parameter
                is not found, it will not be set unless `require` is True.
            check_pdk: If `True`, the method will attempt to retrieve the
                parameter from the PDK. Defaults to `True`.
            require_pdk: If `True`, the parameter *must* be defined in the PDK.
                An error will be raised if it's not found and `check_pdk` is `True`.
                Defaults to `False`.
            pdk_key: The specific key to use when looking up the parameter in the
                PDK. If `None`, `key` will be used.
            check_mainlib: If `True`, the method will attempt to retrieve the
                parameter from the main library. Defaults to `True`.
            require_mainlib: If `True`, the parameter *must* be defined in the
                main library. An error will be raised if it's not found and
                `check_mainlib` is `True`. Defaults to `False`.
            mainlib_key: The specific key to use when looking up the parameter in
                the main library. If `None`, `key` will be used.
            require: If `True`, the parameter *must* be set by this method (either
                from a source or `defvalue`). An error will be raised if it cannot
                be set. Defaults to `False`.
        '''
        check_keys = []
        if check_pdk:
            if not pdk_key:
                pdk_key = key
            if self.pdk.valid("tool", self.tool(), pdk_key):
                check_keys.append((self.pdk, ("tool", self.tool(), pdk_key)))
        if check_mainlib:
            if not mainlib_key:
                mainlib_key = key
            if self.mainlib.valid("tool", self.tool(), mainlib_key):
                check_keys.append((self.mainlib, ("tool", self.tool(), mainlib_key)))
        check_keys.append((self, ("var", key)))

        if require_pdk:
            self.add_required_key(self.pdk, "tool", self.tool(), pdk_key)
        if require_mainlib:
            self.add_required_key(self.mainlib, "tool", self.tool(), mainlib_key)
        if require or defvalue is not None:
            self.add_required_key(self, "var", key)

        if self.get("var", key, field=None).is_set(self.step, self.index):
            return

        for obj, keypath in reversed(check_keys):
            if not obj.valid(*keypath):
                continue

            value = obj.get(*keypath)
            if isinstance(value, (list, set, tuple)):
                if not value:
                    continue
            else:
                if value is None:
                    continue
            self.add_required_key(obj, *keypath)
            self.add_required_key(self, "var", key)
            return self.set("var", key, value)
        if defvalue is not None:
            return self.set("var", key, defvalue)

    def __parse_sdc_clock(self, file: str) -> Tuple[str, float]:
        period = None
        with sc_open(file) as f:
            lines = f.read().splitlines()

        # collect simple variables in case clock is specified with a variable
        re_var = r"[A-Za-z0-9_]+"
        re_num = r"[0-9\.]+"
        sdc_vars = {}
        for line in lines:
            tcl_variable = re.findall(fr"^\s*set\s+({re_var})\s+({re_num}|\${re_var})",
                                      line)
            if tcl_variable:
                var_name, var_value = tcl_variable[0]
                sdc_vars[f'${var_name}'] = var_value

        # TODO: handle line continuations
        for line in lines:
            clock_period = re.findall(fr"create_clock\s.*-period\s+({re_num}|\${re_var})",
                                      line)
            if clock_period:
                convert_period = clock_period[0]
                while isinstance(convert_period, str) and convert_period[0] == "$":
                    if convert_period in sdc_vars:
                        convert_period = sdc_vars[convert_period]
                    else:
                        break
                if isinstance(convert_period, str) and convert_period[0] == "$":
                    self.logger.warning('Unable to identify clock period from '
                                        f'{clock_period[0]}.')
                    continue
                else:
                    try:
                        clock_period = float(convert_period)
                    except TypeError:
                        continue

                if period is None:
                    period = clock_period
                else:
                    period = min(period, clock_period)
        return None, period

    def get_clock(self, clock_units_multiplier: float = 1.0) -> Tuple[str, float]:
        name = None
        period = None

        for lib, fileset in self.project.get_filesets():
            for sdc in lib.get_file(fileset=fileset, filetype="sdc"):
                new_name, new_period = self.__parse_sdc_clock(sdc)
                if new_period is not None:
                    if period is None or new_period < period:
                        period = new_period
                        name = new_name

        if period is not None:
            period *= clock_units_multiplier

        # TODO: get SDCs from constraints
        # TODO: get from schema

        return name, period


class CellArea:
    def __init__(self):
        self.__areas = {}

    def add_cell(self, name=None, module=None,
                 cellarea=None, cellcount=None,
                 macroarea=None, macrocount=None,
                 stdcellarea=None, stdcellcount=None):
        if not name and not module:
            return

        if all([metric is None for metric in (
                cellarea, cellcount,
                macroarea, macrocount,
                stdcellarea, stdcellcount)]):
            return

        if not name:
            name = module

        # ensure name is unique
        check_name = name
        idx = 0
        while check_name in self.__areas:
            check_name = f'{name}{idx}'
            idx += 1
        name = check_name

        self.__areas[name] = {
            "module": module,
            "cellarea": cellarea,
            "cellcount": cellcount,
            "macroarea": macroarea,
            "macrocount": macrocount,
            "stdcellarea": stdcellarea,
            "stdcellcount": stdcellcount
        }

    def size(self):
        return len(self.__areas)

    def write_report(self, path):
        with open(path, 'w') as f:
            json.dump(self.__areas, f, indent=4)
