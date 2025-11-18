import re
import os.path
from pathlib import Path
from typing import Tuple, List, Optional, Union, Dict, Iterable

from siliconcompiler.schema import NamedSchema, EditableSchema, Parameter, Scope, BaseSchema
from siliconcompiler.schema.utils import trim
from siliconcompiler import NodeStatus, utils
from siliconcompiler.utils.paths import cwdirsafe


class Criteria(NamedSchema):
    """
    Schema for defining a single checklist item's criteria.

    This class holds all the configurable parameters for a specific checklist
    item, such as its description, requirements, validation criteria,
    and associated reports or waivers.
    """

    def __init__(self, name: Optional[str] = None):
        super().__init__()
        self.set_name(name)
        schema_checklist(self)

    def get_description(self) -> Optional[str]:
        """
        Retrieves the short, one-line description of the checklist item.

        Returns:
            Optional[str]: The description string, or None if not set.
        """
        return self.get('description')

    def set_description(self, value: Optional[str]) -> None:
        """
        Sets the short, one-line description for the checklist item.

        Args:
            value (Optional[str]): The description string to set.
        """
        self.set('description', value)

    def get_requirement(self) -> Optional[str]:
        """
        Retrieves the detailed requirement description for the checklist item.

        Returns:
            Optional[str]: The requirement description, which can be a
            multi-line string, or None if not set.
        """
        return self.get('requirement')

    def set_requirement(self, value: Optional[str]) -> None:
        """
        Sets the detailed requirement description for the checklist item.

        Args:
            value (Optional[str]): The requirement description to set.
        """
        self.set('requirement', value)

    def get_dataformat(self) -> Optional[str]:
        """
        Retrieves the description of acceptable data file formats.

        Returns:
            Optional[str]: A free-text description of the data format,
            or None if not set.
        """
        return self.get('dataformat')

    def set_dataformat(self, value: Optional[str]):
        """
        Sets the description of acceptable data file formats for signoff.

        Args:
            value (Optional[str]): A free-text description of the data format.
        """
        self.set('dataformat', value)

    def get_rationale(self) -> List[str]:
        """
        Retrieves the rationale codes or descriptions for the checklist item.

        Returns:
            List[str]: A list of rationale strings.
        """
        return self.get('rationale')

    def add_rationale(self, value: Union[List[str], str], clobber: bool = False) -> None:
        """
        Adds one or more rationale codes or descriptions to the checklist item.

        Args:
            value (Union[List[str], str]): A single rationale string or a list of strings.
            clobber (bool): If True, replaces the existing list with the new value.
                If False, appends to the existing list. Defaults to False.
        """
        if clobber:
            self.set('rationale', value)
        else:
            self.add('rationale', value)

    def get_criteria(self) -> List[str]:
        """
        Retrieves the list of signoff criteria.

        Each criterion is a string in the format 'metric op value'
        (e.g., 'errors == 0').

        Returns:
            List[str]: A list of criteria strings.
        """
        return self.get('criteria')

    def add_criteria(self, value: Union[List[str], str], clobber: bool = False) -> None:
        """
        Adds one or more signoff criteria to the checklist item.

        Args:
            value (Union[List[str], str]): A single criterion string or a list of strings.
            clobber (bool): If True, replaces the existing list with the new value.
                If False, appends to the existing list. Defaults to False.
        """
        if clobber:
            self.set('criteria', value)
        else:
            self.add('criteria', value)

    def get_task(self) -> List[Tuple[str, str, str]]:
        """
        Retrieves the flowgraph tasks used to verify this checklist item.

        Each task is represented as a tuple of (job, step, index).

        Returns:
            List[Tuple[str, str, str]]: A list of task tuples.
        """
        return self.get('task')

    def add_task(self, value: Union[List[Tuple[str, str, str]], Tuple[str, str, str]],
                 clobber: bool = False) -> None:
        """
        Adds one or more flowgraph tasks to verify the checklist item.

        Args:
            value (Union[List[Tuple], Tuple]): A single task tuple or a list of tuples.
            clobber (bool): If True, replaces the existing list with the new value.
                If False, appends to the existing list. Defaults to False.
        """
        if clobber:
            self.set('task', value)
        else:
            self.add('task', value)

    def get_report(self) -> List[str]:
        """
        Retrieves the list of report filepaths documenting validation.

        Returns:
            List[str]: A list of filepaths.
        """
        return self.get('report')

    def add_report(self, value: Union[List[str], str], clobber: bool = False) -> None:
        """
        Adds one or more report filepaths to the checklist item.

        Args:
            value (Union[List[str], str]): A single filepath string or a list of strings.
            clobber (bool): If True, replaces the existing list with the new value.
                If False, appends to the existing list. Defaults to False.
        """
        if clobber:
            self.set('report', value)
        else:
            self.add('report', value)

    def get_waiver(self, metric: str) -> List[Union[Path, str]]:
        """
        Retrieves waiver report files for a specific metric.

        Args:
            metric (str): The metric for which to retrieve waivers.

        Returns:
            List[Union[Path, str]]: A list of filepaths for the specified metric's waivers.
        """
        return self.get('waiver', metric)

    def add_waiver(self, metric: str, value: Union[List[Union[Path, str]], Union[Path, str]],
                   clobber: bool = False) -> None:
        """
        Adds one or more waiver reports for a specific metric.

        Args:
            metric (str): The metric to which the waiver applies.
            value (Union[List, Path, str]): A single filepath or a list of filepaths.
            clobber (bool): If True, replaces the existing list with the new value.
                If False, appends to the existing list. Defaults to False.
        """
        if clobber:
            self.set('waiver', metric, value)
        else:
            self.add('waiver', metric, value)

    def get_ok(self) -> bool:
        """
        Retrieves the manual 'ok' status of the checklist item.

        A value of True indicates a human has reviewed and approved the item.

        Returns:
            bool: The boolean status, or False if not set.
        """
        return self.get('ok')

    def set_ok(self, value: bool) -> None:
        """
        Sets the manual 'ok' status of the checklist item.

        Args:
            value (bool): The boolean status to set. True indicates approval.
        """
        self.set('ok', value)

    @classmethod
    def _getdict_type(cls) -> str:
        """
        Internal method to return the type name for dictionary representation.
        """
        return Criteria.__name__


