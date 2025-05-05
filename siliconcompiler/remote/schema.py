from siliconcompiler.schema import BaseSchema
from siliconcompiler.schema import CommandLineSchema
from siliconcompiler.schema import EditableSchema
from siliconcompiler.schema import Parameter, Scope


SCHEMA_VERSION = '0.0.2'


class ServerSchema(BaseSchema, CommandLineSchema):
    def __init__(self):
        super().__init__()

        schema = EditableSchema(self)

        schema.insert(
            'schemaversion',
            Parameter(
                'str',
                scope=Scope.GLOBAL,
                defvalue=SCHEMA_VERSION,
                require='all',
                shorthelp="Schema version number",
                lock=True,
                switch="-schemaversion <str>",
                example=["api: server.get('schemaversion')"],
                help="""SiliconCompiler server schema version number."""))

        schema.insert(
            'option', 'port',
            Parameter(
                'int',
                scope=Scope.GLOBAL,
                defvalue=8080,
                require='all',
                shorthelp="Port number to run the server on.",
                switch="-port <int>",
                example=["cli: -port 8000",
                         "api: server.set('option', 'port', 8080)"],
                help="""Port number to run the server on."""))

        schema.insert(
            'option', 'cluster',
            Parameter(
                '<local,slurm>',
                scope=Scope.GLOBAL,
                defvalue='local',
                require='all',
                shorthelp="Type of compute cluster to use.",
                switch="-cluster <str>",
                example=["cli: -cluster slurm",
                         "api: server.set('option', 'clister', 'slurm')"],
                help="""Type of compute cluster to use."""))

        schema.insert(
            'option', 'nfsmount',
            Parameter(
                'dir',
                scope=Scope.GLOBAL,
                defvalue='/nfs/sc_compute',
                require='all',
                shorthelp="Directory of mounted shared NFS storage.",
                switch="-nfsmount <dir>",
                example=["cli: -nfsmount ~/sc_server",
                         "api: server.set('option', 'server', '~/sc_server')"],
                help="""Directory of mounted shared NFS storage."""))

        schema.insert(
            'option', 'auth',
            Parameter(
                'bool',
                scope=Scope.GLOBAL,
                defvalue=False,
                require='all',
                shorthelp="Flag determining whether to enable authenticated and encrypted jobs.",
                switch="-auth <bool>",
                example=["cli: -auth true",
                         "api: server.set('option', 'auth', True)"],
                help="""Flag determining whether to enable authenticated and encrypted jobs."""))

        schema.insert(
            'option', 'cfg',
            Parameter(
                '[file]',
                scope=Scope.JOB,
                shorthelp="Configuration manifest",
                switch="-cfg <file>",
                example=["cli: -cfg mypdk.json",
                         "api: chip.set('option', 'cfg', 'mypdk.json')"],
                help="""
                List of filepaths to JSON formatted schema configuration
                manifests. The files are read in automatically when using the
                command line application. In Python programs, JSON manifests
                can be merged into the current working manifest using the
                read_manifest() method."""))

        schema.insert(
            'option', 'loglevel',
            Parameter(
                '<info,warning,error,critical,debug>',
                scope=Scope.JOB,
                defvalue='info',
                shorthelp="Logging level",
                switch="-loglevel <str>",
                example=[
                        "cli: -loglevel info",
                        "api: server.set('option', 'loglevel', 'info')"],
                help="""
                Provides explicit control over the level of debug logging printed."""))

        schema.insert(
            'option', 'checkinterval',
            Parameter(
                'int',
                defvalue=30,
                shorthelp="Interval for client",
                switch="-checkinterval <int>",
                example=["cli: -checkinterval 10",
                         "api: chip.set('option', 'checkinterval', 10)"],
                help="""
                Interval between checks to announce to clients"""))
