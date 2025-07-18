from typing import Union, Set, List, Tuple

from siliconcompiler.schema import BaseSchema, NamedSchema, EditableSchema, Parameter, \
    PerNode, Scope
from siliconcompiler import DesignSchema


class ASICTimingScenarioSchema(NamedSchema):
    def __init__(self, name: str = None):
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
                example=["api: chip.set('constraint', 'timing', 'worst', 'voltage', 'VDD', '0.9')"],
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
                example=["api: chip.set('constraint', 'timing', 'worst', 'temperature', '125')"],
                help="""Chip temperature applied to the scenario specified in degrees C."""))

        schema.insert(
            'libcorner',
            Parameter(
                '{str}',
                pernode=PerNode.OPTIONAL,
                scope=Scope.GLOBAL,
                shorthelp="Constraint: library corner",
                switch="-constraint_timing_libcorner 'scenario <str>'",
                example=["api: chip.set('constraint', 'timing', 'worst', 'libcorner', 'ttt')"],
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
                example=["api: chip.set('constraint', 'timing', 'worst', 'pexcorner', 'max')"],
                help="""Parasitic corner applied to the scenario. The
                'pexcorner' string must match a corner found in :keypath:`pdk,<pdk>,pexmodel`."""))

        schema.insert(
            'opcond',
            Parameter(
                'str',
                pernode=PerNode.OPTIONAL,
                scope=Scope.GLOBAL,
                shorthelp="Constraint: operating condition",
                switch="-constraint_timing_opcond 'scenario <str>'",
                example=["api: chip.set('constraint', 'timing', 'worst', 'opcond', 'typical_1.0')"],
                help="""Operating condition applied to the scenario. The value
                can be used to access specific conditions within the library
                timing models from the :keypath:`asic,logiclib` timing models."""))

        schema.insert(
            'mode',
            Parameter(
                'str',
                pernode=PerNode.OPTIONAL,
                scope=Scope.GLOBAL,
                shorthelp="Constraint: operating mode",
                switch="-constraint_timing_mode 'scenario <str>'",
                example=["api: chip.set('constraint', 'timing', 'worst', 'mode', 'test')"],
                help="""Operating mode for the scenario. Operating mode strings
                can be values such as test, functional, standby."""))

        schema.insert(
            'sdcfileset',
            Parameter(
                '[(str,str)]',
                pernode=PerNode.OPTIONAL,
                scope=Scope.GLOBAL,
                shorthelp="Constraint: SDC files",
                switch="-constraint_timing_file 'scenario <file>'",
                example=["api: chip.set('constraint', 'timing', 'worst', 'file', 'hello.sdc')"],
                help="""List of timing constraint sets files to use for the scenario. The
                values are combined with any constraints specified by the design
                'constraint' parameter. If no constraints are found, a default
                constraint file is used based on the clock definitions."""))

        schema.insert(
            'check',
            Parameter(
                '{<setup,hold,maxtran,maxcap,mincap,power,leakagepower,dynamicpower,signalem>}',
                pernode=PerNode.OPTIONAL,
                scope=Scope.GLOBAL,
                shorthelp="Constraint: timing checks",
                switch="-constraint_timing_check 'scenario <str>'",
                example=["api: chip.add('constraint', 'timing', 'worst', 'check', 'setup')"],
                help="""
                List of checks for to perform for the scenario. The checks must
                align with the capabilities of the EDA tools and flow being used.
                Checks generally include objectives like meeting setup and hold goals
                and minimize power. Standard check names include setup, hold, power,
                noise, reliability."""))

    def set_pin_voltage(self,
                        pin: str,
                        voltage: float,
                        step: str = None, index: Union[str, int] = None):
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
                        step: str = None, index: Union[str, int] = None) -> float:
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
                      libcorner: str,
                      clobber: bool = False,
                      step: str = None, index: Union[str, int] = None):
        """
        Adds a library corner to the design.

        Args:
            libcorner (str): The name of the library corner to add.
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

    def get_libcorner(self,
                      step: str = None, index: Union[str, int] = None) -> Set[str]:
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
                      step: str = None, index: Union[str, int] = None):
        """
        Sets the parasitic extraction (PEX) corner for the design.

        Args:
            pexcorner (str): The name of the PEX corner to set.
            step (str, optional): step name.
            index (str, optional): index name.
        """
        return self.set("pexcorner", pexcorner, step=step, index=index)

    def get_pexcorner(self,
                      step: str = None, index: Union[str, int] = None) -> str:
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
                 step: str = None, index: Union[str, int] = None):
        """
        Sets the operational mode for the design.

        Args:
            mode (str): The operational mode to set (e.g., "func", "scan").
            step (str, optional): step name.
            index (str, optional): index name.
        """
        return self.set("mode", mode, step=step, index=index)

    def get_mode(self,
                 step: str = None, index: Union[str, int] = None) -> str:
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
                   step: str = None, index: Union[str, int] = None):
        """
        Sets the operating condition for the design.

        Args:
            opcond (str): The operating condition to set (e.g., "WC", "BC").
            step (str, optional): step name.
            index (str, optional): index name.
        """
        return self.set("opcond", opcond, step=step, index=index)

    def get_opcond(self,
                   step: str = None, index: Union[str, int] = None) -> str:
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
                        step: str = None, index: Union[str, int] = None):
        """
        Sets the temperature for the design.

        Args:
            temperature (float): The temperature value to set in degrees Celsius.
            step (str, optional): step name.
            index (str, optional): index name.
        """
        return self.set("temperature", temperature, step=step, index=index)

    def get_temperature(self,
                        step: str = None, index: Union[str, int] = None) -> float:
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
                       design: Union[DesignSchema, str],
                       fileset: str,
                       clobber: bool = False,
                       step: str = None, index: Union[str, int] = None):
        """
        Adds an SDC fileset for a given design.

        Args:
            design (:class:`DesignSchema` or str): The design object or the name of the design to
                associate the fileset with.
            fileset (str): The name of the SDC fileset to add.
            clobber (bool): If True, existing SDC filesets for the design at the specified
                    step/index will be overwritten.
                    If False (default), the SDC fileset will be added.
            step (str, optional): step name.
            index (str, optional): index name.

        Raises:
            TypeError: If `design` is not a DesignSchema object or a string, or if `fileset` is not
                a string.
        """
        if isinstance(design, DesignSchema):
            design = design.name()

        if not isinstance(design, str):
            raise TypeError("design must be a design object or string")

        if not isinstance(fileset, str):
            raise TypeError("fileset must be a string")

        if clobber:
            return self.set("sdcfileset", (design, fileset), step=step, index=index)
        else:
            return self.add("sdcfileset", (design, fileset), step=step, index=index)

    def get_sdcfileset(self,
                       step: str = None, index: Union[str, int] = None) -> List[Tuple[str, str]]:
        """
        Gets the list of SDC filesets.

        Args:
            step (str, optional): step name.
            index (str, optional): index name.

        Returns:
            A list of tuples, where each tuple contains the design name and the SDC fileset name.
        """
        return self.get("sdcfileset", step=step, index=index)

    def add_check(self,
                  check: str,
                  clobber: bool = False,
                  step: str = None, index: Union[str, int] = None):
        """
        Adds a check to the design process.

        Args:
            check (str): The name of the check to add.
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

    def get_check(self, step: str = None, index: Union[str, int] = None) -> Set[str]:
        """
        Gets the set of checks configured for the design process.

        Args:
            step (str, optional): step name.
            index (str, optional): index name.

        Returns:
            A set of check names.
        """
        return self.get("check", step=step, index=index)


