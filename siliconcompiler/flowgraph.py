from siliconcompiler.schema import BaseSchema, NamedSchema
from siliconcompiler.schema import EditableSchema, Parameter, Scope
from siliconcompiler.schema.utils import trim


class FlowgraphSchema(NamedSchema):
    def __init__(self, name=None):
        super().__init__(name=name)

        schema = EditableSchema(self)
        schema.insert("default", "default", NodeSchema())


class NodeSchema(BaseSchema):
    def __init__(self):
        super().__init__()

        schema_flowgraph(self)


###############################################################################
# Flow Configuration
###############################################################################
def schema_flowgraph(schema):
    schema = EditableSchema(schema)

    # flowgraph input
    schema.insert(
        'input',
        Parameter(
            '[(str,str)]',
            scope=Scope.GLOBAL,
            shorthelp="Flowgraph: step input",
            switch="-flowgraph_input 'flow step index <(str,str)>'",
            example=[
                "cli: -flowgraph_input 'asicflow cts 0 (place,0)'",
                "api: chip.set('flowgraph', 'asicflow', 'cts', '0', 'input', ('place', '0'))"],
            help=trim("""A list of inputs for the current step and index, specified as a
            (step, index) tuple.""")))

    # flowgraph metric weights
    metric = 'default'
    schema.insert(
        'weight', metric,
        Parameter(
            'float',
            scope=Scope.GLOBAL,
            defvalue=0.0,
            shorthelp="Flowgraph: metric weights",
            switch="-flowgraph_weight 'flow step index metric <float>'",
            example=[
                "cli: -flowgraph_weight 'asicflow cts 0 area_cells 1.0'",
                "api: chip.set('flowgraph', 'asicflow', 'cts', '0', 'weight', 'area_cells', 1.0)"],
            help=trim("""Weights specified on a per step and per metric basis used to give
            effective "goodness" score for a step by calculating the sum all step
            real metrics results by the corresponding per step weights.""")))

    schema.insert(
        'goal', metric,
        Parameter(
            'float',
            scope=Scope.GLOBAL,
            shorthelp="Flowgraph: metric goals",
            switch="-flowgraph_goal 'flow step index metric <float>'",
            example=[
                "cli: -flowgraph_goal 'asicflow cts 0 area_cells 1.0'",
                "api: chip.set('flowgraph', 'asicflow', 'cts', '0', 'goal', 'errors', 0)"],
            help=trim("""Goals specified on a per step and per metric basis used to
            determine whether a certain task can be considered when merging
            multiple tasks at a minimum or maximum node. A task is considered
            failing if the absolute value of any of its metrics are larger than
            the goal for that metric, if set.""")))

    # flowgraph tool
    schema.insert(
        'tool',
        Parameter(
            'str',
            scope=Scope.GLOBAL,
            shorthelp="Flowgraph: tool selection",
            switch="-flowgraph_tool 'flow step index <str>'",
            example=[
                "cli: -flowgraph_tool 'asicflow place 0 openroad'",
                "api: chip.set('flowgraph', 'asicflow', 'place', '0', 'tool', 'openroad')"],
            help=trim("""Name of the tool name used for task execution.""")))

    # task (belonging to tool)
    schema.insert(
        'task',
        Parameter(
            'str',
            scope=Scope.GLOBAL,
            shorthelp="Flowgraph: task selection",
            switch="-flowgraph_task 'flow step index <str>'",
            example=[
                "cli: -flowgraph_task 'asicflow myplace 0 place'",
                "api: chip.set('flowgraph', 'asicflow', 'myplace', '0', 'task', 'place')"],
            help=trim("""Name of the tool associated task used for step execution.""")))

    schema.insert(
        'taskmodule',
        Parameter(
            'str',
            scope=Scope.GLOBAL,
            shorthelp="Flowgraph: task module",
            switch="-flowgraph_taskmodule 'flow step index <str>'",
            example=[
                "cli: -flowgraph_taskmodule 'asicflow place 0 "
                "siliconcompiler.tools.openroad.place'",
                "api: chip.set('flowgraph', 'asicflow', 'place', '0', 'taskmodule', "
                "'siliconcompiler.tools.openroad.place')"],
            help=trim("""
            Full python module name of the task module used for task setup and execution.
            """)))

    # flowgraph arguments
    schema.insert(
        'args',
        Parameter(
            '[str]',
            scope=Scope.GLOBAL,
            shorthelp="Flowgraph: setup arguments",
            switch="-flowgraph_args 'flow step index <str>'",
            example=[
                "cli: -flowgraph_args 'asicflow cts 0 0'",
                "api: chip.add('flowgraph', 'asicflow', 'cts', '0', 'args', '0')"],
            help=trim("""User specified flowgraph string arguments specified on a per
            step and per index basis.""")))
