import siliconcompiler
import os
import json
from siliconcompiler.schema import scparam

def test_scparam():

    chip = siliconcompiler.Chip()

    cfg = {}

    # version number
    scparam(cfg,['version','schema'],
            sctype='str',
            defvalue='0.0.0',
            require='all',
            scope='global',
            shorthelp='Schema version number',
            switch="-version_schema <str>",
            example=[
                "cli: -version_schema",
                "api: chip.get('version', 'schema')"],
            schelp="""
            SiliconCompiler schema version number.
            """)

    # metrics
    scparam(cfg,['metric','default','default','cells','default'],
            sctype='int',
            require='asic',
            scope='job',
            shorthelp='Metric instance count',
            switch=r"-metric_cells 'step index group <int>'",
            example=[
                "cli: -metric_cells 'place 0 goal 100'",
                "api: chip.set('metric','place','0','cells','goal,'100')"],
            schelp="""
            Metric tracking the total number of instances on a per step basis.
            Total cells includes registers. In the case of FPGAs, it
            represents the number of LUTs.
            """)

    scparam(cfg,['metric','default','default','warnings','default'],
            sctype='int',
            require='all',
            scope='job',
            shorthelp='Metric total warnings',
            switch=r"-metric_warnings 'step index group <int>'",
            example=[
                "cli: -metric_warnings 'dfm 0 goal 0'",
                "api: chip.set('metric','dfm','0','warnings','real','0')"],
            schelp="""
            Metric tracking the total number of warnings on a per step basis.
            """)

    # golden version
    cfg_golden = {}
    cfg_golden['version'] = {}
    cfg_golden['version']['schema'] = {
        'switch': "-version_schema <str>",
        'type': 'str',
        'lock': 'false',
        'scope':'global',
        'require': 'all',
        'signature': None,
        'defvalue': '0.0.0',
        'value': '0.0.0',
        'shorthelp': 'Schema version number',
        'example': ["cli: -version_schema",
                    "api: chip.get('version', 'schema')"],
        'help': """SiliconCompiler schema version number."""
    }

    step='default'
    index='default'
    group='default'

    cfg_golden['metric'] = {}
    cfg_golden['metric'][step] = {}
    cfg_golden['metric'][step][index] = {}

    cfg_golden['metric'][step][index]['warnings'] = {}
    cfg_golden['metric'][step][index]['warnings'][group] = {
        'switch': "-metric_warnings 'step index group <int>'",
        'type': 'int',
        'lock': 'false',
        'scope': 'job',
        'require': 'all',
        'signature': None,
        'defvalue': None,
        'value': None,
        'shorthelp': 'Metric total warnings',
        'example': [
            "cli: -metric_warnings 'dfm 0 goal 0'",
            "api: chip.set('metric','dfm','0','warnings','real','0')"],

        'help': """Metric tracking the total number of warnings on a per step basis."""
    }

    cfg_golden['metric'][step][index]['cells'] = {}
    cfg_golden['metric'][step][index]['cells'][group] = {
        'switch': "-metric_cells 'step index group <int>'",
        'type': 'int',
        'lock': 'false',
        'scope': 'job',
        'require': 'asic',
        'signature': None,
        'defvalue': None,
        'value': None,
        'shorthelp': 'Metric instance count',
        'example': [
            "cli: -metric_cells 'place 0 goal 100'",
            "api: chip.set('metric','place','0','cells','goal,'100')"],
        'help': """Metric tracking the total number of instances on a per step basis. Total cells includes registers. In the case of FPGAs, it represents the number of LUTs."""
    }

    assert cfg == cfg_golden


#########################
if __name__ == "__main__":
    test_scparam()
