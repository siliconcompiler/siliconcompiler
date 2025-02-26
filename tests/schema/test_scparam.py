from siliconcompiler.schema import Schema
from siliconcompiler.schema.schema_cfg import scparam, SCHEMA_DEFAULT_KEY
from siliconcompiler.schema.utils import PerNode, Scope


def test_scparam():
    cfg = {}

    # metrics
    scparam(cfg, ['metric', SCHEMA_DEFAULT_KEY, SCHEMA_DEFAULT_KEY, 'cells', SCHEMA_DEFAULT_KEY],
            sctype='int',
            require='asic',
            scope=Scope.JOB,
            shorthelp='Metric instance count',
            switch="-metric_cells 'step index group <int>'",
            example=[
                "cli: -metric_cells 'place 0 goal 100'",
                "api: chip.set('metric', 'place', '0', 'cells', 'goal, '100')"],
            schelp="""
            Metric tracking the total number of instances on a per step basis.
            Total cells includes registers. In the case of FPGAs, it
            represents the number of LUTs.
            """)

    scparam(cfg, ['metric', SCHEMA_DEFAULT_KEY, SCHEMA_DEFAULT_KEY, 'warnings', SCHEMA_DEFAULT_KEY],
            sctype='int',
            require='all',
            scope=Scope.JOB,
            shorthelp='Metric total warnings',
            switch="-metric_warnings 'step index group <int>'",
            example=[
                "cli: -metric_warnings 'dfm 0 goal 0'",
                "api: chip.set('metric', 'dfm', '0', 'warnings', 'real', '0')"],
            schelp="""
            Metric tracking the total number of warnings on a per step basis.
            """)

    # golden version
    cfg_golden = {}

    cfg_golden['metric'] = {}
    cfg_golden['metric'][SCHEMA_DEFAULT_KEY] = {}
    cfg_golden['metric'][SCHEMA_DEFAULT_KEY][SCHEMA_DEFAULT_KEY] = {}

    cfg_golden['metric'][SCHEMA_DEFAULT_KEY][SCHEMA_DEFAULT_KEY]['warnings'] = {}
    cfg_golden['metric'][SCHEMA_DEFAULT_KEY][SCHEMA_DEFAULT_KEY]['warnings'][SCHEMA_DEFAULT_KEY] = {
        'switch': [
            "-metric_warnings 'step index group <int>'"],
        'type': 'int',
        'lock': False,
        'scope': Scope.JOB.value,
        'require': 'all',
        'notes': None,
        'pernode': PerNode.NEVER.value,
        'node': {
            'default': {
                'default': {
                    'value': None,
                    'signature': None
                }
            }
        },
        'shorthelp': 'Metric total warnings',
        'example': [
            "cli: -metric_warnings 'dfm 0 goal 0'",
            "api: chip.set('metric', 'dfm', '0', 'warnings', 'real', '0')"],
        'help': "Metric tracking the total number of warnings on a per step basis."
    }

    cfg_golden['metric'][SCHEMA_DEFAULT_KEY][SCHEMA_DEFAULT_KEY]['cells'] = {}
    cfg_golden['metric'][SCHEMA_DEFAULT_KEY][SCHEMA_DEFAULT_KEY]['cells'][SCHEMA_DEFAULT_KEY] = {
        'switch': [
            "-metric_cells 'step index group <int>'"],
        'type': 'int',
        'lock': False,
        'scope': Scope.JOB.value,
        'require': 'asic',
        'notes': None,
        'pernode': PerNode.NEVER.value,
        'node': {
            'default': {
                'default': {
                    'value': None,
                    'signature': None
                }
            }
        },
        'shorthelp': 'Metric instance count',
        'example': [
            "cli: -metric_cells 'place 0 goal 100'",
            "api: chip.set('metric', 'place', '0', 'cells', 'goal, '100')"],
        'help': """Metric tracking the total number of instances on a per step basis.
Total cells includes registers. In the case of FPGAs, it
represents the number of LUTs."""
    }

    assert cfg == cfg_golden


def test_defvalue():
    '''Regression test that changing list-type value doesn't change defvalue.'''

    schema = Schema()
    assert schema.get_default('asic', 'logiclib') == []
    schema.add('asic', 'logiclib', 'mylib')
    assert schema.get_default('asic', 'logiclib') == []


#########################
if __name__ == "__main__":
    test_scparam()
