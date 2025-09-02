from siliconcompiler.schema import BaseSchema

from siliconcompiler.constraints.asic_timing import \
    ASICTimingConstraintSchema, ASICTimingScenarioSchema
from siliconcompiler.constraints.asic_floorplan import ASICAreaConstraint
from siliconcompiler.constraints.asic_pins import \
    ASICPinConstraint, ASICPinConstraints
from siliconcompiler.constraints.asic_component import \
    ASICComponentConstraint, ASICComponentConstraints

from siliconcompiler.constraints.fpga_timing import \
    FPGATimingConstraintSchema, FPGATimingScenarioSchema


class FPGAPinConstraints(BaseSchema):
    pass


class FPGAComponentConstraints(BaseSchema):
    pass


__all__ = [
    "ASICTimingConstraintSchema",
    "ASICTimingScenarioSchema",
    "ASICAreaConstraint",
    "ASICPinConstraint",
    "ASICPinConstraints",
    "ASICComponentConstraint",
    "ASICComponentConstraints",
    "FPGATimingConstraintSchema",
    "FPGATimingScenarioSchema"
]
