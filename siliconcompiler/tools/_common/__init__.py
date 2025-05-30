import os
import pkgutil


def __get_library_keys(chip, include_asic=True, library=None, libraries=None):
    '''
    Returns a list of libraries included in this step/index

    Args:
        chip (Chip): Chip object
        include_asic (bool): include the asic libraries.
    '''
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')

    libs = []

    if not libraries:
        libraries = set()

    pref_key = []
    if library:
        pref_key = ['library', library]

    def get_libs(*key):
        if chip.valid(*key) and chip.get(*key, step=step, index=index):
            if chip.get(*key, step=step, index=index):
                return [key]
        return []

    if include_asic:
        libs.extend(get_libs(*pref_key, 'asic', 'logiclib'))
        libs.extend(get_libs(*pref_key, 'asic', 'macrolib'))

    libnames = set()
    if library:
        libnames.add(library)
    for lib_key in get_libs(*pref_key, 'option', 'library'):
        if lib_key in libs:
            continue

        libs.append(lib_key)

        for libname in chip.get(*lib_key, step=step, index=index):
            if libname in libnames:
                continue

            libnames.add(libname)
            libs.extend(__get_library_keys(
                chip,
                include_asic=include_asic,
                library=libname,
                libraries=libnames))

    return set(libs)


def get_libraries(chip, include_asic=True):
    '''
    Returns a list of libraries included in this step/index

    Args:
        chip (Chip): Chip object
        include_asic (bool): include the asic libraries.
    '''
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')

    libs = []

    for key in __get_library_keys(chip, include_asic=include_asic):
        libs.extend(chip.get(*key, step=step, index=index))

    return set(libs)


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
    tool, task = get_tool_task(chip, step, index)

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

    return bool(keys)


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

    files = []
    for key in __get_keys(chip, *key, include_library_files=False):
        step, index = __get_step_index(chip, *key)
        files.extend(chip.find_files(*key, step=step, index=index))

    if add_library_files:
        for item in get_libraries(chip, include_asic=False):
            lib_key = ('library', item, *key)
            if __is_key_valid(chip, *lib_key):
                step, index = __get_step_index(chip, *lib_key)
                files.extend(chip.find_files(*lib_key, step=step, index=index))

    return __remove_duplicates(chip, files, list(key))


def has_input_files(chip, *key, check_library_files=True):
    '''
    Returns true if the specified key is set.

    Args:
        chip (Chip): Chip object
        key (list): Key to check
        check_library_files (bool): When True, files from library keys
            will be checked
    '''
    if __get_keys(chip, *key, include_library_files=check_library_files):
        return True

    return False


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

    if chip.get(*key, field='pernode').is_never():
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
    from siliconcompiler import SiliconCompilerError

    if not supports:
        supports = []

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)
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
            raise SiliconCompilerError(
                f'{tool}/{task} is requesting support for {opt}, which does not exist',
                chip=chip)


