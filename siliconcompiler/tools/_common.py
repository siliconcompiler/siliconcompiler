def get_libraries(chip):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')

    libs = []

    if chip.get('option', 'mode') == 'asic':
        libs.extend(chip.get('asic', 'logiclib', step=step, index=index))
        libs.extend(chip.get('asic', 'macrolib', step=step, index=index))

    libs.extend(chip.get('option', 'library', step=step, index=index))

    return libs


def __remove_duplicates(chip, values, type):
    new_values = []
    for v in values:
        if v not in new_values:
            new_values.append(v)
        else:
            chip.logger.warning(f"Removing duplicate {type}: {v}")
    return new_values


def get_key_files(chip, *key):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')

    if chip.get(*key, field='pernode') == 'never':
        step = None
        index = None

    files = chip.find_files(*key, step=step, index=index)

    for item in get_libraries(chip):
        files.extend(chip.find_files('library', item, *key, step=step, index=index))

    return __remove_duplicates(chip, files, "file")


def get_key_values(chip, *key):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')

    if chip.get(*key, field='pernode') == 'never':
        step = None
        index = None

    values = chip.get(*key, step=step, index=index)

    for item in get_libraries(chip):
        values.extend(chip.get('library', item, *key, step=step, index=index))

    return __remove_duplicates(chip, values, "value")


def add_require_if_set(chip, *key):
    if not isinstance(key[0], str):
        # This is a list so loop over it
        for vkey in key:
            add_require_if_set(chip, vkey)
        return

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = chip._get_tool_task(step, index)

    if chip.get(*key, field='pernode') == 'never':
        acc_step = None
        acc_index = None
    else:
        acc_step = step
        acc_index = index

    keys = [key]
    for item in get_libraries(chip):
        keys.append(('library', item, *key))

    for key in keys:
        if not chip.valid(*key):
            continue
        if not chip.get(*key, step=acc_step, index=acc_index):
            return

        chip.add('tool', tool, 'task', task, 'require',
                 ",".join(key),
                 step=step, index=index)
