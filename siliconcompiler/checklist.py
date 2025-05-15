from siliconcompiler.schema import NamedSchema
from siliconcompiler.schema import EditableSchema, Parameter, Scope
from siliconcompiler.schema.utils import trim


class ChecklistSchema(NamedSchema):
    def __init__(self, name=None):
        super().__init__(name=name)

        schema_checklist(self)


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