def __get_frontend_option_keys(chip):
    opts = {
        'ydir': __get_keys(chip, 'option', 'ydir'),
        'vlib': __get_keys(chip, 'option', 'vlib'),
        'idir': __get_keys(chip, 'option', 'idir'),
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
    tool, task = get_tool_task(chip, step, index)

    for libkey in __get_library_keys(chip):
        chip.add('tool', tool, 'task', task, 'require', ','.join(libkey), step=step, index=index)

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
    from siliconcompiler.utils import get_file_ext

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    flow = chip.get('option', 'flow')

    for input_step, input_index in chip.get('flowgraph', flow, step, index, 'input'):
        tool, task = get_tool_task(chip, input_step, input_index, flow=flow)
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

            if chip.get(*key, field='pernode').is_never():
                check_step = None
                check_index = None

            check_value = chip.get(*key, step=check_step, index=check_index)
            if check_value:
                return key, check_value

    return None, None


def input_provides(chip, step, index, flow=None):
    from siliconcompiler import NodeStatus

    if not flow:
        flow = chip.get('option', 'flow')

    pruned_nodes = chip.get('option', 'prune')

    nodes = chip.get('flowgraph', flow, step, index, 'input')
    inputs = {}
    for in_step, in_index in nodes:
        if (in_step, in_index) in pruned_nodes:
            # node has been pruned so will not provide anything
            continue

        if chip.get('record', 'status', step=in_step, index=in_index) == \
                NodeStatus.SKIPPED:
            for file, nodes in input_provides(chip, in_step, in_index, flow=flow).items():
                inputs.setdefault(file, []).extend(nodes)
            continue
        tool, task = get_tool_task(chip, in_step, in_index, flow=flow)

        for output in chip.get('tool', tool, 'task', task, 'output',
                               step=in_step, index=in_index):
            inputs.setdefault(output, []).append((in_step, in_index))

    return inputs


def input_file_node_name(filename, step, index):
    from siliconcompiler.utils import get_file_ext

    file_type = get_file_ext(filename)

    if file_type:
        base = filename
        ext = None
        total_ext = []
        while ext != file_type:
            base, ext = os.path.splitext(base)
            ext = ext[1:].lower()
            total_ext.append(ext)

        total_ext.reverse()

        return f'{base}.{step}{index}.{".".join(total_ext)}'
    else:
        return f'{filename}.{step}{index}'


def add_common_file(chip, key, file):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)

    chip.set('tool', tool, 'task', task, 'file', key,
             f'tools/_common/{file}',
             step=step, index=index,
             package='siliconcompiler')
    chip.add('tool', tool, 'task', task, 'require',
             ','.join(['tool', tool, 'task', task, 'file', key]),
             step=step, index=index)


###########################################################################
def get_tool_task(chip, step, index, flow=None):
    '''
    Helper function to get the name of the tool and task associated with a given step/index.
    '''
    if not flow:
        flow = chip.get('option', 'flow')

    tool = chip.get('flowgraph', flow, step, index, 'tool')
    task = chip.get('flowgraph', flow, step, index, 'task')
    return tool, task


def get_tool_tasks(chip, tool):
    tool_dir = os.path.dirname(tool.__file__)
    tool_name = tool.__name__.split('.')[-1]
    tool_base_module = tool.__name__.split('.')
    if not tool.__file__.endswith('__init__.py'):
        tool_base_module = tool_base_module[0:-1]

    task_candidates = []
    for task_mod in pkgutil.iter_modules([tool_dir]):
        if task_mod.name.startswith('_'):
            continue

        if task_mod.name == tool_name:
            continue
        task_candidates.append(task_mod.name)

    tasks = []
    for task in sorted(task_candidates):
        task_module = '.'.join([*tool_base_module, task])
        if getattr(chip._load_module(task_module), 'setup', None):
            tasks.append(task)

    return tasks


#######################################
def record_metric(chip, step, index, metric, value, source, source_unit=None):
    '''
    Records a metric from a given step and index.

    This function ensures the metrics are recorded in the correct units
    as specified in the schema, additionally, this will record the source
    of the value if provided.

    Args:
        step (str): step to record the metric into
        index (str): index to record the metric into
        metric (str): metric to record
        value (float/int): value of the metric that is being recorded
        source (str): file the value came from
        source_unit (str): unit of the value, if not provided it is assumed to have no units

    Examples:
        >>> record_metric(chip, 'floorplan', '0', 'cellarea', 500.0, 'reports/metrics.json', \\
            source_units='um^2')
        Records the metric cell area under 'floorplan0' and notes the source as
        'reports/metrics.json'
    '''
    chip.get("metric", field="schema").record(
        step, index,
        metric,
        value,
        unit=source_unit
    )

    if source:
        flow = chip.get('option', 'flow')
        tool, task = get_tool_task(chip, step, index, flow=flow)

        chip.add('tool', tool, 'task', task, 'report', metric, source, step=step, index=index)


def has_pre_post_script(chip):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)

    return chip.get('tool', tool, 'task', task, 'prescript', step=step, index=index) or \
        chip.get('tool', tool, 'task', task, 'postscript', step=step, index=index)
