from siliconcompiler.schema import BaseSchema, EditableSchema, Parameter, Scope
from siliconcompiler.schema_support.cmdlineschema import CommandLineSchema


SCHEMA_VERSION = '0.0.4'


class ServerSchema(CommandLineSchema, BaseSchema):
    def __init__(self):
        super().__init__()

        schema = EditableSchema(self)

        schema.insert(
            'schemaversion',
            Parameter(
                'str',
                scope=Scope.GLOBAL,
                defvalue=SCHEMA_VERSION,
                require=True,
                shorthelp="Schema version number",
                lock=True,
                switch="-schemaversion <str>",
                example=["api: server.get('schemaversion')"],
                help="""SiliconCompiler server schema version number."""))

        schema.insert(
            'option', 'port',
            Parameter(
                'int<1..65535>',
                scope=Scope.GLOBAL,
                defvalue=8080,
                require=True,
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
                require=True,
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
                defvalue='./sc_compute',
                require=True,
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
                require=True,
                shorthelp="Flag determining whether to enable authenticated and encrypted jobs.",
                switch="-auth <bool>",
                example=["cli: -auth true",
                         "api: server.set('option', 'auth', True)"],
                help="""Flag determining whether to enable authenticated and encrypted jobs."""))

        schema.insert(
            'option', 'maxuploadsize',
            Parameter(
                'int<0..>',
                scope=Scope.GLOBAL,
                defvalue=0,
                shorthelp="Maximum size in MB of an uploaded job.",
                switch="-maxuploadsize <int>",
                example=["cli: -maxuploadsize 1024",
                         "api: server.set('option', 'maxuploadsize', 1024)"],
                help="""
                Maximum size in MB of a job upload. Zero, the default, accepts
                any size: a job's manifest and its collected sources are sent in
                one request, which for a real design is routinely tens of MB and
                has no upper bound this server could pick for it."""))

        schema.insert(
            'option', 'checkinterval',
            Parameter(
                'int<1..>',
                defvalue=5,
                shorthelp="Interval for client checks",
                switch="-checkinterval <int>",
                example=["cli: -checkinterval 10",
                         "api: server.set('option', 'checkinterval', 10)"],
                units="s",
                help="""
                Interval between checks to announce to clients"""))
