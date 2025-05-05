# Copyright 2025 Silicon Compiler Authors. All Rights Reserved.

from siliconcompiler.schema import BaseSchema
from siliconcompiler.schema import EditableSchema, Parameter, PerNode, Scope
from siliconcompiler.schema.utils import trim


class RecordSchema(BaseSchema):
    def __init__(self):
        super().__init__()

        schema_record(self)


###########################################################################
# Run Record
###########################################################################
def schema_record(schema):
    schema = EditableSchema(schema)
    records = {'userid': ['userid',
                          'wiley',
                          ''],
               'publickey': ['public key',
                             '<key>',
                             ''],
               'machine': ['machine name',
                           'carbon',
                           '(myhost, localhost, ...'],
               'macaddr': ['MAC address',
                           '<addr>',
                           ''],
               'ipaddr': ['IP address',
                          '<addr>',
                          ''],
               'platform': ['platform name',
                            'linux',
                            '(linux, windows, freebsd)'],
               'distro': ['distro name',
                          'ubuntu',
                          '(ubuntu, redhat, centos)'],
               'arch': ['hardware architecture',
                        'x86_64',
                        '(x86_64, rv64imafdc)'],
               'starttime': ['start time',
                             '\"2021-09-06 12:20:20\"',
                             'Time is reported in the ISO 8601 format YYYY-MM-DD HR:MIN:SEC'],
               'endtime': ['end time',
                           '\"2021-09-06 12:20:20\"',
                           'Time is reported in the ISO 8601 format YYYY-MM-DD HR:MIN:SEC'],
               'region': ['cloud region',
                          '\"US Gov Boston\"',
                          """Recommended naming methodology:

                          * local: node is the local machine
                          * onprem: node in on-premises IT infrastructure
                          * public: generic public cloud
                          * govcloud: generic US government cloud
                          * <region>: cloud and entity specific region string name
                          """],
               'scversion': ['software version',
                             '1.0',
                             """Version number for the SiliconCompiler software."""],
               'toolversion': ['tool version',
                               '1.0',
                               """The tool version captured corresponds to the 'tool'
                               parameter within the 'tool' dictionary."""],
               'toolpath': ['tool path',
                            '/usr/bin/openroad',
                            """Full path to tool executable used to run this
                            task."""],
               'toolargs': ['tool CLI arguments',
                            '\"-I include/ foo.v\"',
                            'Arguments passed to tool via CLI.'],
               'pythonversion': ['Python version',
                                 '3.12.3',
                                 """Version of python used to run this task."""],
               'osversion': ['O/S version',
                             '20.04.1-Ubuntu',
                             """Since there is not standard version system for operating
                             systems, extracting information from is platform dependent.
                             For Linux based operating systems, the 'osversion' is the
                             version of the distro."""],
               'kernelversion': ['O/S kernel version',
                                 '5.11.0-34-generic',
                                 """Used for platforms that support a distinction
                                 between os kernels and os distributions."""]}

    for key, (shorthelp, example, longhelp) in records.items():
        schema.insert(
            key,
            Parameter(
                "str",
                scope=Scope.JOB,
                shorthelp=f"Record: {shorthelp}",
                switch=f"-record_{key} 'step index <str>'",
                example=[
                    f"cli: -record_{key} 'dfm 0 {example}'",
                    f"api: chip.set('record', '{key}', '{example}', step='dfm', index=0)"],
                pernode=PerNode.REQUIRED,
                help=f'Record tracking the {shorthelp} per step and index basis.'
                     f'{" " + trim(longhelp) if longhelp else ""}'
            ))

    schema.insert(
        "toolexitcode",
        Parameter(
            "int",
            scope=Scope.JOB,
            shorthelp="Record: tool exit code",
            switch="-record_toolexitcode 'step index <int>'",
            example=[
                "cli: -record_toolexitcode 'dfm 0 0'",
                "api: chip.set('record', 'toolexitcode', 0, step='dfm', index=0)"],
            pernode=PerNode.REQUIRED,
            help='Record tracking the tool exit code per step and index basis.'
        ))

    # Non-per-node records.
    schema.insert(
        "remoteid",
        Parameter(
            "str",
            scope=Scope.JOB,
            shorthelp="Record: remote job ID",
            switch="-record_remoteid '<str>'",
            example=[
                "cli: -record_remoteid '0123456789abcdeffedcba9876543210'",
                "api: chip.set('record', 'remoteid', '0123456789abcdeffedcba9876543210')"],
            help='Record tracking the job ID for a remote run.'
        ))

    schema.insert(
        "pythonpackage",
        Parameter(
            "[str]",
            scope=Scope.JOB,
            shorthelp="Record: python packages",
            switch="-record_pythonpackage '<str>'",
            example=[
                "cli: -record_pythonpackage 'siliconcompiler==0.28.0'",
                "api: chip.set('record', 'pythonpackage', 'siliconcompiler==0.28.0')"],
            help='Record tracking for the python packages installed.'
        ))

    # flowgraph status
    schema.insert(
        "status",
        Parameter(
            "<pending,queued,running,success,error,skipped,timeout>",  # sync with NodeStatus
            pernode=PerNode.REQUIRED,
            scope=Scope.JOB,
            shorthelp="Record: node execution status",
            switch="-record_status 'step index <str>'",
            example=[
                "cli: -record_status 'syn 0 success'",
                "api: chip.set('record', 'status', 'success', step='syn', index='0')"],
            help="""Record tracking for the status of a node."""
        ))

    # flowgraph select
    schema.insert(
        "inputnode",
        Parameter(
            "[(str,str)]",
            pernode=PerNode.REQUIRED,
            scope=Scope.JOB,
            shorthelp="Record: node inputs",
            switch="-record_inputnode 'step index <(str,str)>'",
            example=[
                "cli: -record_inputnode 'cts 0 (place,42)'",
                "api: chip.set('record', 'inputnode', ('place', '42'), step='syn', index='0')"],
            help=trim("""
            List of selected inputs for the current step/index specified as
            (in_step, in_index) tuple.""")
        ))
