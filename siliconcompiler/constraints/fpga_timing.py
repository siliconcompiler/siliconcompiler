from typing import Union, Optional

from siliconcompiler.schema import BaseSchema, NamedSchema, EditableSchema, Parameter, \
    PerNode, Scope


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

        EditableSchema(self).insert("default", FPGATimingScenarioSchema())

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

        EditableSchema(self).insert(scenario.name, scenario, clobber=True)

    def get_scenario(self, scenario: Optional[str] = None):
        """
        Retrieves one or all timing scenarios from the configuration.

        This method provides flexibility to fetch either a specific timing scenario
        by its name or a collection of all currently defined scenarios.

        Args:
            scenario (str, optional): The name (string) of the specific timing scenario to retrieve.
                      If this argument is omitted or set to None, the method will return
                      a dictionary containing all available timing scenarios.

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
            for scenario in self.getkeys():
                scenarios[scenario] = self.get(scenario, field="schema")
            return scenarios

        if not self.valid(scenario):
            raise LookupError(f"{scenario} is not defined")
        return self.get(scenario, field="schema")

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
            :class:FPGATimingScenarioSchema: The newly created :class:`FPGATimingScenarioSchema`
                object.

        Raises:
            ValueError: If the provided `scenario` name is empty or None.
            LookupError: If a scenario with the specified `scenario` name already exists
                         in the configuration.
        """
        if not scenario:
            raise ValueError("scenario name is required")

        if self.valid(scenario):
            raise LookupError(f"{scenario} scenario already exists")

        scenarioobj = FPGATimingScenarioSchema(scenario)
        self.add_scenario(scenarioobj)
        return scenarioobj

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

        if not self.valid(scenario):
            return False

        EditableSchema(self).remove(scenario)
        return True
