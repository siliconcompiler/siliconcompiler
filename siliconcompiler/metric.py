import shutil

from typing import List, Tuple

from siliconcompiler.schema import BaseSchema
from siliconcompiler.schema import EditableSchema, Parameter, PerNode, Scope
from siliconcompiler.schema.utils import trim

from siliconcompiler.utils import truncate_text, units
from siliconcompiler.record import RecordTime


class MetricSchema(BaseSchema):
    def __init__(self):
        super().__init__()

        schema = EditableSchema(self)

        for item, description in [
                ('errors', 'errors'),
                ('warnings', 'warnings')]:
            schema.insert(
                item,
                Parameter(
                    'int',
                    scope=Scope.JOB,
                    shorthelp=f"Metric: total {item}",
                    switch=f"-metric_{item} 'step index <int>'",
                    example=[
                        f"cli: -metric_{item} 'dfm 0 0'",
                        f"api: chip.set('metric', '{item}', 0, step='dfm', index=0)"],
                    pernode=PerNode.REQUIRED,
                    help=trim(f"""Metric tracking the total number of {description} on a
                    per step and index basis.""")))

        schema.insert(
            'memory',
            Parameter(
                'float',
                unit='B',
                scope=Scope.JOB,
                shorthelp="Metric: memory",
                switch="-metric_memory 'step index <float>'",
                example=[
                    "cli: -metric_memory 'dfm 0 10e9'",
                    "api: chip.set('metric', 'memory', 10e9, step='dfm', index=0)"],
                pernode=PerNode.REQUIRED,
                help=trim("""
                Metric tracking total peak program memory footprint on a per
                step and index basis.""")))

        schema.insert(
            'exetime',
            Parameter(
                'float',
                unit='s',
                scope=Scope.JOB,
                shorthelp="Metric: exetime",
                switch="-metric_exetime 'step index <float>'",
                example=[
                    "cli: -metric_exetime 'dfm 0 10.0'",
                    "api: chip.set('metric', 'exetime', 10.0, step='dfm', index=0)"],
                pernode=PerNode.REQUIRED,
                help=trim("""
                Metric tracking time spent by the EDA executable :keypath:`tool,<tool>,exe` on a
                per step and index basis. It does not include the SiliconCompiler
                runtime overhead or time waiting for I/O operations and
                inter-processor communication to complete.""")))

        schema.insert(
            'tasktime',
            Parameter(
                'float',
                unit='s',
                scope=Scope.JOB,
                shorthelp="Metric: tasktime",
                switch="-metric_tasktime 'step index <float>'",
                example=[
                    "cli: -metric_tasktime 'dfm 0 10.0'",
                    "api: chip.set('metric', 'tasktime', 10.0, step='dfm', index=0)"],
                pernode=PerNode.REQUIRED,
                help=trim("""
                Metric tracking the total amount of time spent on a task from
                beginning to end, including data transfers and pre/post
                processing.""")))

        schema.insert(
            'totaltime',
            Parameter(
                'float',
                unit='s',
                scope=Scope.JOB,
                shorthelp="Metric: totaltime",
                switch="-metric_totaltime 'step index <float>'",
                example=[
                    "cli: -metric_totaltime 'dfm 0 10.0'",
                    "api: chip.set('metric', 'totaltime', 10.0, step='dfm', index=0)"],
                pernode=PerNode.REQUIRED,
                help=trim("""
                Metric tracking the total amount of time spent from the beginning
                of the run up to and including the current step and index.""")))

    def clear(self, step, index):
        '''
        Clear all saved metrics for a given step and index

        Args:
            step (str): Step name to clear.
            index (str/int): Index name to clear.
        '''
        for metric in self.getkeys():
            self.unset(metric, step=step, index=str(index))

    def record(self, step, index, metric, value, unit=None):
        """
        Record a metric

        Args:
            step (str): step to record
            index (str/int): index to record
            metric (str): name of metric
            value (int/float): value to record
            unit (str): unit associated with value
        """
        metric_unit = self.get(metric, field='unit')

        if not metric_unit and unit:
            raise ValueError(f"{metric} does not have a unit, but {unit} was supplied")

        if metric_unit:
            value = units.convert(value, from_unit=unit, to_unit=metric_unit)

        return self.set(metric, value, step=step, index=str(index))

    def record_tasktime(self, step, index, record):
        """
        Record the task time for this node

        Args:
            step (str): step to record
            index (str/int): index to record
            record (:class:`RecordSchema`): record to lookup data in
        """
        start_time, end_time = [
            record.get_recorded_time(step, index, RecordTime.START),
            record.get_recorded_time(step, index, RecordTime.END)
        ]

        if start_time is None or end_time is None:
            return False

        return self.record(step, index, "tasktime", end_time-start_time, unit="s")

    def record_totaltime(self, step, index, flow, record):
        """
        Record the total time for this node

        Args:
            step (str): step to record
            index (str/int): index to record
            flow (:class:`FlowgraphSchema`): flowgraph to lookup nodes in
            record (:class:`RecordSchema`): record to lookup data in
        """
        all_nodes = flow.get_nodes()
        node_times = [
            (record.get_recorded_time(*node, RecordTime.START),
             record.get_recorded_time(*node, RecordTime.END)) for node in all_nodes
        ]

        # Remove incomplete records
        node_times = [times for times in node_times if times[0] is not None]

        if len(node_times) == 0:
            return False

        node_end = record.get_recorded_time(step, index, RecordTime.END)
        if node_end is None:
            return False

        node_times = sorted(node_times)
        if len(node_times) > 1:
            new_times = []
            for n in range(len(node_times)):
                if not new_times:
                    new_times.append(node_times[n])
                    continue
                prev_start_time, prev_end_time = new_times[-1]
                start_time, end_time = node_times[n]

                new_start = min(prev_start_time, start_time)

                if prev_end_time is None:
                    new_times[-1] = (new_start, end_time)
                elif prev_end_time >= start_time:
                    if end_time is not None:
                        new_end = max(prev_end_time, end_time)
                    else:
                        new_end = prev_end_time
                    new_times[-1] = (new_start, new_end)
                else:
                    new_times.append(node_times[n])
            node_times = new_times

        total_time = 0
        for start_time, end_time in node_times:
            if start_time > node_end:
                continue
            total_time += min(end_time, node_end) - start_time

        return self.record(step, index, "totaltime", total_time, unit="s")

    def get_formatted_metric(self, metric: str, step: str, index: str) -> str:
        if metric == 'memory':
            return units.format_binary(self.get(metric, step=step, index=index),
                                       self.get(metric, field="unit"))
        elif metric in ['exetime', 'tasktime', 'totaltime']:
            return units.format_time(self.get(metric, step=step, index=index))
        elif self.get(metric, field="type") == 'int':
            return str(self.get(metric, step=step, index=index))
        else:
            return units.format_si(self.get(metric, step=step, index=index),
                                   self.get(metric, field="unit"))

    def summary_table(self,
                      nodes: List[Tuple[str, str]] = None,
                      column_width: int = 15,
                      formatted: bool = True,
                      trim_empty_metrics: bool = True):
        from pandas import DataFrame

        if not nodes:
            nodes = set()
            for metric in self.getkeys():
                for value, step, index in self.get(metric, field=None).getvalues():
                    nodes.add((step, index))
            nodes = list(sorted(nodes))

        row_labels = list(self.getkeys())
        sort_map = {metric: 0 for metric in row_labels}
        sort_map["errors"] = -2
        sort_map["warnings"] = -1
        sort_map["memory"] = 1
        sort_map["exetime"] = 2
        sort_map["tasktime"] = 3
        sort_map["totaltime"] = 4
        row_labels = sorted(row_labels, key=lambda row: sort_map[row])

        if trim_empty_metrics:
            for metric in self.getkeys():
                data = []
                for step, index in nodes:
                    data.append(self.get(metric, step=step, index=index))
                if all([dat is None for dat in data]):
                    row_labels.remove(metric)

        if 'totaltime' in row_labels:
            if not any([self.get('totaltime', step=step, index=index) is None
                        for step, index in nodes]):
                nodes.sort(
                    key=lambda node: self.get('totaltime', step=node[0], index=node[1]))

        # trim labels to column width
        column_labels = ["unit"]
        labels = [f'{step}/{index}' for step, index in nodes]
        if labels:
            column_width = min([column_width, max([len(label) for label in labels])])

        for label in labels:
            column_labels.append(truncate_text(label, column_width).center(column_width))

        if formatted:
            none_value = "---".center(column_width)
        else:
            none_value = None

        data = []
        for metric in row_labels:
            row = [self.get(metric, field="unit") or ""]
            for step, index in nodes:
                value = self.get(metric, step=step, index=index)
                if value is None:
                    value = none_value
                else:
                    if formatted:
                        value = self.get_formatted_metric(metric, step=step, index=index)
                        value = value.center(column_width)
                    else:
                        value = self.get(metric, step=step, index=index)
                row.append(value)
            data.append(row)

        return DataFrame(data, row_labels, column_labels)

    def summary(self,
                headers: List[Tuple[str, str]],
                nodes: List[Tuple[str, str]] = None,
                column_width: int = 15) -> None:
        header = []
        headers.insert(0, ("SUMMARY", None))
        if headers:
            max_header = max([len(title) for title, _ in headers])
            for title, value in headers:
                if value is None:
                    header.append(f"{title:<{max_header}} :")
                else:
                    header.append(f"{title:<{max_header}} : {value}")

        max_line_width = max(4 * column_width, int(0.95*shutil.get_terminal_size().columns))
        data = self.summary_table(nodes=nodes, column_width=column_width)

        print("-" * max_line_width)
        print("\n".join(header))
        print()
        if data.empty:
            print("  No metrics to display!")
        else:
            print(data.to_string(line_width=max_line_width, col_space=3))
        print("-" * max_line_width)

    @classmethod
    def _getdict_type(cls) -> str:
        """
        Returns the meta data for getdict
        """

        return MetricSchema.__name__


