from typing import Union, Set, List, Tuple

from siliconcompiler.schema import BaseSchema, NamedSchema, EditableSchema, Parameter, PerNode, Scope
from siliconcompiler import DesignSchema


class TimingScenarioSchema(NamedSchema):
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
                help="""List of timing constraint files to use for the scenario. The
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

    def set_pin_voltage(self, pin: str, voltage: float, step: str = None, index: Union[str, int] = None):
        return self.set("voltage", pin, voltage, step=step, index=index)

    def get_pin_voltage(self, pin: str, step: str = None, index: Union[str, int] = None) -> float:
        if not self.valid("voltage", pin):
            raise LookupError(f"{pin} does not have voltage")
        return self.get("voltage", pin, step=step, index=index)

    def add_libcorner(self, libcorner: str, clobber: bool = False, step: str = None, index: Union[str, int] = None):
        if clobber:
            return self.set("libcorner", libcorner, step=step, index=index)
        else:
            return self.add("libcorner", libcorner, step=step, index=index)

    def get_libcorner(self, step: str = None, index: Union[str, int] = None) -> Set[str]:
        return self.get("libcorner", step=step, index=index)

    def set_pexcorner(self, pexcorner: str, step: str = None, index: Union[str, int] = None):
        return self.set("pexcorner", pexcorner, step=step, index=index)

    def get_pexcorner(self, step: str = None, index: Union[str, int] = None) -> str:
        return self.get("pexcorner", step=step, index=index)

    def set_mode(self, mode: str, step: str = None, index: Union[str, int] = None):
        return self.set("mode", mode, step=step, index=index)

    def get_mode(self, step: str = None, index: Union[str, int] = None) -> str:
        return self.get("mode", step=step, index=index)

    def set_opcond(self, opcond: str, step: str = None, index: Union[str, int] = None):
        return self.set("opcond", opcond, step=step, index=index)

    def get_opcond(self, step: str = None, index: Union[str, int] = None) -> str:
        return self.get("opcond", step=step, index=index)

    def set_temperature(self, temperature: float, step: str = None, index: Union[str, int] = None):
        return self.set("temperature", temperature, step=step, index=index)

    def get_temperature(self, step: str = None, index: Union[str, int] = None) -> float:
        return self.get("temperature", step=step, index=index)

    def add_sdcfileset(self, design: Union[DesignSchema, str], fileset: str, clobber: bool = False, step: str = None, index: Union[str, int] = None):
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

    def get_sdcfileset(self, step: str = None, index: Union[str, int] = None) -> List[Tuple[str, str]]:
        return self.get("sdcfileset", step=step, index=index)

    def add_check(self, check: str, clobber: bool = False, step: str = None, index: Union[str, int] = None):
        if clobber:
            return self.set("check", check, step=step, index=index)
        else:
            return self.add("check", check, step=step, index=index)

    def get_check(self, step: str = None, index: Union[str, int] = None) -> Set[str]:
        return self.get("check", step=step, index=index)


class TimingConstraintSchema(BaseSchema):
    def __init__(self):
        super().__init__()

        EditableSchema(self).insert("default", TimingScenarioSchema())

    def add_scenario(self, scenario: TimingScenarioSchema):
        if not isinstance(scenario, TimingScenarioSchema):
            raise TypeError("scenario must be a timing scenario object")

        if scenario.name() is None:
            raise ValueError("scenario must have a name")

        EditableSchema(self).insert(scenario.name(), scenario, clobber=True)

    def get_scenario(self, scenario: str = None):
        if scenario is None:
            scenarios = {}
            for scenario in self.getkeys():
                scenarios[scenario] = self.get(scenario, field="schema")
            return scenarios

        if not self.valid(scenario):
            raise LookupError(f"{scenario} is not defined")
        return self.get(scenario, field="schema")
