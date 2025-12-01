from typing import Union, Set, List, Tuple, Optional, Dict

from siliconcompiler.schema import BaseSchema, NamedSchema, EditableSchema, Parameter, \
    PerNode, Scope
from siliconcompiler import Design
from siliconcompiler.constraints.timing_mode import TimingModeSchema
from siliconcompiler.schema.baseschema import LazyLoad


class ASICTimingScenarioSchema(NamedSchema):
    """
    Represents a single timing scenario for ASIC design constraints.

    This class encapsulates various parameters that define a specific timing
    scenario, such as operating voltage, temperature, library corners, PEX corners,
    operating mode, SDC filesets, and timing checks to be performed.
    """

    def __init__(self, name: Optional[str] = None):
        super().__init__()
        self.set_name(name)

        schema = EditableSchema(self)
        schema.insert(
            'voltage', 'default',
            Parameter(
                "float",
                pernode=PerNode.OPTIONAL,
                unit='V',
                scope=Scope.GLOBAL,
                shorthelp="Constraint: pin voltage level",
                switch="-constraint_timing_voltage 'scenario pin <float>'",
                example=["api: asic.set('constraint', 'timing', 'worst', 'voltage', 'VDD', '0.9')"],
                help="""Operating voltage applied to a specific pin in the scenario."""))

        schema.insert(
            'temperature',
            Parameter(
                'float',
                pernode=PerNode.OPTIONAL,
                unit='C',
                scope=Scope.GLOBAL,
                shorthelp="Constraint: temperature",
                switch="-constraint_timing_temperature 'scenario <float>'",
                example=["api: asic.set('constraint', 'timing', 'worst', 'temperature', '125')"],
                help="""Chip temperature applied to the scenario specified in degrees C."""))

        schema.insert(
            'libcorner',
            Parameter(
                '{str}',
                pernode=PerNode.OPTIONAL,
                scope=Scope.GLOBAL,
                shorthelp="Constraint: library corner",
                switch="-constraint_timing_libcorner 'scenario <str>'",
                example=["api: asic.set('constraint', 'timing', 'worst', 'libcorner', 'ttt')"],
                help="""List of characterization corners used to select
                timing files for all logiclibs and macrolibs."""))

        schema.insert(
            'pexcorner',
            Parameter(
                'str',
                pernode=PerNode.OPTIONAL,
                scope=Scope.GLOBAL,
                shorthelp="Constraint: pex corner",
                switch="-constraint_timing_pexcorner 'scenario <str>'",
                example=["api: asic.set('constraint', 'timing', 'worst', 'pexcorner', 'max')"],
                help="""Parasitic corner applied to the scenario. The
                'pexcorner' string must match a corner found in
                :keypath:`PDK,pdk,pexmodelfileset`."""))

        schema.insert(
            'opcond',
            Parameter(
                'str',
                pernode=PerNode.OPTIONAL,
                scope=Scope.GLOBAL,
                shorthelp="Constraint: operating condition",
                switch="-constraint_timing_opcond 'scenario <str>'",
                example=["api: asic.set('constraint', 'timing', 'worst', 'opcond', 'typical_1.0')"],
                help="""Operating condition applied to the scenario. The value
                can be used to access specific conditions within the library
                timing models from the :keypath:`ASIC,asic,asiclib` timing models."""))

        schema.insert(
            'mode',
            Parameter(
                'str',
                pernode=PerNode.OPTIONAL,
                scope=Scope.GLOBAL,
                shorthelp="Constraint: operating mode",
                switch="-constraint_timing_mode 'scenario <str>'",
                example=["api: asic.set('constraint', 'timing', 'worst', 'mode', 'test')"],
                help="""Operating mode for the scenario. Operating mode strings
                can be values such as test, functional, standby."""))

        schema.insert(
            'check',
            Parameter(
                '{<setup,hold,maxtran,maxcap,mincap,power,leakagepower,dynamicpower,signalem>}',
                pernode=PerNode.OPTIONAL,
                scope=Scope.GLOBAL,
                shorthelp="Constraint: timing checks",
                switch="-constraint_timing_check 'scenario <str>'",
                example=["api: asic.add('constraint', 'timing', 'worst', 'check', 'setup')"],
                help="""
                List of checks for to perform for the scenario. The checks must
                align with the capabilities of the EDA tools and flow being used.
                Checks generally include objectives like meeting setup and hold goals
                and minimize power. Standard check names include setup, hold, power,
                noise, reliability."""))

    def set_pin_voltage(self,
                        pin: str,
                        voltage: float,
                        step: Optional[str] = None, index: Optional[Union[str, int]] = None):
        """
        Sets the voltage for a specified pin.

        Args:
            pin (str): The name of the pin.
            voltage (float): The voltage value to set.
            step (str, optional): step name.
            index (str, optional): index name.
        """
        return self.set("voltage", pin, voltage, step=step, index=index)

    def get_pin_voltage(self,
                        pin: str,
                        step: Optional[str] = None, index: Optional[Union[str, int]] = None) \
            -> float:
        """
        Gets the voltage of a specified pin.

        Args:
            pin (str): The name of the pin.
            step (str, optional): step name.
            index (str, optional): index name.

        Returns:
            The voltage of the pin.

        Raises:
            LookupError: If the specified pin does not have a voltage defined.
        """
        if not self.valid("voltage", pin):
            raise LookupError(f"{pin} does not have voltage")
        return self.get("voltage", pin, step=step, index=index)

    def add_libcorner(self,
                      libcorner: Union[List[str], str],
                      clobber: bool = False,
                      step: Optional[str] = None, index: Optional[Union[str, int]] = None):
        """
        Adds a library corner to the design.

        Args:
            libcorner (Union[List[str], str]): One or more library corners to add.
            clobber (bool): If True, existing library corners at the specified step/index will
                    be overwritten.
                    If False (default), the library corner will be added.
            step (str, optional): step name.
            index (str, optional): index name.
        """
        if clobber:
            return self.set("libcorner", libcorner, step=step, index=index)
        else:
            return self.add("libcorner", libcorner, step=step, index=index)

    def get_libcorner(self, step: Optional[str] = None, index: Optional[Union[str, int]] = None) \
            -> Set[str]:
        """
        Gets the set of library corners.

        Args:
            step (str, optional): step name.
            index (str, optional): index name.

        Returns:
            A set of library corner names.
        """
        return self.get("libcorner", step=step, index=index)

    def set_pexcorner(self,
                      pexcorner: str,
                      step: Optional[str] = None, index: Optional[Union[str, int]] = None):
        """
        Sets the parasitic extraction (PEX) corner for the design.

        Args:
            pexcorner (str): The name of the PEX corner to set.
            step (str, optional): step name.
            index (str, optional): index name.
        """
        return self.set("pexcorner", pexcorner, step=step, index=index)

    def get_pexcorner(self,
                      step: Optional[str] = None, index: Optional[Union[str, int]] = None) -> str:
        """
        Gets the parasitic extraction (PEX) corner currently set for the design.

        Args:
            step (str, optional): step name.
            index (str, optional): index name.

        Returns:
            The name of the PEX corner.
        """
        return self.get("pexcorner", step=step, index=index)

    def set_mode(self,
                 mode: str,
                 step: Optional[str] = None, index: Optional[Union[str, int]] = None):
        """
        Sets the operational mode for the design.

        Args:
            mode (str): The operational mode to set (e.g., "func", "scan").
            step (str, optional): step name.
            index (str, optional): index name.
        """
        return self.set("mode", mode, step=step, index=index)

    def get_mode(self,
                 step: Optional[str] = None, index: Optional[Union[str, int]] = None) -> str:
        """
        Gets the operational mode currently set for the design.

        Args:
            step (str, optional): step name.
            index (str, optional): index name.

        Returns:
            The name of the operational mode.
        """
        return self.get("mode", step=step, index=index)

    def set_opcond(self,
                   opcond: str,
                   step: Optional[str] = None, index: Optional[Union[str, int]] = None):
        """
        Sets the operating condition for the design.

        Args:
            opcond (str): The operating condition to set (e.g., "WC", "BC").
            step (str, optional): step name.
            index (str, optional): index name.
        """
        return self.set("opcond", opcond, step=step, index=index)

    def get_opcond(self,
                   step: Optional[str] = None, index: Optional[Union[str, int]] = None) -> str:
        """
        Gets the operating condition currently set for the design.

        Args:
            step (str, optional): step name.
            index (str, optional): index name.

        Returns:
            The name of the operating condition.
        """
        return self.get("opcond", step=step, index=index)

    def set_temperature(self,
                        temperature: float,
                        step: Optional[str] = None, index: Optional[Union[str, int]] = None):
        """
        Sets the temperature for the design.

        Args:
            temperature (float): The temperature value to set in degrees Celsius.
            step (str, optional): step name.
            index (str, optional): index name.
        """
        return self.set("temperature", temperature, step=step, index=index)

    def get_temperature(self, step: Optional[str] = None, index: Optional[Union[str, int]] = None) \
            -> float:
        """
        Gets the temperature currently set for the design.

        Args:
            step (str, optional): step name.
            index (str, optional): index name.

        Returns:
            The temperature in degrees Celsius.
        """
        return self.get("temperature", step=step, index=index)

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
        import warnings
        warnings.warn("This function is deprecated and will be removed in a future version, "
                      "use TimingModeSchema instead", DeprecationWarning, stacklevel=2)

        mode = self.get_mode(step=step, index=index)
        if mode is None:
            raise ValueError("Mode not defined")

        timing_constraints: ASICTimingConstraintSchema = self._parent()._parent()
        try:
            modeobj = timing_constraints.get_mode(mode)
        except LookupError:
            modeobj = timing_constraints.make_mode(mode)
        return modeobj.add_sdcfileset(design=design, fileset=fileset,
                                      clobber=clobber,
                                      step=step, index=index)

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
        import warnings
        warnings.warn("This function is deprecated and will be removed in a future version, "
                      "use TimingModeSchema instead", DeprecationWarning, stacklevel=2)

        mode = self.get_mode(step=step, index=index)
        if mode is None:
            raise ValueError("Mode not defined")

        timing_constraints: ASICTimingConstraintSchema = self._parent()._parent()
        try:
            modeobj = timing_constraints.get_mode(mode)
        except LookupError:
            modeobj = timing_constraints.make_mode(mode)
        return modeobj.get_sdcfileset(step=step, index=index)

    def add_check(self,
                  check: Union[List[str], str],
                  clobber: bool = False,
                  step: Optional[str] = None, index: Optional[Union[str, int]] = None):
        """
        Adds a check to the design process.

        Args:
            check (Union[List[str], str]): One or more checks to add.
            clobber (bool): If True, existing checks at the specified step/index will
                    be overwritten.
                    If False (default), the check will be added.
            step (str, optional): step name.
            index (str, optional): index name.
        """
        if clobber:
            return self.set("check", check, step=step, index=index)
        else:
            return self.add("check", check, step=step, index=index)

    def get_check(self, step: Optional[str] = None, index: Optional[Union[str, int]] = None) \
            -> Set[str]:
        """
        Gets the set of checks configured for the design process.

        Args:
            step (str, optional): step name.
            index (str, optional): index name.

        Returns:
            A set of check names.
        """
        return self.get("check", step=step, index=index)

    def _from_dict(self, manifest: Dict,
                   keypath: Union[List[str], Tuple[str, ...]],
                   version: Optional[Tuple[int, ...]] = None,
                   lazyload: LazyLoad = LazyLoad.ON) \
            -> Tuple[Set[Tuple[str, ...]], Set[Tuple[str, ...]]]:

        sdcfileset = None
        if version and version < (0, 53, 0):
            sdcfileset = manifest.pop("sdcfileset", None)
            lazyload = LazyLoad.OFF

        ret = super()._from_dict(manifest, keypath, version, lazyload)

        if sdcfileset:
            param = Parameter.from_dict(sdcfileset, keypath=(*keypath, "sdcfileset"),
                                        version=version)
            for value, step, index in param.getvalues():
                if self.get_mode(step=step, index=index) is None:
                    self.set_mode("_importcreated_", step=step, index=index)
                for design, fileset in value:
                    self.add_sdcfileset(design, fileset, step=step, index=index)

        return ret


