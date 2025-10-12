import shutil
import sys

from typing import List, Tuple, TextIO, Union, Optional, TYPE_CHECKING

from siliconcompiler.schema import BaseSchema
from siliconcompiler.schema import EditableSchema, Parameter, PerNode, Scope
from siliconcompiler.schema.utils import trim

from siliconcompiler.utils import truncate_text, units
from siliconcompiler.schema_support.record import RecordTime, RecordSchema


if TYPE_CHECKING:
    from pandas import DataFrame
    from siliconcompiler import Flowgraph


class MetricSchema(BaseSchema):
    '''
    Schema for storing and accessing metrics collected during a run.

    This class provides a structured way to define, record, and report
    various metrics such as runtime, memory usage, and design quality
    indicators for each step of a compilation flow.
    '''

    def __init__(self):
        '''Initializes the MetricSchema.'''
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
                        f"api: project.set('metric', '{item}', 0, step='dfm', index=0)"],
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
                    "api: project.set('metric', 'memory', 10e9, step='dfm', index=0)"],
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
                    "api: project.set('metric', 'exetime', 10.0, step='dfm', index=0)"],
                pernode=PerNode.REQUIRED,
                help=trim("""
                Metric tracking time spent by the EDA executable
                :keypath:`tool,<tool>,task,<task>,exe` on a
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
                    "api: project.set('metric', 'tasktime', 10.0, step='dfm', index=0)"],
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
                    "api: project.set('metric', 'totaltime', 10.0, step='dfm', index=0)"],
                pernode=PerNode.REQUIRED,
                help=trim("""
                Metric tracking the total amount of time spent from the beginning
                of the run up to and including the current step and index.""")))

    def clear(self, step: str, index: Union[int, str]) -> None:
        '''
        Clears all saved metrics for a given step and index.

        Args:
            step (str): The step name to clear metrics for.
            index (str or int): The index to clear metrics for.
        '''
        for metric in self.getkeys():
            self.unset(metric, step=step, index=str(index))

    def record(self,
               step: str, index: Union[str, int],
               metric: str,
               value: Union[float, int],
               unit: Optional[str] = None):
        """
        Records a metric value for a specific step and index.

        This method handles unit conversion if the metric is defined with a
        unit in the schema.

        Args:
            step (str): The step to record the metric for.
            index (str or int): The index to record the metric for.
            metric (str): The name of the metric to record.
            value (int or float): The value of the metric.
            unit (str, optional): The unit of the provided value. If the schema
                defines a unit for this metric, the value will be converted.
                Defaults to None.

        Returns:
            The recorded value after any unit conversion.
        """
        metric_unit: Optional[str] = self.get(metric, field='unit')

        if not metric_unit and unit:
            raise ValueError(f"{metric} does not have a unit, but {unit} was supplied")

        if metric_unit:
            value = units.convert(value, from_unit=unit, to_unit=metric_unit)

        return self.set(metric, value, step=step, index=str(index))

    def record_tasktime(self, step: str, index: Union[str, int], record: RecordSchema):
        """
        Records the task time for a given node based on start and end times.

        Args:
            step (str): The step of the node.
            index (str or int): The index of the node.
            record (RecordSchema): The record schema containing timing data.

        Returns:
            bool: True if the time was successfully recorded, False otherwise.
        """
        start_time, end_time = [
            record.get_recorded_time(step, index, RecordTime.START),
            record.get_recorded_time(step, index, RecordTime.END)
        ]

        if start_time is None or end_time is None:
            return False

        return self.record(step, index, "tasktime", end_time-start_time, unit="s")

    def record_totaltime(self,
                         step: str, index: Union[str, int],
                         flow: "Flowgraph",
                         record: RecordSchema):
        """
        Records the cumulative total time up to the end of a given node.

        This method calculates the total wall-clock time by summing the
        durations of all previously executed parallel tasks.

        Args:
            step (str): The step of the node.
            index (str or int): The index of the node.
            flow (Flowgraph): The flowgraph containing the nodes.
            record (RecordSchema): The record schema containing timing data.

        Returns:
            bool: True if the time was successfully recorded, False otherwise.
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

    def get_formatted_metric(self, metric: str, step: str, index: Union[int, str]) -> str:
        '''
        Retrieves and formats a metric for display.

        Handles special formatting for memory (binary units), time, and adds
        SI suffixes for other float values.

        Args:
            metric (str): The name of the metric to format.
            step (str): The step of the metric.
            index (str): The index of the metric.

        Returns:
            str: The formatted, human-readable metric value as a string.
        '''
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
                      nodes: Optional[List[Tuple[str, str]]] = None,
                      column_width: int = 15,
                      formatted: bool = True,
                      trim_empty_metrics: bool = True) -> "DataFrame":
        '''
        Generates a summary of metrics as a pandas DataFrame.

        Args:
            nodes (List[Tuple[str, str]], optional): A list of (step, index)
                tuples to include in the summary. If None, all nodes with
                metrics are included. Defaults to None.
            column_width (int, optional): The width for each column.
                Defaults to 15.
            formatted (bool, optional): If True, metric values are formatted
                for human readability. Defaults to True.
            trim_empty_metrics (bool, optional): If True, metrics that have no
                value for any of the specified nodes are excluded.
                Defaults to True.

        Returns:
            pandas.DataFrame: A DataFrame containing the metric summary.
        '''
        from pandas import DataFrame

        if not nodes:
            unique_nodes = set()
            for metric in self.getkeys():
                for _, step, index in self.get(metric, field=None).getvalues():
                    unique_nodes.add((step, index))
            nodes = list(sorted(unique_nodes))

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
                headers: List[Tuple[str, Optional[str]]],
                nodes: Optional[List[Tuple[str, str]]] = None,
                column_width: int = 15,
                fd: Optional[TextIO] = None) -> None:
        '''
        Prints a formatted summary of metrics to a file descriptor.

        Args:
            headers (List[Tuple[str, str]]): A list of (title, value) tuples
                to print in the header section of the summary.
            nodes (List[Tuple[str, str]], optional): A list of (step, index)
                tuples to include. Defaults to all nodes.
            column_width (int, optional): The width for each column in the table.
                Defaults to 15.
            fd (TextIO, optional): The file descriptor to write to.
                Defaults to `sys.stdout`.
        '''
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

        if not fd:
            fd = sys.stdout

        print("-" * max_line_width, file=fd)
        print("\n".join(header), file=fd)
        print(file=fd)
        if data.empty:
            print("  No metrics to display!", file=fd)
        else:
            print(data.to_string(line_width=max_line_width, col_space=3), file=fd)
        print("-" * max_line_width, file=fd)

    @classmethod
    def _getdict_type(cls) -> str:
        """
        Returns the metadata type for `getdict` serialization.
        """

        return MetricSchema.__name__