class Checklist(NamedSchema):
    """
    A class for managing a collection of design checklist items and their verification.

    This class acts as a container for multiple `Criteria` objects, each
    representing an item in a design checklist (e.g., 'ISO D000'). It provides
    methods to define, access, and automatically verify these items against
    flow results.
    """
    def __init__(self, name: Optional[str] = None):
        """
        Initializes the Checklist object.

        Args:
            name (str, optional): The name of the checklist standard. Defaults to None.
        """
        super().__init__()
        self.set_name(name)
        EditableSchema(self).insert("default", Criteria())

    def make_criteria(self, name: str) -> Criteria:
        """
        Creates a new, named `Criteria` item within this checklist.

        Args:
            name (str): The unique name for the new checklist item.

        Returns:
            Criteria: The newly created `Criteria` object.

        Raises:
            ValueError: If a criteria item with the same name already exists.
        """
        if name in self.getkeys():
            raise ValueError(f"{name} has already been defined")
        return self.get(name, field="schema")

    def get_criteria(self, name: Optional[str] = None) -> Union[Dict[str, Criteria], Criteria]:
        """
        Retrieves one or all `Criteria` items from the checklist.

        If a name is provided, it returns the specific `Criteria` object.
        If no name is provided, it returns a dictionary of all `Criteria` objects.

        Args:
            name (Optional[str], optional): The name of the item to retrieve.
                Defaults to None.

        Returns:
            Union[Dict[str, Criteria], Criteria]: A single `Criteria` object
            or a dictionary mapping names to `Criteria` objects.

        Raises:
            ValueError: If a name is provided but is not found in the checklist.
        """
        if name is None:
            criteria: Dict[str, Criteria] = {}
            for item in self.getkeys():
                criteria[item] = self.get_criteria(item)
            return criteria
        if name not in self.getkeys():
            raise ValueError(f"{name} is not defined")
        return self.get(name, field="schema")

    def check(self, items: Optional[Iterable[str]] = None,
              check_ok: bool = False,
              require_reports: bool = True) -> bool:
        """
        Checks the status of items in a checklist against flow results.

        This method validates checklist items by comparing their defined
        criteria against metrics recorded in the chip's history. For an item
        to pass, all its criteria must be met by the associated tasks,
        considering any waivers.

        For items with automated checks (linked to a task), this method verifies
        that metric values from the flow run satisfy the criteria (e.g., 'errors == 0').
        It also ensures that corresponding EDA reports were generated.

        For items without a task, it only checks that a report has been manually added.

        Args:
            items (Optional[Iterable[str]]): A list of item names to check. If None,
                all items in the checklist are checked. Defaults to None.
            check_ok (bool): If True, all checked items must also have their 'ok'
                parameter set to True, indicating manual review. Defaults to False.
            require_reports (bool): If True, asserts that report files exist for
                all automated checks. Defaults to True.

        Returns:
            bool: True if all specified checks pass, False otherwise.
        """
        error = False

        schema_root = self._parent(root=True)
        logger = getattr(schema_root, "logger", None)
        cwd = cwdirsafe(schema_root)

        assert hasattr(schema_root, "history"), f"{schema_root}"

        if logger:
            logger.info(f'Checking checklist {self.name}')

        if items is None:
            items = self.getkeys()

        # These metrics are recorded by SC internally, so they don't have reports.
        metrics_without_reports = (
            'tasktime',
            'totaltime',
            'exetime',
            'memory')

        for item in items:
            if item not in self.getkeys():
                if logger:
                    logger.error(f'{item} is not a check in {self.name}.')
                error = True
                continue

            allow_missing_reports = True
            has_check = False
            item_criteria: Criteria = self.get_criteria(item)

            for criteria in item_criteria.get_criteria():
                m = re.match(r'^(\w+)\s*([\>\=\<]+)\s*([+\-]?\d+(\.\d+)?(e[+\-]?\d+)?)$',
                             criteria.strip())
                if not m:
                    raise ValueError(f"Illegal checklist criteria: {criteria}")

                metric = m.group(1)
                op = m.group(2)

                if metric not in metrics_without_reports:
                    allow_missing_reports = False

                for job, step, index in item_criteria.get_task():
                    job_data = schema_root.history(job)
                    flow = job_data.get("flowgraph", job_data.get('option', 'flow'), field="schema")

                    if (step, index) not in flow.get_nodes():
                        error = True
                        if logger:
                            logger.error(f'{step}/{index} not found in flowgraph for {job}')
                        continue

                    if job_data.get('record', 'status', step=step, index=index) == \
                            NodeStatus.SKIPPED:
                        if logger:
                            logger.warning(f'{step}/{index} was skipped')
                        continue

                    has_check = True

                    # Automated checks
                    tool = flow.get(step, index, 'tool')
                    task = flow.get(step, index, 'task')

                    if metric not in job_data.getkeys("metric"):
                        if logger:
                            logger.error(f"Criteria must use legal metrics only: {criteria}")
                        error = True
                        continue

                    if job_data.get("metric", metric, field='type') == 'int':
                        goal = int(m.group(3))
                        number_format = 'd'
                    else:
                        goal = float(m.group(3))
                        if goal == 0.0 or (abs(goal) > 1e-3 and abs(goal) < 1e5):
                            number_format = '.3f'
                        else:
                            number_format = '.3e'

                    value = job_data.get('metric', metric, step=step, index=index)
                    criteria_ok = utils.safecompare(value, op, goal)
                    waivers = item_criteria.get_waiver(metric) \
                        if metric in item_criteria.getkeys("waiver") else []

                    criteria_str = f'{metric}{op}{goal:{number_format}}'
                    compare_str = f'{value:{number_format}}{op}{goal:{number_format}}'
                    step_desc = f'job {job} with step {step}/{index} and task {tool}/{task}'
                    if not criteria_ok and waivers:
                        if logger:
                            logger.warning(f'{item} criteria {criteria_str} ({compare_str}) unmet '
                                           f'by {step_desc}, but found waivers.')
                    elif not criteria_ok:
                        if logger:
                            logger.error(f'{item} criteria {criteria_str} ({compare_str}) unmet '
                                         f'by {step_desc}.')
                        error = True
                    elif criteria_ok and logger:
                        logger.info(f'{item} criteria {criteria_str} met by {step_desc}.')

                    has_reports = (
                        job_data.valid('tool', tool, 'task', task, 'report', metric) and
                        job_data.get('tool', tool, 'task', task, 'report', metric,
                                     step=step, index=index)
                    )

                    if allow_missing_reports and not has_reports:
                        continue

                    reports = []
                    try:
                        if has_reports:
                            reports = job_data.find_files(
                                'tool', tool, 'task', task, 'report', metric,
                                step=step, index=index,
                                missing_ok=not require_reports)
                    except FileNotFoundError:
                        reports = []
                        continue

                    if require_reports and not reports:
                        if logger:
                            logger.error(f'No reports generated for metric {metric} in {step_desc}')
                        error = True

                    for report in reports:
                        if not report:
                            continue
                        report_path = os.path.relpath(report, cwd)
                        if report_path not in item_criteria.get_report():
                            item_criteria.add_report(report_path)

            if has_check:
                if require_reports and not allow_missing_reports and not item_criteria.get_report():
                    if logger:
                        logger.error(f'No report documenting item {item}')
                    error = True

                if check_ok and not item_criteria.get_ok():
                    if logger:
                        logger.error(f"Item {item} 'ok' field not checked")
                    error = True

        if not error and logger:
            logger.info('Check succeeded!')

        return not error

    @classmethod
    def _getdict_type(cls) -> str:
        """
        Internal method to return the type name for dictionary representation.
        """
        return Checklist.__name__

    def _generate_doc(self, doc,
                      ref_root: str = "",
                      key_offset: Optional[Tuple[str, ...]] = None,
                      detailed: bool = True):
        """
        Internal method to generate documentation for the checklist schema.
        """
        from .schema.docs.utils import build_section
        settings = build_section('Configuration', f"{ref_root}-config")

        if not key_offset:
            key_offset = tuple()

        for key in self.getkeys():
            criteria = build_section(key, f"{ref_root}-config-{key}")
            params = BaseSchema._generate_doc(self.get(key, field="schema"),
                                              doc,
                                              ref_root=f"{ref_root}-config-{key}",
                                              key_offset=(*key_offset, "checklist", self.name),
                                              detailed=False)
            if params:
                criteria += params
                settings += criteria

        return settings