class ASICTimingConstraintSchema(BaseSchema):
    """
    Manages a collection of ASIC timing scenarios for design constraints.

    This class provides methods to add, retrieve, create, and remove
    individual :class:`ASICTimingScenarioSchema` objects, allowing for organized
    management of various timing-related constraints for different operating
    conditions or analysis modes.
    """

    def __init__(self):
        super().__init__()

        EditableSchema(self).insert("scenario", "default", ASICTimingScenarioSchema())
        EditableSchema(self).insert("mode", "default", TimingModeSchema())

    def add_scenario(self, scenario: ASICTimingScenarioSchema):
        """
        Adds a timing scenario to the design configuration.

        This method is responsible for incorporating a new or updated timing scenario
        into the system's configuration. If a scenario with the same name already
        exists, it will be overwritten (`clobber=True`).

        Args:
            scenario: The :class:`ASICTimingScenarioSchema` object representing the timing scenario
                      to add. This object must have a valid name defined via its `name()` method.

        Raises:
            TypeError: If the provided `scenario` argument is not an instance of
                       :class:`ASICTimingScenarioSchema`.
            ValueError: If the `scenario` object's `name()` method returns None, indicating
                        that the scenario does not have a defined name.
        """
        if not isinstance(scenario, ASICTimingScenarioSchema):
            raise TypeError("scenario must be a timing scenario object")

        if scenario.name is None:
            raise ValueError("scenario must have a name")

        EditableSchema(self).insert("scenario", scenario.name, scenario, clobber=True)

    def get_scenario(self, scenario: Optional[str] = None) \
            -> Union[ASICTimingScenarioSchema, Dict[str, ASICTimingScenarioSchema]]:
        """
        Retrieves one or all timing scenarios from the configuration.

        This method provides flexibility to fetch either a specific timing scenario
        by its name or a collection of all currently defined scenarios.

        Args:
            scenario (str, optional): The name (string) of the specific timing scenario to retrieve.
                                      If this argument is omitted or set to None, the method will
                                      return a dictionary containing all available timing scenarios.

        Returns:
            If `scenario` is provided: The :class:`ASICTimingScenarioSchema` object corresponding
                to the specified scenario name.
            If `scenario` is None: A dictionary where keys are scenario names (str) and
                values are their respective :class:`ASICTimingScenarioSchema` objects.

        Raises:
            LookupError: If a specific `scenario` name is provided but no scenario with
                         that name is found in the configuration.
        """
        if scenario is None:
            scenarios = {}
            for name in self.getkeys("scenario"):
                scenarios[name] = self.get("scenario", name, field="schema")
            return scenarios

        if not self.valid("scenario", scenario):
            raise LookupError(f"{scenario} is not defined")
        return self.get("scenario", scenario, field="schema")

    def make_scenario(self, scenario: str) -> ASICTimingScenarioSchema:
        """
        Creates and adds a new timing scenario with the specified name.

        This method initializes a new :class:`ASICTimingScenarioSchema` object with the given
        name and immediately adds it to the constraint configuration. It ensures that
        a scenario with the same name does not already exist, preventing accidental
        overwrites.

        Args:
            scenario (str): The name for the new timing scenario. This name must be
                            a non-empty string and unique within the current configuration.

        Returns:
            :class:ASICTimingScenarioSchema: The newly created :class:`ASICTimingScenarioSchema`
                object.

        Raises:
            ValueError: If the provided `scenario` name is empty or None.
            LookupError: If a scenario with the specified `scenario` name already exists
                         in the configuration.
        """
        if not scenario:
            raise ValueError("scenario name is required")

        if self.valid("scenario", scenario):
            raise LookupError(f"{scenario} scenario already exists")

        scenarioobj = ASICTimingScenarioSchema(scenario)
        self.add_scenario(scenarioobj)
        return scenarioobj

    def copy_scenario(self, scenario: str, name: str, insert: bool = True) \
            -> ASICTimingScenarioSchema:
        """
        Copies an existing timing scenario, renames it, and optionally adds it to the design.

        This method retrieves the scenario identified by ``scenario``, creates a
        deep copy of it, and renames the copy to ``name``. If ``insert`` is True,
        the new scenario is immediately added to the configuration.

        Args:
            scenario (str): The name of the existing scenario to be copied.
            name (str): The name to assign to the new copied scenario.
            insert (bool, optional): Whether to add the newly created scenario
                to the configuration. Defaults to True.

        Returns:
            ASICTimingScenarioSchema: The newly created copy of the scenario.

        Raises:
            LookupError: If the source scenario specified by ``scenario`` does not exist.
        """
        constraint = EditableSchema(self.get_scenario(scenario)).copy()
        EditableSchema(constraint).rename(name)
        if insert:
            if self.valid("scenario", name):
                raise ValueError(f"{name} already exists")
            self.add_scenario(constraint)
        return constraint

    def remove_scenario(self, scenario: str) -> bool:
        """
        Removes a timing scenario from the design configuration.

        This method deletes the specified timing scenario from the system's
        configuration.

        Args:
            scenario (str): The name of the timing scenario to remove.
                            This name must be a non-empty string.

        Returns:
            bool: True if the scenario was successfully removed, False if no
                  scenario with the given name was found.

        Raises:
            ValueError: If the provided `scenario` name is empty or None.
        """
        if not scenario:
            raise ValueError("scenario name is required")

        if not self.valid("scenario", scenario):
            return False

        EditableSchema(self).remove("scenario", scenario)
        return True

    def add_mode(self, mode: TimingModeSchema):
        """
        Adds a timing mode to the design configuration.

        This method is responsible for incorporating a new or updated timing mode
        into the system's configuration. If a mode with the same name already
        exists, it will be overwritten (`clobber=True`).

        Args:
            mode: The :class:`TimingModeSchema` object representing the timing mode
                  to add. This object must have a valid name defined via its `name()` method.

        Raises:
            TypeError: If the provided `mode` argument is not an instance of
                       :class:`TimingModeSchema`.
            ValueError: If the `mode` object's `name()` method returns None, indicating
                        that the mode does not have a defined name.
        """
        if not isinstance(mode, TimingModeSchema):
            raise TypeError("mode must be a timing mode object")

        if mode.name is None:
            raise ValueError("mode must have a name")

        EditableSchema(self).insert("mode", mode.name, mode, clobber=True)

    def get_mode(self, mode: Optional[str] = None) \
            -> Union[TimingModeSchema, Dict[str, TimingModeSchema]]:
        """
        Retrieves one or all timing modes from the configuration.

        This method provides flexibility to fetch either a specific timing mode
        by its name or a collection of all currently defined modes.

        Args:
            mode (str, optional): The name (string) of the specific timing mode to retrieve.
                                  If this argument is omitted or set to None, the method will
                                  return a dictionary containing all available timing modes.

        Returns:
            If `mode` is provided: The :class:`TimingModeSchema` object corresponding
                to the specified mode name.
            If `mode` is None: A dictionary where keys are mode names (str) and
                values are their respective :class:`TimingModeSchema` objects.

        Raises:
            LookupError: If a specific `mode` name is provided but no mode with
                         that name is found in the configuration.
        """
        if mode is None:
            modes = {}
            for name in self.getkeys("mode"):
                modes[name] = self.get("mode", name, field="schema")
            return modes

        if not self.valid("mode", mode):
            raise LookupError(f"{mode} is not defined")
        return self.get("mode", mode, field="schema")

    def make_mode(self, mode: str) -> TimingModeSchema:
        """
        Creates and adds a new timing mode with the specified name.

        This method initializes a new :class:`TimingModeSchema` object with the given
        name and immediately adds it to the constraint configuration. It ensures that
        a mode with the same name does not already exist, preventing accidental
        overwrites.

        Args:
            mode (str): The name for the new timing mode. This name must be
                        a non-empty string and unique within the current configuration.

        Returns:
            :class:`TimingModeSchema`: The newly created :class:`TimingModeSchema`
                object.

        Raises:
            ValueError: If the provided `mode` name is empty or None.
            LookupError: If a mode with the specified `mode` name already exists
                         in the configuration.
        """
        if not mode:
            raise ValueError("mode name is required")

        if self.valid("mode", mode):
            raise LookupError(f"{mode} mode already exists")

        modeobj = TimingModeSchema(mode)
        self.add_mode(modeobj)
        return modeobj

    def copy_mode(self, mode: str, name: str, insert: bool = True) \
            -> TimingModeSchema:
        """
        Copies an existing timing mode, renames it, and optionally adds it to the design.

        This method retrieves the mode identified by ``mode``, creates a
        deep copy of it, and renames the copy to ``name``. If ``insert`` is True,
        the new mode is immediately added to the configuration.

        Args:
            mode (str): The name of the existing mode to be copied.
            name (str): The name to assign to the new copied mode.
            insert (bool, optional): Whether to add the newly created mode
                to the configuration. Defaults to True.

        Returns:
            TimingModeSchema: The newly created copy of the mode.

        Raises:
            LookupError: If the source mode specified by ``mode`` does not exist.
        """
        newmode = EditableSchema(self.get_mode(mode)).copy()
        EditableSchema(newmode).rename(name)
        if insert:
            if self.valid("mode", name):
                raise ValueError(f"{name} already exists")
            self.add_mode(newmode)
        return newmode

    def remove_mode(self, mode: str) -> bool:
        """
        Removes a timing mode from the design configuration.

        This method deletes the specified timing mode from the system's
        configuration.

        Args:
            mode (str): The name of the timing mode to remove.
                        This name must be a non-empty string.

        Returns:
            bool: True if the mode was successfully removed, False if no
                  mode with the given name was found.

        Raises:
            ValueError: If the provided `mode` name is empty or None.
        """
        if not mode:
            raise ValueError("mode name is required")

        if not self.valid("mode", mode):
            return False

        EditableSchema(self).remove("mode", mode)
        return True

    def _from_dict(self, manifest: Dict,
                   keypath: Union[List[str], Tuple[str, ...]],
                   version: Optional[Tuple[int, ...]] = None,
                   lazyload: LazyLoad = LazyLoad.ON) \
            -> Tuple[Set[Tuple[str, ...]], Set[Tuple[str, ...]]]:
        if version and version < (0, 53, 0):
            manifest.pop("__meta__", None)
            manifest = {
                "scenario": manifest,
                "mode": self.getdict("mode")
            }
            lazyload = LazyLoad.OFF

        return super()._from_dict(manifest, keypath, version, lazyload)
