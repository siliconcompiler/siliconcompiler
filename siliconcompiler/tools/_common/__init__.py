import os
from siliconcompiler.utils import get_file_ext


def get_libraries(chip, include_asic=True):
    '''
    Returns a list of libraries included in this step/index

    Args:
        chip (Chip): Chip object
        include_asic (bool): When in ['option', 'mode'] == 'asic'
            also include the asic libraries.
    '''
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')

    libs = []

    if include_asic and chip.get('option', 'mode') == 'asic':
        libs.extend(chip.get('asic', 'logiclib', step=step, index=index))
        libs.extend(chip.get('asic', 'macrolib', step=step, index=index))

    libs.extend(chip.get('option', 'library', step=step, index=index))

    return libs


def add_require_input(chip, *key, include_library_files=True):
    '''
    Adds input files to the require list of the task.

    Args:
        chip (Chip): Chip object
        key (list): Key to check for requirements
        add_library_files (bool): When True, files from library keys
            will be included
    '''
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = chip._get_tool_task(step, index)

    keys = []
    for key in __get_keys(chip, *key, include_library_files=False):
        keys.append(key)

    if include_library_files:
        for item in get_libraries(chip, include_asic=False):
            lib_key = ('library', item, *key)
            if __is_key_valid(chip, *lib_key):
                keys.append(lib_key)

    for key in keys:
        chip.add('tool', tool, 'task', task, 'require',
                 ",".join(key),
                 step=step, index=index)


def get_input_files(chip, *key, add_library_files=True):
    '''
    Returns a list of files from the key input and includes files
    from libraries if requested.

    Args:
        chip (Chip): Chip object
        key (list): Key to collect files from
        add_library_files (bool): When True, files from library keys
            will be included
    '''
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')

    files = []
    for key in __get_keys(chip, *key, include_library_files=False):
        files.extend(chip.find_files(*key, step=step, index=index))

    if add_library_files:
        for item in get_libraries(chip, include_asic=False):
            lib_key = ('library', item, *key)
            if __is_key_valid(chip, *lib_key):
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
    if chip.valid(*key):
        step, index = __get_step_index(chip, *key)
        if chip.get(*key, step=step, index=index):
            return True
    return False


def __get_keys(chip, *key, include_library_files=True):
    keys = []
    if __is_key_valid(chip, *key):
        keys.append(key)

    if include_library_files:
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
        val_list = ', '.join([str(list(v)) for v in vals])
        if opt not in supports and val_list:
            msg = f'{tool}/{task} does not support [\'option\', \'{opt}\']'
            if len(vals) != 1 or len(vals[0]) != 2:
                msg += f', the following values will be ignored: {val_list}'
                pass
            chip.logger.warning(msg)

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
    '''
    Adds keys to the require list for the frontend task and checks if
    options are set, which the current frontend does not support.

    Args:
        chip (Chip): Chip object
        supports (list): List of ['option', '*'] which the frontend supports
    '''
    opt_keys = __get_frontend_option_keys(chip)
    __assert_support(chip, opt_keys, supports)

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = chip._get_tool_task(step, index)
    for opt in supports:
        for key in opt_keys[opt]:
            chip.add('tool', tool, 'task', task, 'require', ','.join(key), step=step, index=index)


def get_frontend_options(chip, supports=None):
    '''
    Returns a dictionary of options set for the frontend and checks if
    options are set, which the current frontend does not support.

    Args:
        chip (Chip): Chip object
        supports (list): List of ['option', '*'] which the frontend supports
    '''
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


def find_incoming_ext(chip, support_exts, default_ext):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    flow = chip.get('option', 'flow')

    for input_step, input_index in chip.get('flowgraph', flow, step, index, 'input'):
        tool, task = chip._get_tool_task(input_step, input_index, flow=flow)
        output_exts = {get_file_ext(f): f for f in chip.get('tool', tool, 'task', task, 'output',
                                                            step=input_step, index=input_index)}
        # Search the supported order
        for ext in support_exts:
            if ext in output_exts:
                if output_exts[ext].lower().endswith('.gz'):
                    return f'{ext}.gz'
                return ext

    for ext in support_exts:
        for fileset in chip.getkeys('input'):
            if chip.valid('input', fileset, ext):
                return ext

    # Nothing found return the default
    return default_ext


def pick_key(chip, check_keys, step=None, index=None):
    if not step:
        step = chip.get('arg', 'step')
    if not index:
        index = chip.get('arg', 'index')

    for key in check_keys:
        if chip.valid(*key):
            check_step = step
            check_index = index

            if chip.get(*key, field='pernode') == 'never':
                check_step = None
                check_index = None

            check_value = chip.get(*key, step=check_step, index=check_index)
            if check_value:
                return key, check_value

    return None, None


def input_provides(chip, step, index, flow=None):
    if not flow:
        flow = chip.get('option', 'flow')

    nodes = chip.get('flowgraph', flow, step, index, 'input')
    inputs = {}
    for in_step, in_index in nodes:
        tool, task = chip._get_tool_task(in_step, in_index, flow=flow)

        for output in chip.get('tool', tool, 'task', task, 'output',
                               step=in_step, index=in_index):
            inputs.setdefault(output, []).append((in_step, in_index))

    return inputs


def input_file_node_name(filename, step, index):
    file_type = get_file_ext(filename)

    base = filename
    total_ext = []
    ext = None
    while ext != file_type:
        base, ext = os.path.splitext(base)
        ext = ext[1:].lower()
        total_ext.append(ext)

    total_ext.reverse()

    return f'{base}.{step}{index}.{".".join(total_ext)}'


def add_common_file(chip, key, file):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = chip._get_tool_task(step, index)

    chip.set('tool', tool, 'task', task, 'file', key,
             f'tools/_common/{file}',
             step=step, index=index,
             package='siliconcompiler')
    chip.add('tool', tool, 'task', task, 'require',
             ','.join(['tool', tool, 'task', task, 'file', key]),
             step=step, index=index)