class ASICTimingConstraintSchema(BaseSchema):
    def __init__(self):
        super().__init__()

        EditableSchema(self).insert("default", ASICTimingScenarioSchema())

    def add_scenario(self, scenario: ASICTimingScenarioSchema):
        """
        Adds a timing scenario to the design configuration.

        This method is responsible for incorporating a new or updated timing scenario
        into the system's configuration. If a scenario with the same name already
        exists, it will be overwritten (`clobber=True`).

        Args:
            scenario: The `ASICTimingScenarioSchema` object representing the timing scenario to add.
                      This object must have a valid name defined via its `name()` method.

        Raises:
            TypeError: If the provided `scenario` argument is not an instance of
                       `ASICTimingScenarioSchema`.
            ValueError: If the `scenario` object's `name()` method returns None, indicating
                        that the scenario does not have a defined name.
        """
        if not isinstance(scenario, ASICTimingScenarioSchema):
            raise TypeError("scenario must be a timing scenario object")

        if scenario.name() is None:
            raise ValueError("scenario must have a name")

        EditableSchema(self).insert(scenario.name(), scenario, clobber=True)

    def get_scenario(self, scenario: str = None):
        """
        Retrieves one or all timing scenarios from the configuration.

        This method provides flexibility to fetch either a specific timing scenario
        by its name or a collection of all currently defined scenarios.

        Args:
            scenario (str, optional): The name (string) of the specific timing scenario to retrieve.
                      If this argument is omitted or set to None, the method will return
                      a dictionary containing all available timing scenarios.

        Returns:
            - If `scenario` is provided: The :class:`ASICTimingScenarioSchema` object corresponding
              to the specified scenario name.
            - If `scenario` is None: A dictionary where keys are scenario names (str) and
              values are their respective :class:`ASICTimingScenarioSchema` objects.

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
