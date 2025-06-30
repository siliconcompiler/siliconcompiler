import re

import os.path

from siliconcompiler.schema import NamedSchema
from siliconcompiler.schema import EditableSchema, Parameter, Scope
from siliconcompiler.schema.utils import trim

from siliconcompiler import NodeStatus, utils


class ChecklistSchema(NamedSchema):
    def __init__(self, name=None):
        super().__init__()
        self.set_name(name)

        schema_checklist(self)

    def check(self, items=None, check_ok=False, require_reports=True):
        '''
        Check items in a checklist.

        Checks the status of items in a checklist for the standard provided. If
        a specific list of items is unspecified, all items are checked.

        All items have an associated 'task' parameter, which indicates which
        tasks can be used to automatically validate the item. For an item to be
        checked, all tasks must satisfy the item's criteria, unless waivers are
        provided. In addition, that task must have generated EDA report files
        for each metric in the criteria.

        For items without an associated task, the only requirement is that at
        least one report has been added to that item.

        When 'check_ok' is True, every item must also have its 'ok' parameter
        set to True, indicating that a human has reviewed the item.

        Args:
            items (list of str): Items to check from standard.
            check_ok (bool): Whether to check item 'ok' parameter.
            verbose (bool): Whether to print passing criteria.
            require_reports (bool): Whether to assert the presence of reports.

        Returns:
            Status of item check.

        Examples:
            >>> status = chip.check_checklist('d000')
            Returns status.
        '''
        error = False

        schema_root = self._parent(root=True)
        logger = getattr(schema_root, "logger", None)
        cwd = getattr(schema_root, "cwd", os.getcwd())

        assert hasattr(schema_root, "history"), f"{schema_root}"

        if logger:
            logger.info(f'Checking checklist {self.name()}')

        if items is None:
            items = self.getkeys()

        # these tasks are recorded by SC so there are no reports
        metrics_without_reports = (
            'tasktime',
            'totaltime',
            'exetime',
            'memory')

        for item in items:
            if item not in self.getkeys():
                if logger:
                    logger.error(f'{item} is not a check in {self.name()}.')
                error = True
                continue

            allow_missing_reports = True

            has_check = False

            all_criteria = self.get(item, 'criteria')
            for criteria in all_criteria:
                m = re.match(r'^(\w+)\s*([\>\=\<]+)\s*([+\-]?\d+(\.\d+)?(e[+\-]?\d+)?)$',
                             criteria.strip())
                if not m:
                    raise ValueError(f"Illegal checklist criteria: {criteria}")

                metric = m.group(1)
                op = m.group(2)

                if metric not in metrics_without_reports:
                    allow_missing_reports = False

                tasks = self.get(item, 'task')
                for job, step, index in tasks:
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
                    criteria_ok = utils.safecompare(self, value, op, goal)
                    if metric in self.getkeys(item, 'waiver'):
                        waivers = self.get(item, 'waiver', metric)
                    else:
                        waivers = []

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
                    elif criteria_ok:
                        if logger:
                            logger.info(f'{item} criteria {criteria_str} met by {step_desc}.')

                    has_reports = \
                        job_data.valid('tool', tool, 'task', task, 'report', metric) and \
                        job_data.get('tool', tool, 'task', task, 'report', metric,
                                     step=step, index=index)

                    if allow_missing_reports and not has_reports:
                        # No reports available and it is allowed
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
                            logger.error(f'No reports generated for metric {metric} in '
                                         f'{step_desc}')
                        error = True

                    for report in reports:
                        if not report:
                            continue

                        report = os.path.relpath(report, cwd)
                        if report not in self.get(item, 'report'):
                            self.add(item, 'report', report)

            if has_check:
                if require_reports and \
                        not allow_missing_reports and \
                        not self.get(item, 'report'):
                    # TODO: validate that report exists?
                    if logger:
                        logger.error(f'No report documenting item {item}')
                    error = True

                if check_ok and not self.get(item, 'ok'):
                    if logger:
                        logger.error(f"Item {item} 'ok' field not checked")
                    error = True

        if not error and logger:
            logger.info('Check succeeded!')

        return not error


