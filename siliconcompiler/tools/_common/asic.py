from .. import _common
import json


def get_mainlib(chip):
    return get_libraries(chip, 'logic')[0]


def get_libraries(chip, type):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')

    if type not in ('logic', 'macro'):
        raise ValueError(f'Cannot collect {type} libraries')

    libs = []
    for lib in chip.get('asic', f'{type}lib', step=step, index=index):
        if lib in libs:
            continue
        libs.append(lib)

    for lib in _common.get_libraries(chip, include_asic=False):
        if not chip.valid('library', lib, 'asic', f'{type}lib'):
            continue
        for sublib in chip.get('library', lib, 'asic', f'{type}lib', step=step, index=index):
            if sublib in libs:
                continue
            libs.append(sublib)

    return libs


def get_timing_modes(chip):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')

    modes = set()
    for scenario in chip.getkeys('constraint', 'timing'):
        modes.add(chip.get('constraint', 'timing', scenario, 'mode',
                  step=step, index=index))
    return sorted(modes)


def set_tool_task_var(chip,
                      param_key,
                      default_value=None,
                      schelp=None,
                      option_key=None,
                      pdk_key=None,
                      lib_key=None,
                      require=None,
                      skip=None):
    '''
    Set parameter from PDK -> main library -> option -> default_value
    '''
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = _common.get_tool_task(chip, step, index)
    pdkname = chip.get('option', 'pdk')
    stackup = chip.get('option', 'stackup')

    if not skip:
        skip = []
    if not isinstance(skip, (list, tuple)):
        skip = [skip]

    if not require:
        require = []
    if not isinstance(require, (list, tuple)):
        require = [require]

    check_keys = []

    # Add PDK key
    if 'pdk' not in skip:
        if not pdk_key:
            pdk_key = param_key
        check_keys.append(['pdk', pdkname, 'var', tool, stackup, pdk_key])
        if 'pdk' in require:
            chip.add('tool', tool, 'task', task, 'require',
                     ','.join(check_keys[-1]),
                     step=step, index=index)

    # Add library key
    if 'lib' not in skip:
        mainlib = get_mainlib(chip)
        if not lib_key:
            lib_key = f'{tool}_{param_key}'
        check_keys.append(['library', mainlib, 'option', 'var', lib_key])
        if 'lib' in require:
            chip.add('tool', tool, 'task', task, 'require',
                     ','.join(check_keys[-1]),
                     step=step, index=index)

    # Add option key
    if 'option' not in skip:
        if not option_key:
            option_key = f'{tool}_{param_key}'
        check_keys.append(['option', 'var', option_key])
        if 'option' in require:
            chip.add('tool', tool, 'task', task, 'require',
                     ','.join(check_keys[-1]),
                     step=step, index=index)

    require_key, value = _common.pick_key(chip, reversed(check_keys), step=step, index=index)
    if not value:
        value = default_value

    if value:
        chip.set('tool', tool, 'task', task, 'var', param_key, value,
                 step=step, index=index, clobber=False)

        if require_key:
            chip.add('tool', tool, 'task', task, 'require',
                     ','.join(require_key),
                     step=step, index=index)

    if value or 'key' in require:
        chip.add('tool', tool, 'task', task, 'require',
                 ','.join(['tool', tool, 'task', task, 'var', param_key]),
                 step=step, index=index)

    if schelp:
        chip.set('tool', tool, 'task', task, 'var', param_key,
                 schelp, field='help')

    return value


def get_tool_task_var(chip,
                      param_key,
                      option_key=None,
                      pdk_key=None,
                      lib_key=None,
                      skip=None):
    '''
    Get parameter from PDK -> main library -> option -> default_value
    '''
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, _ = _common.get_tool_task(chip, step, index)
    pdkname = chip.get('option', 'pdk')
    stackup = chip.get('option', 'stackup')

    if not skip:
        skip = []
    if not isinstance(skip, (list, tuple)):
        skip = [skip]

    check_keys = []
    # Add PDK key
    if 'pdk' not in skip:
        if not pdk_key:
            pdk_key = param_key
        check_keys.append(['pdk', pdkname, 'var', tool, stackup, pdk_key])

    # Add library key
    if 'lib' not in skip:
        mainlib = get_mainlib(chip)
        if not lib_key:
            lib_key = f'{tool}_{param_key}'
        check_keys.append(['library', mainlib, 'option', 'var', lib_key])

    # Add option key
    if 'option' not in skip:
        if not option_key:
            option_key = f'{tool}_{param_key}'
        check_keys.append(['option', 'var', option_key])

    _, value = _common.pick_key(chip, reversed(check_keys), step=step, index=index)

    return value


class CellArea:
    def __init__(self):
        self.__areas = {}

    def addCell(self, name=None, module=None,
                cellarea=None, cellcount=None,
                macroarea=None, macrocount=None,
                stdcellarea=None, stdcellcount=None):
        if not name and not module:
            return

        if all([metric is None for metric in (
                cellarea, cellcount,
                macroarea, macrocount,
                stdcellarea, stdcellcount)]):
            return

        if not name:
            name = module

        # ensure name is unique
        check_name = name
        idx = 0
        while check_name in self.__areas:
            check_name = f'{name}{idx}'
            idx += 1
        name = check_name

        self.__areas[name] = {
            "module": module,
            "cellarea": cellarea,
            "cellcount": cellcount,
            "macroarea": macroarea,
            "macrocount": macrocount,
            "stdcellarea": stdcellarea,
            "stdcellcount": stdcellcount
        }

    def size(self):
        return len(self.__areas)

    def writeReport(self, path):
        with open(path, 'w') as f:
            json.dump(self.__areas, f, indent=4)
