def get_libraries(chip, include_asic=True):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')

    libs = []

    if include_asic and chip.get('option', 'mode') == 'asic':
        libs.extend(chip.get('asic', 'logiclib', step=step, index=index))
        libs.extend(chip.get('asic', 'macrolib', step=step, index=index))

    libs.extend(chip.get('option', 'library', step=step, index=index))

    return libs


def add_require_input(chip, *key, include_library_files=True):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = chip._get_tool_task(step, index)

    keys = [key]
    if include_library_files:
        for item in get_libraries(chip, include_asic=False):
            keys.append(('library', item, *key))

    for key in keys:
        chip.add('tool', tool, 'task', task, 'require',
                 ",".join(key),
                 step=step, index=index)


def get_input_files(chip, *key, add_library_files=True):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')

    files = chip.find_files(*key, step=step, index=index)

    if add_library_files:
        for item in get_libraries(chip, include_asic=False):
            lib_key = ['library', item, *key]
            if chip.valid(*lib_key):
                files.extend(chip.find_files(*lib_key, step=step, index=index))

    return __remove_duplicates(chip, files, list(key))


def __remove_duplicates(chip, values, type):
    new_values = []
    for v in values:
        if v not in new_values:
            new_values.append(v)
        else:
            chip.logger.warning(f"Removing duplicate {type}: {v}")
    return new_values


def __get_step_index(chip, *key):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')

    if chip.get(*key, field='pernode') == 'never':
        step = None
        index = None

    return step, index


def __is_key_valid(chip, *key):
    step, index = __get_step_index(chip, *key)
    if chip.valid(*key) and chip.get(*key, step=step, index=index):
        return True
    return False


def __get_keys(chip, *key):
    keys = []
    if __is_key_valid(chip, *key):
        keys.append(key)

    for item in get_libraries(chip):
        lib_key = ['library', item, *key]
        if __is_key_valid(chip, *lib_key):
            keys.append(tuple(lib_key))

    return keys


def __assert_support(chip, opt_keys, supports):
    if not supports:
        supports = []

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = chip._get_tool_task(step, index)
    for opt, vals in opt_keys.items():
        if opt not in supports:
            val_list = ', '.join([list(v) for v in vals])
            chip.logger.warn(f'{tool}/{task} does not support [\'option\', \'{opt}\'], '
                             f'the following values will be ignored: {val_list}')

    for opt in supports:
        if opt not in opt_keys:
            chip.error(f'{tool}/{task} is requesting support for {opt}, which does not exist',
                       fatal=True)


def __get_frontend_option_keys(chip):
    opts = {
        'ydir': __get_keys(chip, 'option', 'ydir'),
        'vlib': __get_keys(chip, 'option', 'vlib'),
        'idir': __get_keys(chip, 'option', 'idir'),
        'cmdfile': __get_keys(chip, 'option', 'cmdfile'),
        'define': __get_keys(chip, 'option', 'define'),
        'libext': __get_keys(chip, 'option', 'libext'),
        'param': []  # Only from 'option', no libraries
    }

    for param in chip.getkeys('option', 'param'):
        opts['param'].append(('option', 'param', param))

    return opts


def add_frontend_requires(chip, supports=None):
    opt_keys = __get_frontend_option_keys(chip)
    __assert_support(chip, opt_keys, supports)

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = chip._get_tool_task(step, index)
    for opt in supports:
        for key in opt_keys[opt]:
            chip.add('tool', tool, 'task', task, 'require', ','.join(key), step=step, index=index)


def get_frontend_options(chip, supports=None):
    opt_keys = __get_frontend_option_keys(chip)
    __assert_support(chip, opt_keys, supports)

    params = opt_keys['param']
    del opt_keys['param']

    opts = {}
    for opt, keys in opt_keys.items():
        opts[opt] = []
        for key in keys:
            sc_type = chip.get(*key, field='type')
            step, index = __get_step_index(chip, *key)
            if 'file' in sc_type or 'dir' in sc_type:
                opts[opt].extend(chip.find_files(*key, step=step, index=index))
            else:
                opts[opt].extend(chip.get(*key, step=step, index=index))

        opts[opt] = __remove_duplicates(chip, opts[opt], ['option', opt])

    opts['param'] = []
    for key in params:
        param = key[-1]
        value = chip.get(*key)
        opts['param'].append((param, value))

    return opts