class MetricSchemaTmp(MetricSchema):
    def __init__(self):
        super().__init__()

        schema_metric_tmp(self)


###########################################################################
# Metrics to Track
###########################################################################
def schema_metric_tmp(schema):
    schema = EditableSchema(schema)

    metrics = {'drvs': 'design rule violations',
               'drcs': 'physical design rule violations',
               'unconstrained': 'unconstrained timing paths'}

    for item, description in metrics.items():
        schema.insert(
            item,
            Parameter(
                'int',
                scope=Scope.JOB,
                shorthelp=f"Metric: total {item}",
                switch=f"-metric_{item} 'step index <int>'",
                example=[
                    f"cli: -metric_{item} 'dfm 0 0'",
                    f"api: chip.set('metric', '{item}', 0, step='dfm', index=0)"],
                pernode=PerNode.REQUIRED,
                help=trim(f"""Metric tracking the total number of {description} on a
                per step and index basis.""")))

    schema.insert(
        'coverage',
        Parameter(
            'float',
            unit='%',
            scope=Scope.JOB,
            shorthelp="Metric: coverage",
            switch="-metric_coverage 'step index <float>'",
            example=[
                "cli: -metric_coverage 'place 0 99.9'",
                "api: chip.set('metric', 'coverage', 99.9, step='place', index=0)"],
            pernode=PerNode.REQUIRED,
            help=trim("""
            Metric tracking the test coverage in the design expressed as a percentage
            with 100 meaning full coverage. The meaning of the metric depends on the
            task being executed. It can refer to code coverage, feature coverage,
            stuck at fault coverage.""")))

    schema.insert(
        'security',
        Parameter(
            'float',
            unit='%',
            scope=Scope.JOB,
            shorthelp="Metric: security",
            switch="-metric_security 'step index <float>'",
            example=[
                "cli: -metric_security 'place 0 100'",
                "api: chip.set('metric', 'security', 100, step='place', index=0)"],
            pernode=PerNode.REQUIRED,
            help=trim("""
            Metric tracking the level of security (1/vulnerability) of the design.
            A completely secure design would have a score of 100. There is no
            absolute scale for the security metrics (like with power, area, etc)
            so the metric will be task and tool dependent.""")))

    metrics = {'luts': 'FPGA LUTs used',
               'dsps': 'FPGA DSP slices used',
               'brams': 'FPGA BRAM tiles used'}

    for item, description in metrics.items():
        schema.insert(
            item,
            Parameter(
                'int',
                scope=Scope.JOB,
                shorthelp=f"Metric: {description}",
                switch=f"-metric_{item} 'step index <int>'",
                example=[
                    f"cli: -metric_{item} 'place 0 100'",
                    f"api: chip.set('metric', '{item}', 100, step='place', index=0)"],
                pernode=PerNode.REQUIRED,
                help=trim(f"""
                Metric tracking the total {description} used by the design as reported
                by the implementation tool. There is no standardized definition
                for this metric across vendors, so metric comparisons can
                generally only be done between runs on identical tools and
                device families.""")))

    metrics = {'cellarea': 'cell area (ignoring fillers)',
               'totalarea': 'physical die area',
               'macroarea': 'macro cell area',
               'padcellarea': 'io pad cell area',
               'stdcellarea': 'standard cell area'}

    for item, description in metrics.items():
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
                    f"api: chip.set('metric', '{item}', 100.00, step='place', index=0)"],
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
                "api: chip.set('metric', 'utilization', 50.00, step='place', index=0)"],
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
                "api: chip.set('metric', 'logicdepth', 8, step='place', index=0)"],
            pernode=PerNode.REQUIRED,
            help=trim("""
            Metric tracking the logic depth of the design. This is determined
            by the number of logic gates between the start of the critital timing
            path to the end of the path.""")))

    metrics = {'peakpower': 'worst case total peak power',
               'averagepower': 'average workload power',
               'leakagepower': 'leakage power with rails active but without any dynamic '
                               'switching activity'}

    for item, description in metrics.items():
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
                    f"api: chip.set('metric', '{item}', 0.01, step='place', index=0)"],
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
                "api: chip.set('metric', 'irdrop', 0.05, step='place', index=0)"],
            pernode=PerNode.REQUIRED,
            help=trim("""
            Metric tracking the peak IR drop in the design based on extracted
            power and ground rail parasitics, library power models, and
            switching activity. The switching activity calculated on a per
            node basis is taken from one of three possible sources, in order
            of priority: VCD file, SAIF file, 'activityfactor' parameter.""")))

    metrics = {'holdpaths': 'hold',
               'setuppaths': 'setup'}

    for item, description in metrics.items():
        schema.insert(
            item,
            Parameter(
                'int',
                scope=Scope.JOB,
                shorthelp=f"Metric: {item}",
                switch=f"-metric_{item} 'step index <int>'",
                example=[
                    f"cli: -metric_{item} 'place 0 10'",
                    f"api: chip.set('metric', '{item}', 10, step='place', index=0)"],
                pernode=PerNode.REQUIRED,
                help=trim(f"""
                Metric tracking the total number of timing paths violating {description}
                constraints.""")))

    metrics = {'holdslack': 'worst hold slack (positive or negative)',
               'holdwns': 'worst negative hold slack (positive values truncated to zero)',
               'holdtns': 'total negative hold slack (TNS)',
               'holdskew': 'hold clock skew',
               'setupslack': 'worst setup slack (positive or negative)',
               'setupwns': 'worst negative setup slack (positive values truncated to zero)',
               'setuptns': 'total negative setup slack (TNS)',
               'setupskew': 'setup clock skew'}

    for item, description in metrics.items():
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
                    f"api: chip.set('metric', '{item}', 0.01, step='place', index=0)"],
                pernode=PerNode.REQUIRED,
                help=trim(f"""
                Metric tracking the {description} on a per step and index basis.""")))

    metrics = {'fmax': 'maximum clock frequency'}

    for item, description in metrics.items():
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
                    f"api: chip.set('metric', '{item}', 100e6, step='place', index=0)"],
                pernode=PerNode.REQUIRED,
                help=trim(f"""
                Metric tracking the {description} on a per step and index basis.""")))

    metrics = {'macros': 'macros',
               'cells': 'cell instances',
               'registers': 'register instances',
               'buffers': 'buffer instances',
               'inverters': 'inverter instances',
               'transistors': 'transistors',
               'pins': 'pins',
               'nets': 'nets',
               'vias': 'vias'}

    for item, description in metrics.items():
        schema.insert(
            item,
            Parameter(
                'int',
                scope=Scope.JOB,
                shorthelp=f"Metric: {item}",
                switch=f"-metric_{item} 'step index <int>'",
                example=[
                    f"cli: -metric_{item} 'place 0 100'",
                    f"api: chip.set('metric', '{item}', 50, step='place', index=0)"],
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
                "api: chip.set('metric', 'wirelength', 50.0, step='place', index=0)"],
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
                "api: chip.set('metric', 'overflow', 50, step='place', index=0)"],
            pernode=PerNode.REQUIRED,
            help=trim("""
            Metric tracking the total number of overflow tracks for the routing
            on per step and index basis. Any non-zero number suggests an over
            congested design. To analyze where the congestion is occurring
            inspect the router log files for detailed per metal overflow
            reporting and open up the design to find routing hotspots.""")))
