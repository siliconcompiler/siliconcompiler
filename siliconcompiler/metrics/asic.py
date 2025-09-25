from siliconcompiler.schema_support.metric import MetricSchema

from siliconcompiler.schema import EditableSchema, Parameter, Scope, PerNode
from siliconcompiler.schema.utils import trim


class ASICMetricsSchema(MetricSchema):
    def __init__(self):
        super().__init__()

        schema = EditableSchema(self)

        for item, description in [
                ('drvs', 'design rule violations'),
                ('drcs', 'physical design rule violations'),
                ('unconstrained', 'unconstrained timing paths')]:
            schema.insert(
                item,
                Parameter(
                    'int',
                    scope=Scope.JOB,
                    shorthelp=f"Metric: total {item}",
                    switch=f"-metric_{item} 'step index <int>'",
                    example=[
                        f"cli: -metric_{item} 'dfm 0 0'",
                        f"api: asic.set('metric', '{item}', 0, step='dfm', index=0)"],
                    pernode=PerNode.REQUIRED,
                    help=trim(f"""Metric tracking the total number of {description} on a
                    per step and index basis.""")))

        for item, description in [
                ('cellarea', 'cell area (ignoring fillers)'),
                ('totalarea', 'physical die area'),
                ('macroarea', 'macro cell area'),
                ('padcellarea', 'io pad cell area'),
                ('stdcellarea', 'standard cell area')]:
            schema.insert(
                item,
                Parameter(
                    'float',
                    unit='um^2',
                    scope=Scope.JOB,
                    shorthelp=f"Metric: {item}",
                    switch=f"-metric_{item} 'step index <float>'",
                    example=[
                        f"cli: -metric_{item} 'place 0 100.00'",
                        f"api: asic.set('metric', '{item}', 100.00, step='place', index=0)"],
                    pernode=PerNode.REQUIRED,
                    help=trim(f"""
                    Metric tracking the total {description} occupied by the design.""")))

        schema.insert(
            'utilization',
            Parameter(
                'float',
                unit='%',
                scope=Scope.JOB,
                shorthelp="Metric: area utilization",
                switch="-metric_utilization 'step index <float>'",
                example=[
                    "cli: -metric_utilization 'place 0 50.00'",
                    "api: asic.set('metric', 'utilization', 50.00, step='place', index=0)"],
                pernode=PerNode.REQUIRED,
                help=trim("""
                Metric tracking the area utilization of the design calculated as
                100 * (cellarea/totalarea).""")))

        schema.insert(
            'logicdepth',
            Parameter(
                'int',
                scope=Scope.JOB,
                shorthelp="Metric: logic depth",
                switch="-metric_logicdepth 'step index <int>'",
                example=[
                    "cli: -metric_logicdepth 'place 0 8'",
                    "api: asic.set('metric', 'logicdepth', 8, step='place', index=0)"],
                pernode=PerNode.REQUIRED,
                help=trim("""
                Metric tracking the logic depth of the design. This is determined
                by the number of logic gates between the start of the critital timing
                path to the end of the path.""")))

        for item, description in [
                ('peakpower', 'worst case total peak power'),
                ('averagepower', 'average workload power'),
                ('leakagepower', 'leakage power with rails active but without any dynamic '
                                 'switching activity')]:
            schema.insert(
                item,
                Parameter(
                    'float',
                    unit='mw',
                    scope=Scope.JOB,
                    shorthelp=f"Metric: {item}",
                    switch=f"-metric_{item} 'step index <float>'",
                    example=[
                        f"cli: -metric_{item} 'place 0 0.01'",
                        f"api: asic.set('metric', '{item}', 0.01, step='place', index=0)"],
                    pernode=PerNode.REQUIRED,
                    help=trim(f"""
                    Metric tracking the {description} of the design specified on a per step
                    and index basis. Power metric depend heavily on the method
                    being used for extraction: dynamic vs static, workload
                    specification (vcd vs saif), power models, process/voltage/temperature.
                    The power {item} metric tries to capture the data that would
                    usually be reflected inside a datasheet given the appropriate
                    footnote conditions.""")))

        schema.insert(
            'irdrop',
            Parameter(
                'float',
                unit='mv',
                scope=Scope.JOB,
                shorthelp="Metric: peak IR drop",
                switch="-metric_irdrop 'step index <float>'",
                example=[
                    "cli: -metric_irdrop 'place 0 0.05'",
                    "api: asic.set('metric', 'irdrop', 0.05, step='place', index=0)"],
                pernode=PerNode.REQUIRED,
                help=trim("""
                Metric tracking the peak IR drop in the design based on extracted
                power and ground rail parasitics, library power models, and
                switching activity. The switching activity calculated on a per
                node basis is taken from one of three possible sources, in order
                of priority: VCD file, SAIF file, 'activityfactor' parameter.""")))

        for item, description in [
                ('holdpaths', 'hold'),
                ('setuppaths', 'setup')]:
            schema.insert(
                item,
                Parameter(
                    'int',
                    scope=Scope.JOB,
                    shorthelp=f"Metric: {item}",
                    switch=f"-metric_{item} 'step index <int>'",
                    example=[
                        f"cli: -metric_{item} 'place 0 10'",
                        f"api: asic.set('metric', '{item}', 10, step='place', index=0)"],
                    pernode=PerNode.REQUIRED,
                    help=trim(f"""
                    Metric tracking the total number of timing paths violating {description}
                    constraints.""")))

        for item, description in [
                ('holdslack', 'worst hold slack (positive or negative)'),
                ('holdwns', 'worst negative hold slack (positive values truncated to zero)'),
                ('holdtns', 'total negative hold slack (TNS)'),
                ('holdskew', 'hold clock skew'),
                ('setupslack', 'worst setup slack (positive or negative)'),
                ('setupwns', 'worst negative setup slack (positive values truncated to zero)'),
                ('setuptns', 'total negative setup slack (TNS)'),
                ('setupskew', 'setup clock skew')]:
            schema.insert(
                item,
                Parameter(
                    'float',
                    unit='ns',
                    scope=Scope.JOB,
                    shorthelp=f"Metric: {item}",
                    switch=f"-metric_{item} 'step index <float>'",
                    example=[
                        f"cli: -metric_{item} 'place 0 0.01'",
                        f"api: asic.set('metric', '{item}', 0.01, step='place', index=0)"],
                    pernode=PerNode.REQUIRED,
                    help=trim(f"""
                    Metric tracking the {description} on a per step and index basis.""")))

        for item, description in [
                ('fmax', 'maximum clock frequency')]:
            schema.insert(
                item,
                Parameter(
                    'float',
                    unit='Hz',
                    scope=Scope.JOB,
                    shorthelp=f"Metric: {item}",
                    switch=f"-metric_{item} 'step index <float>'",
                    example=[
                        f"cli: -metric_{item} 'place 0 100e6'",
                        f"api: asic.set('metric', '{item}', 100e6, step='place', index=0)"],
                    pernode=PerNode.REQUIRED,
                    help=trim(f"""
                    Metric tracking the {description} on a per step and index basis.""")))

        for item, description in [
                ('macros', 'macros'),
                ('cells', 'cell instances'),
                ('registers', 'register instances'),
                ('buffers', 'buffer instances'),
                ('inverters', 'inverter instances'),
                ('transistors', 'transistors'),
                ('pins', 'pins'),
                ('nets', 'nets'),
                ('vias', 'vias')]:
            schema.insert(
                item,
                Parameter(
                    'int',
                    scope=Scope.JOB,
                    shorthelp=f"Metric: {item}",
                    switch=f"-metric_{item} 'step index <int>'",
                    example=[
                        f"cli: -metric_{item} 'place 0 100'",
                        f"api: asic.set('metric', '{item}', 50, step='place', index=0)"],
                    pernode=PerNode.REQUIRED,
                    help=trim(f"""
                    Metric tracking the total number of {description} in the design
                    on a per step and index basis.""")))

        schema.insert(
            'wirelength',
            Parameter(
                'float',
                unit='um',
                scope=Scope.JOB,
                shorthelp="Metric: wirelength",
                switch="-metric_wirelength 'step index <float>'",
                example=[
                    "cli: -metric_wirelength 'place 0 100.0'",
                    "api: asic.set('metric', 'wirelength', 50.0, step='place', index=0)"],
                pernode=PerNode.REQUIRED,
                help=trim("""
                Metric tracking the total wirelength of the design on a per step
                and index basis.""")))

        schema.insert(
            'overflow',
            Parameter(
                'int',
                scope=Scope.JOB,
                shorthelp="Metric: overflow",
                switch="-metric_overflow 'step index <int>'",
                example=[
                    "cli: -metric_overflow 'place 0 0'",
                    "api: asic.set('metric', 'overflow', 50, step='place', index=0)"],
                pernode=PerNode.REQUIRED,
                help=trim("""
                Metric tracking the total number of overflow tracks for the routing
                on per step and index basis. Any non-zero number suggests an over
                congested design. To analyze where the congestion is occurring
                inspect the router log files for detailed per metal overflow
                reporting and open up the design to find routing hotspots.""")))