############################################
# Design Checklist Schema Definition
############################################
def schema_checklist(schema: Criteria):
    """
    Adds standard checklist parameters to a Criteria schema object.

    This function defines the common set of parameters that make up a checklist
    item, such as 'description', 'criteria', 'report', etc., and adds them to
    the provided schema.

    Args:
        schema (Criteria): The Criteria schema object to modify.
    """
    edit = EditableSchema(schema)

    metric = 'default'

    edit.insert(
        'description',
        Parameter(
            'str',
            scope=Scope.GLOBAL,
            shorthelp="Checklist: item description",
            switch="-checklist_description 'standard item <str>'",
            example=[
                "cli: -checklist_description 'ISO D000 A-DESCRIPTION'",
                "api: check.set('checklist', 'ISO', 'D000', 'description', 'A-DESCRIPTION')"],
            help=trim("""
            A short one line description of the checklist item.""")))

    edit.insert(
        'requirement',
        Parameter(
            'str',
            scope=Scope.GLOBAL,
            shorthelp="Checklist: item requirement",
            switch="-checklist_requirement 'standard item <str>'",
            example=[
                "cli: -checklist_requirement 'ISO D000 DOCSTRING'",
                "api: check.set('checklist', 'ISO', 'D000', 'requirement', 'DOCSTRING')"],
            help=trim("""
            A complete requirement description of the checklist item
            entered as a multi-line string.""")))

    edit.insert(
        'dataformat',
        Parameter(
            'str',
            scope=Scope.GLOBAL,
            shorthelp="Checklist: item data format",
            switch="-checklist_dataformat 'standard item <str>'",
            example=[
                "cli: -checklist_dataformat 'ISO D000 README'",
                "api: check.set('checklist', 'ISO', 'D000', 'dataformat', 'README')"],
            help=trim("""
            Free text description of the type of data files acceptable as
            checklist signoff validation.""")))

    edit.insert(
        'rationale',
        Parameter(
            '[str]',
            scope=Scope.GLOBAL,
            shorthelp="Checklist: item rationale",
            switch="-checklist_rationale 'standard item <str>'",
            example=[
                "cli: -checklist_rationale 'ISO D000 reliability'",
                "api: check.set('checklist', 'ISO', 'D000', 'rationale', 'reliability')"],
            help=trim("""
            Rationale for the checklist item. Rationale should be a
            unique alphanumeric code used by the standard or a short one line
            or single word description.""")))

    edit.insert(
        'criteria',
        Parameter(
            '[str]',
            scope=Scope.GLOBAL,
            shorthelp="Checklist: item criteria",
            switch="-checklist_criteria 'standard item <str>'",
            example=[
                "cli: -checklist_criteria 'ISO D000 errors==0'",
                "api: check.set('checklist', 'ISO', 'D000', 'criteria', 'errors==0')"],
            help=trim("""
            Simple list of signoff criteria for checklist item which
            must all be met for signoff. Each signoff criteria consists of
            a metric, a relational operator, and a value in the form
            'metric op value'.""")))

    edit.insert(
        'task',
        Parameter(
            '[(str,str,str)]',
            scope=Scope.GLOBAL,
            shorthelp="Checklist: item task",
            switch="-checklist_task 'standard item <(str,str,str)>'",
            example=[
                "cli: -checklist_task 'ISO D000 (job0,place,0)'",
                "api: check.set('checklist', 'ISO', 'D000', 'task', ('job0', 'place', '0'))"],
            help=trim("""
            Flowgraph job and task used to verify the checklist item.
            The parameter should be left empty for manual and for tool
            flows that bypass the SC infrastructure.""")))

    edit.insert(
        'report',
        Parameter(
            '[file]',
            scope=Scope.GLOBAL,
            shorthelp="Checklist: item report",
            switch="-checklist_report 'standard item <file>'",
            example=[
                "cli: -checklist_report 'ISO D000 my.rpt'",
                "api: check.set('checklist', 'ISO', 'D000', 'report', 'my.rpt')"],
            help=trim("""
            Filepath to report(s) of specified type documenting the successful
            validation of the checklist item.""")))

    edit.insert(
        'waiver', metric,
        Parameter(
            '[file]',
            scope=Scope.GLOBAL,
            shorthelp="Checklist: item metric waivers",
            switch="-checklist_waiver 'standard item metric <file>'",
            example=[
                "cli: -checklist_waiver 'ISO D000 bold my.txt'",
                "api: check.set('checklist', 'ISO', 'D000', 'waiver', 'hold', 'my.txt')"],
            help=trim("""
            Filepath to report(s) documenting waivers for the checklist
            item specified on a per metric basis.""")))

    edit.insert(
        'ok',
        Parameter(
            'bool',
            scope=Scope.GLOBAL,
            shorthelp="Checklist: item ok",
            switch="-checklist_ok 'standard item <bool>'",
            example=[
                "cli: -checklist_ok 'ISO D000 true'",
                "api: check.set('checklist', 'ISO', 'D000', 'ok', True)"],
            help=trim("""
            Boolean check mark for the checklist item. A value of
            True indicates a human has inspected the all item dictionary
            parameters and verified they check out.""")))