############################################
# Design Checklist
############################################
def schema_checklist(schema):
    schema = EditableSchema(schema)

    item = 'default'
    metric = 'default'

    schema.insert(
        item, 'description',
        Parameter(
            'str',
            scope=Scope.GLOBAL,
            shorthelp="Checklist: item description",
            switch="-checklist_description 'standard item <str>'",
            example=[
                "cli: -checklist_description 'ISO D000 A-DESCRIPTION'",
                "api: chip.set('checklist', 'ISO', 'D000', 'description', 'A-DESCRIPTION')"],
            help=trim("""
            A short one line description of the checklist item.""")))

    schema.insert(
        item, 'requirement',
        Parameter(
            'str',
            scope=Scope.GLOBAL,
            shorthelp="Checklist: item requirement",
            switch="-checklist_requirement 'standard item <str>'",
            example=[
                "cli: -checklist_requirement 'ISO D000 DOCSTRING'",
                "api: chip.set('checklist', 'ISO', 'D000', 'requirement', 'DOCSTRING')"],
            help=trim("""
            A complete requirement description of the checklist item
            entered as a multi-line string.""")))

    schema.insert(
        item, 'dataformat',
        Parameter(
            'str',
            scope=Scope.GLOBAL,
            shorthelp="Checklist: item data format",
            switch="-checklist_dataformat 'standard item <str>'",
            example=[
                "cli: -checklist_dataformat 'ISO D000 README'",
                "api: chip.set('checklist', 'ISO', 'D000', 'dataformat', 'README')"],
            help=trim("""
            Free text description of the type of data files acceptable as
            checklist signoff validation.""")))

    schema.insert(
        item, 'rationale',
        Parameter(
            '[str]',
            scope=Scope.GLOBAL,
            shorthelp="Checklist: item rational",
            switch="-checklist_rationale 'standard item <str>'",
            example=[
                "cli: -checklist_rationale 'ISO D000 reliability'",
                "api: chip.set('checklist', 'ISO', 'D000', 'rationale', 'reliability')"],
            help=trim("""
            Rationale for the the checklist item. Rationale should be a
            unique alphanumeric code used by the standard or a short one line
            or single word description.""")))

    schema.insert(
        item, 'criteria',
        Parameter(
            '[str]',
            scope=Scope.GLOBAL,
            shorthelp="Checklist: item criteria",
            switch="-checklist_criteria 'standard item <str>'",
            example=[
                "cli: -checklist_criteria 'ISO D000 errors==0'",
                "api: chip.set('checklist', 'ISO', 'D000', 'criteria', 'errors==0')"],
            help=trim("""
            Simple list of signoff criteria for checklist item which
            must all be met for signoff. Each signoff criteria consists of
            a metric, a relational operator, and a value in the form.
            'metric op value'.""")))

    schema.insert(
        item, 'task',
        Parameter(
            '[(str,str,str)]',
            scope=Scope.GLOBAL,
            shorthelp="Checklist: item task",
            switch="-checklist_task 'standard item <(str,str,str)>'",
            example=[
                "cli: -checklist_task 'ISO D000 (job0,place,0)'",
                "api: chip.set('checklist', 'ISO', 'D000', 'task', ('job0', 'place', '0'))"],
            help=trim("""
            Flowgraph job and task used to verify the checklist item.
            The parameter should be left empty for manual and for tool
            flows that bypass the SC infrastructure.""")))

    schema.insert(
        item, 'report',
        Parameter(
            '[file]',
            scope=Scope.GLOBAL,
            shorthelp="Checklist: item report",
            switch="-checklist_report 'standard item <file>'",
            example=[
                "cli: -checklist_report 'ISO D000 my.rpt'",
                "api: chip.set('checklist', 'ISO', 'D000', 'report', 'my.rpt')"],
            help=trim("""
            Filepath to report(s) of specified type documenting the successful
            validation of the checklist item.""")))

    schema.insert(
        item, 'waiver', metric,
        Parameter(
            '[file]',
            scope=Scope.GLOBAL,
            shorthelp="Checklist: item metric waivers",
            switch="-checklist_waiver 'standard item metric <file>'",
            example=[
                "cli: -checklist_waiver 'ISO D000 bold my.txt'",
                "api: chip.set('checklist', 'ISO', 'D000', 'waiver', 'hold', 'my.txt')"],
            help=trim("""
            Filepath to report(s) documenting waivers for the checklist
            item specified on a per metric basis.""")))

    schema.insert(
        item, 'ok',
        Parameter(
            'bool',
            scope=Scope.GLOBAL,
            shorthelp="Checklist: item ok",
            switch="-checklist_ok 'standard item <bool>'",
            example=[
                "cli: -checklist_ok 'ISO D000 true'",
                "api: chip.set('checklist', 'ISO', 'D000', 'ok', True)"],
            help=trim("""
            Boolean check mark for the checklist item. A value of
            True indicates a human has inspected the all item dictionary
            parameters check out.""")))
