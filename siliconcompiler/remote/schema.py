from siliconcompiler.schema.schema_cfg import scparam
from siliconcompiler.schema import Schema


SCHEMA_VERSION = '0.0.1'


def schema_cfg():
    # Basic schema setup
    cfg = {}

    scparam(cfg, ['schemaversion'],
            sctype='str',
            scope='global',
            defvalue=SCHEMA_VERSION,
            require='all',
            shorthelp="Schema version number",
            lock=True,
            switch="-schemaversion <str>",
            example=["api: server.get('schemaversion')"],
            schelp="""SiliconCompiler server schema version number.""")

    scparam(cfg, ['option', 'port'],
            sctype='int',
            scope='global',
            defvalue=8080,
            require='all',
            shorthelp="Port number to run the server on.",
            switch="-port <int>",
            example=["cli: -port 8000",
                     "api: server.set('option', 'port', 8080)"],
            schelp="""Port number to run the server on.""")

    scparam(cfg, ['option', 'cluster'],
            sctype='enum',
            enum=['local', 'slurm'],
            scope='global',
            defvalue='local',
            require='all',
            shorthelp="Type of compute cluster to use.",
            switch="-cluster <str>",
            example=["cli: -cluster slurm",
                     "api: server.set('option', 'clister', 'slurm')"],
            schelp="""Type of compute cluster to use.""")

    scparam(cfg, ['option', 'nfsmount'],
            sctype='dir',
            scope='global',
            defvalue='/nfs/sc_compute',
            require='all',
            shorthelp="Directory of mounted shared NFS storage.",
            switch="-nfsmount <dir>",
            example=["cli: -nfsmount ~/sc_server",
                     "api: server.set('option', 'server', '~/sc_server')"],
            schelp="""Directory of mounted shared NFS storage.""")

    scparam(cfg, ['option', 'auth'],
            sctype='bool',
            scope='global',
            defvalue=False,
            require='all',
            shorthelp="Flag determining whether to enable authenticated and encrypted jobs.",
            switch="-auth <bool>",
            example=["cli: -auth true",
                     "api: server.set('option', 'auth', True)"],
            schelp="""Flag determining whether to enable authenticated and encrypted jobs.""")

    scparam(cfg, ['option', 'cfg'],
            sctype='[file]',
            scope='job',
            shorthelp="Configuration manifest",
            switch="-cfg <file>",
            example=["cli: -cfg mypdk.json",
                     "api: chip.set('option', 'cfg', 'mypdk.json')"],
            schelp="""
            List of filepaths to JSON formatted schema configuration
            manifests. The files are read in automatically when using the
            command line application. In Python programs, JSON manifests
            can be merged into the current working manifest using the
            read_manifest() method.""")

    scparam(cfg, ['option', 'loglevel'],
            sctype='enum',
            enum=["NOTSET", "INFO", "DEBUG", "WARNING", "ERROR", "CRITICAL"],
            pernode='optional',
            scope='job',
            defvalue='INFO',
            shorthelp="Logging level",
            switch="-loglevel <str>",
            example=[
                "cli: -loglevel INFO",
                "api: server.set('option', 'loglevel', 'INFO')"],
            schelp="""
            Provides explicit control over the level of debug logging printed.""")

    return cfg


class ServerSchema(Schema):
    def __init__(self, cfg=None, manifest=None, logger=None):
        super().__init__(cfg=cfg,
                         manifest=manifest,
                         logger=logger)

    def _init_schema_cfg(self):
        return schema_cfg()
