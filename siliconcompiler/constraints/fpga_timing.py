from typing import List, Set, Tuple, Union, Optional, Dict

from siliconcompiler.schema import BaseSchema, NamedSchema, EditableSchema, Parameter, \
    PerNode, Scope
from siliconcompiler.constraints.timing_mode import TimingModeSchema
from siliconcompiler.schema.baseschema import LazyLoad


class FPGATimingScenarioSchema(NamedSchema):
    """
    Represents a single timing scenario for FPGA design constraints.

    This class encapsulates various parameters that define a specific timing
    scenario and operating mode.
    """

    def __init__(self, name: Optional[str] = None):
        super().__init__()
        self.set_name(name)

        schema = EditableSchema(self)
        schema.insert(
            'mode',
            Parameter(
                'str',
                pernode=PerNode.OPTIONAL,
                scope=Scope.GLOBAL,
                shorthelp="Constraint: operating mode",
                switch="-constraint_timing_mode 'scenario <str>'",
                example=["api: fpga.set('constraint', 'timing', 'worst', 'mode', 'test')"],
                help="""Operating mode for the scenario. Operating mode strings
                can be values such as test, functional, standby."""))

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

    def get_mode(self, step: Optional[str] = None, index: Optional[Union[str, int]] = None) -> str:
        """
        Gets the operational mode currently set for the design.

        Args:
            step (str, optional): step name.
            index (str, optional): index name.

        Returns:
            The name of the operational mode.
        """
        return self.get("mode", step=step, index=index)


class FPGATimingConstraintSchema(BaseSchema):
    """
    Manages a collection of FPGA timing scenarios for design constraints.

    This class provides methods to add, retrieve, create, and remove
    individual :class:`FPGATimingScenarioSchema` objects, allowing for organized
    management of various timing-related constraints for different operating
    conditions or analysis modes.
    """

    def __init__(self):
        super().__init__()

        EditableSchema(self).insert("scenario", "default", FPGATimingScenarioSchema())
        EditableSchema(self).insert("mode", "default", TimingModeSchema())

    def add_scenario(self, scenario: FPGATimingScenarioSchema):
        """
        Adds a timing scenario to the design configuration.

        This method is responsible for incorporating a new or updated timing scenario
        into the system's configuration. If a scenario with the same name already
        exists, it will be overwritten (`clobber=True`).

        Args:
            scenario: The :class:`FPGATimingScenarioSchema` object representing the timing scenario
                      to add. This object must have a valid name defined via its `name()` method.

        Raises:
            TypeError: If the provided `scenario` argument is not an instance of
                       :class:`FPGATimingScenarioSchema`.
            ValueError: If the `scenario` object's `name()` method returns None, indicating
                        that the scenario does not have a defined name.
        """
        if not isinstance(scenario, FPGATimingScenarioSchema):
            raise TypeError("scenario must be a timing scenario object")

        if scenario.name is None:
            raise ValueError("scenario must have a name")

        EditableSchema(self).insert("scenario", scenario.name, scenario, clobber=True)

    def get_scenario(self, scenario: Optional[str] = None) \
            -> Union[FPGATimingScenarioSchema, Dict[str, FPGATimingScenarioSchema]]:
        """
        Retrieves one or all timing scenarios from the configuration.

        This method provides flexibility to fetch either a specific timing scenario
        by its name or a collection of all currently defined scenarios.

        Args:
            scenario (str, optional): The name (string) of the specific timing scenario to retrieve.
                                      If this argument is omitted or set to None, the method will
                                      return a dictionary containing all available timing scenarios.

        Returns:
            If `scenario` is provided: The :class:`FPGATimingScenarioSchema` object corresponding
                to the specified scenario name.
            If `scenario` is None: A dictionary where keys are scenario names (str) and
                values are their respective :class:`FPGATimingScenarioSchema` objects.

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

    def make_scenario(self, scenario: str) -> FPGATimingScenarioSchema:
        """
        Creates and adds a new timing scenario with the specified name.

        This method initializes a new :class:`FPGATimingScenarioSchema` object with the given
        name and immediately adds it to the constraint configuration. It ensures that
        a scenario with the same name does not already exist, preventing accidental
        overwrites.

        Args:
            scenario (str): The name for the new timing scenario. This name must be
                            a non-empty string and unique within the current configuration.

        Returns:
            :class:`FPGATimingScenarioSchema`: The newly created :class:`FPGATimingScenarioSchema`
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

        scenarioobj = FPGATimingScenarioSchema(scenario)
        self.add_scenario(scenarioobj)
        return scenarioobj

    def copy_scenario(self, scenario: str, name: str, insert: bool = True) \
            -> FPGATimingScenarioSchema:
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
            FPGATimingScenarioSchema: The newly created copy of the scenario.

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
