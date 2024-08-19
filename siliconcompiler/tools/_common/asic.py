from .. import _common


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
                      require=None):
    '''
    Set parameter from PDK -> main library -> option -> default_value
    '''
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = _common.get_tool_task(chip, step, index)
    pdkname = chip.get('option', 'pdk')
    stackup = chip.get('option', 'stackup')
    mainlib = get_mainlib(chip)

    if not require:
        require = []
    if not isinstance(require, (list, tuple)):
        require = [require]

    check_keys = []

    # Add PDK key
    if not pdk_key:
        pdk_key = param_key
    check_keys.append(['pdk', pdkname, 'var', tool, stackup, pdk_key])
    if 'pdk' in require:
        chip.add('tool', tool, 'task', task, 'require',
                 ','.join(check_keys[-1]),
                 step=step, index=index)

    # Add library key
    if not lib_key:
        lib_key = f'{tool}_{param_key}'
    check_keys.append(['library', mainlib, 'option', 'var', lib_key])
    if 'lib' in require:
        chip.add('tool', tool, 'task', task, 'require',
                 ','.join(check_keys[-1]),
                 step=step, index=index)

    # Add option key
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
