# Copyright 2025 Silicon Compiler Authors. All Rights Reserved.

# NOTE: this file cannot rely on any third-party dependencies, including other
# SC dependencies outside of its directory, since it may be used by tool drivers
# that have isolated Python environments.

from siliconcompiler.schema.new.baseschema import BaseSchema
from siliconcompiler.schema.new.editableschema import EditableSchema
from siliconcompiler.schema.new.parameter import Parameter, Scope

from siliconcompiler.schema.new.schema_cfg import schema_cfg


class Schema(BaseSchema):
    def __init__(self):
        super().__init__()

        schema_cfg(self)


class PDK(BaseSchema):
    def __init__(self):
        super().__init__()

        schema = EditableSchema(self)
        schema.add("foundry", Parameter(
            "str",
            scope=Scope.GLOBAL,
            shorthelp="PDK: foundry name",
            switch="-pdk_foundry 'pdkname <str>'",
            example=["cli: -pdk_foundry 'asap7 virtual'",
                     "api: chip.set('pdk', 'asap7', 'foundry', 'virtual')"],
            help="""
            Name of foundry corporation. Examples include intel, gf, tsmc,
            samsung, skywater, virtual. The \'virtual\' keyword is reserved for
            simulated non-manufacturable processes."""))
        schema.add("node", Parameter(
            "float",
            scope=Scope.GLOBAL,
            unit='nm',
            shorthelp="PDK: process node",
            switch="-pdk_node 'pdkname <float>'",
            example=["cli: -pdk_node 'asap7 130'",
                     "api: chip.set('pdk', 'asap7', 'node', 130)"],
            help="""
            Approximate relative minimum dimension of the process target specified
            in nanometers. The parameter is required for flows and tools that
            leverage the value to drive technology dependent synthesis and APR
            optimization. Node examples include 180, 130, 90, 65, 45, 32, 22 14,
            10, 7, 5, 3."""))


class Design(BaseSchema):
    def __init__(self):
        super().__init__()

        schema = EditableSchema(self)
        schema.add("name", Parameter(
            "str"))
        schema.add("input", "default", "default", Parameter(
            "file"))


if __name__ == "__main__":
    schema = Schema()

    # import json
    # print(json.dumps(schema.getdict(include_default=False), indent=2))
    schema.write_manifest("test.json")
